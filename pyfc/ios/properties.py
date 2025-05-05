# -*- coding: utf-8 -*-
import logging
from typing import TYPE_CHECKING, Any

import ifcopenshell as ios
from pyfc.adapters.properties import IPropertyAdapter, IPSetAdapter
from pyfc.errors import IfcAdapterError
from pyfc.models import (
    IfcObject,
    IfcProperty,
    IfcPSet,
    IfcUnitType,
    IfcValue,
    Property,
)

# Import IfcEntityType
from pyfc.models.ifc_types import IfcEntityType
from pyfc.utils import convert

# Import utilities
from . import utilities as ifc_utils
from .base import IosBaseAdapter
from .qto_property import QUANTITY_CONFIG
from .value_handler import IosValueUnitHandler

# Import context for type hinting only if needed at module level
if TYPE_CHECKING:
    from .context import IosModelContext

logger = logging.getLogger(__name__)


class IosPSetAdapter(IosBaseAdapter[IfcPSet], IPSetAdapter):
    """Adapter for IfcPropertySet and IfcElementQuantity entities."""

    def create_model(self, entity: Any) -> IfcPSet:
        """Create an IfcPSet model from an entity."""
        return IfcPSet(entity, self)

    def get_properties(self, pset_id: int) -> list[IfcProperty]:
        """Get properties or quantities from a property set or quantity set."""
        pset_entity = self.context.ifc_by_id(pset_id)
        if not pset_entity:
            raise IfcAdapterError(f"Property set or quantity set with ID {pset_id} not found")
        try:
            prop_entities = []
            # Use utility functions
            if ifc_utils.is_property_set(pset_entity) and ifc_utils.has_attribute_value(
                pset_entity, "HasProperties"
            ):
                prop_entities = pset_entity.HasProperties
            elif ifc_utils.is_element_quantity(pset_entity) and ifc_utils.has_attribute_value(
                pset_entity, "Quantities"
            ):
                prop_entities = pset_entity.Quantities
            else:
                # It's valid for a PSet/QtoSet to exist but be empty
                logger.debug(
                    f"PSet/QtoSet {pset_id} ({pset_entity.is_a()}) has no properties or quantities defined."
                )
                return []

            result = []
            if prop_entities:
                property_adapter = IosPropertyAdapter(self.context)
                # Ensure prop_entities is iterable using utility function for iteration
                prop_entities_iter = ifc_utils.ensure_iterable(prop_entities)

                for prop_entity in prop_entities_iter:
                    # Use utility function
                    if ifc_utils.is_property_or_quantity(prop_entity):
                        result.append(property_adapter.create_model(prop_entity))
                    else:
                        # Log if an unexpected item is in the list
                        logger.warning(
                            f"Skipping non-property/quantity entity found in PSet/QtoSet {pset_id}\n"
                            f"Entity: '{prop_entity}' (#{prop_entity.id() if prop_entity else 'None'}, Type: {prop_entity.is_a() if prop_entity else 'None'})"
                        )
            return result

        except Exception as e:
            logger.error(f"Error getting properties/quantities for PSet/QtoSet {pset_id}: {e}")
            return []

    def _add_single_value_property(
        self, pset_entity: ios.entity_instance, prop: Property
    ) -> IfcProperty:
        """
        Adds an IfcPropertySingleValue to an IfcPropertySet, handling units.
        Assumes the property does NOT already exist (checked by caller).
        """
        property_adapter = IosPropertyAdapter(self.context)
        value_handler = property_adapter._value_handler

        ifc_value = prop.ifc_value
        if not ifc_value:
            raise IfcAdapterError(f"Cannot add property '{prop.name}' without an IfcValue.")

        # Check for potentially inappropriate units in a PropertySet (vs QtoSet)
        if ifc_value.unit_type not in (IfcUnitType.UNKNOWN, IfcUnitType.COUNT):
            logger.warning(
                f"Adding property '{prop.name}' with unit '{ifc_value.unit_type.name}' to an IfcPropertySet (ID: {pset_entity.id()}). "
                f"Units are typically associated with IfcPropertySingleValue via IfcUnitAssignment or context, not directly like quantities."
            )

        nominal_value_entity = value_handler.create_ifc_value_entity(ifc_value)
        if not nominal_value_entity:
            raise IfcAdapterError(
                f"Failed to create NominalValue entity for property '{prop.name}'."
            )

        # Use IfcEntityType
        prop_entity = self.context.create_entity(
            IfcEntityType.PROPERTY_SINGLE_VALUE,
            Name=prop.name,
            NominalValue=nominal_value_entity,
        )

        # Assign Unit if specified and applicable for IfcPropertySingleValue
        # Note: Units for IfcPropertySingleValue are often context-dependent (via IfcUnitAssignment)
        # or sometimes explicitly set. Adding it here if provided.
        if ifc_value.unit_type not in (IfcUnitType.UNKNOWN, IfcUnitType.COUNT):
            unit_entity = value_handler.get_or_create_unit(ifc_value.unit_type, ifc_value.prefix)
            if unit_entity:
                # Check if the instance has the attribute using utility function
                if ifc_utils.has_attribute(prop_entity, "Unit"):
                    prop_entity.Unit = unit_entity
                    logger.debug(
                        f"Assigned unit #{unit_entity.id()} ({unit_entity.is_a()}) directly to IfcPropertySingleValue '{prop.name}'"
                    )
                else:
                    logger.warning(
                        f"Schema does not allow direct assignment of 'Unit' to IfcPropertySingleValue '{prop.name}'. Unit not assigned directly."
                    )
            else:
                logger.warning(
                    f"Could not determine or create unit for type '{ifc_value.unit_type.name}' (prefix: {ifc_value.prefix.name}) for property '{prop.name}'. Unit not assigned."
                )

        # Add the new property to the PSet's list using utility functions
        if not ifc_utils.has_attribute(pset_entity, "HasProperties"):
            # This case should ideally not happen if PSet was created correctly
            logger.error(f"IfcPropertySet {pset_entity.id()} is missing 'HasProperties' attribute.")
            pset_entity.HasProperties = []  # Attempt to fix

        props = ifc_utils.ensure_tuple(getattr(pset_entity, "HasProperties", None))
        pset_entity.HasProperties = props + (prop_entity,)

        logger.debug(
            f"Added IfcPropertySingleValue '{prop.name}' (#{prop_entity.id()}) to PSet {pset_entity.id()}"
        )
        self.context.mark_modified()
        return property_adapter.create_model(prop_entity)

    def _add_quantity_property(
        self, qto_entity: ios.entity_instance, prop: Property
    ) -> IfcProperty:
        """
        Adds an IfcQuantity* to an IfcElementQuantity using QUANTITY_CONFIG.
        Assumes the quantity does NOT already exist (checked by caller).
        """
        property_adapter = IosPropertyAdapter(self.context)
        value_handler = property_adapter._value_handler

        ifc_value = prop.ifc_value
        if not ifc_value:
            raise IfcAdapterError(f"Cannot add quantity '{prop.name}' without an IfcValue.")

        # --- Use QUANTITY_CONFIG to get type, attribute, and conversion ---
        qto_config = QUANTITY_CONFIG.get(ifc_value.unit_type)

        if not qto_config:
            raise IfcAdapterError(
                f"Cannot determine IfcQuantity subtype for unit '{ifc_value.unit_type.name}'. "
                f"Cannot add property '{prop.name}' to QtoSet {qto_entity.id()}."
            )

        try:
            # Convert value using the function from the config
            entity_value = qto_config.convert_func(ifc_value.value)
            if entity_value is None:
                raise ValueError(
                    f"Value '{ifc_value.value}' cannot be converted to required type "
                    f"({qto_config.error_msg_value_type}) for quantity '{prop.name}' ({qto_config.qto_type.value})."
                )

            unit_entity = None
            # Get/Create unit only if it's not COUNT or UNKNOWN
            if ifc_value.unit_type not in (IfcUnitType.COUNT, IfcUnitType.UNKNOWN):
                unit_entity = value_handler.get_or_create_unit(
                    ifc_value.unit_type, ifc_value.prefix
                )
                if not unit_entity:
                    logger.warning(
                        f"Could not determine or create unit for type '{ifc_value.unit_type.name}' "
                        f"(prefix: {ifc_value.prefix.name}) for quantity '{prop.name}'. Unit not assigned."
                    )

            # Prepare arguments for entity creation using config
            create_kwargs = {
                "Name": prop.name,
                qto_config.ifc_attr: entity_value,
                # "Formula": getattr(prop, 'formula', None) # Optional
            }

            # Create the specific IfcQuantity entity using type from config
            prop_entity = self.context.create_entity(qto_config.qto_type, **create_kwargs)
            # Assign unit if found/created and the instance supports it
            if unit_entity and ifc_utils.has_attribute(prop_entity, "Unit"):
                prop_entity.Unit = unit_entity
            elif (
                ifc_value.unit_type not in (IfcUnitType.COUNT, IfcUnitType.UNKNOWN)
                and not unit_entity
            ):
                # Warning already logged above if unit_entity is None when expected
                pass

        except ValueError as ve:
            # Catch conversion errors
            raise IfcAdapterError(
                f"Invalid value for {qto_config.qto_type.value} '{prop.name}': {ve}"
            ) from ve
        except Exception as e:
            # Catch other potential errors during entity creation/unit assignment
            raise IfcAdapterError(
                f"Error creating quantity entity {qto_config.qto_type.value} for '{prop.name}': {e}"
            ) from e

        # Add the new quantity to the QtoSet's list
        if not ifc_utils.has_attribute(qto_entity, "Quantities"):
            logger.error(f"IfcElementQuantity {qto_entity.id()} is missing 'Quantities' attribute.")
            qto_entity.Quantities = []

        quantities = ifc_utils.ensure_list(getattr(qto_entity, "Quantities", None))
        quantities.append(prop_entity)
        qto_entity.Quantities = ifc_utils.ensure_tuple(quantities)

        logger.debug(
            f"Added {qto_config.qto_type.value} '{prop.name}' (#{prop_entity.id()}) to QtoSet {qto_entity.id()}"
        )
        self.context.mark_modified()
        return property_adapter.create_model(prop_entity)

    # Renamed from remove_property
    def remove_property_from_pset(self, pset_id: int, prop_name: str) -> bool:
        """Remove a property or quantity from a property set or quantity set."""
        pset_entity = self.context.ifc_by_id(pset_id)
        if not pset_entity:
            logger.error(f"Property set or quantity set with ID {pset_id} not found for removal.")
            raise IfcAdapterError(
                f"Property set or quantity set with ID {pset_id} not found for removal."
            )

        prop_entity_to_remove = None
        modified = False
        is_qto = False
        prop_list_attr = None

        try:
            # Determine attribute name ('HasProperties' or 'Quantities') using utility functions
            if ifc_utils.is_element_quantity(pset_entity):
                is_qto = True
                prop_list_attr = "Quantities"
            elif ifc_utils.is_property_set(pset_entity):
                prop_list_attr = "HasProperties"
            else:
                logger.warning(
                    f"Property removal not supported for PSet type: {pset_entity.is_a()}. "
                    f"Only IfcPropertySet and IfcElementQuantity are currently handled."
                )
                return False

            if not ifc_utils.has_attribute_value(pset_entity, prop_list_attr):
                logger.debug(
                    f"PSet/QtoSet {pset_id} has no '{prop_list_attr}' attribute or it's empty. Cannot remove '{prop_name}'."
                )
                return False

            prop_list = ifc_utils.ensure_list(getattr(pset_entity, prop_list_attr))
            prop_entity_to_remove = None
            for p in prop_list:
                # Use is_attribute_value
                if ifc_utils.is_attribute_value(p, "Name", prop_name):
                    prop_entity_to_remove = p
                    break

            if not prop_entity_to_remove:
                logger.debug(
                    f"Property/quantity '{prop_name}' not found in PSet/QtoSet {pset_id} for removal."
                )
                return False

            # --- Proceed with removal logic if found ---
            # Create the new list without the removed item
            new_prop_list = [p for p in prop_list if p.id() != prop_entity_to_remove.id()]
            # Update the PSet entity's attribute
            setattr(pset_entity, prop_list_attr, ifc_utils.ensure_tuple(new_prop_list))
            modified = True

            # --- Continue with removal logic ---
            if modified and prop_entity_to_remove:
                prop_type = "Quantity" if is_qto else "Property"
                prop_id = prop_entity_to_remove.id()
                logger.info(
                    f"Removed {prop_type} '{prop_name}' (#{prop_id}) from PSet/QtoSet {pset_id}"
                )

                # Also remove the value entity if it's a single value property using utility functions
                if ifc_utils.is_single_value_property(
                    prop_entity_to_remove
                ) and ifc_utils.has_attribute_value(prop_entity_to_remove, "NominalValue"):
                    value_entity = getattr(prop_entity_to_remove, "NominalValue")
                    # value_entity is guaranteed non-None by has_attribute_value check
                    if self.context.remove_entity(value_entity):
                        logger.debug(f"Removed associated value entity #{value_entity.id()}")
                    else:
                        logger.error(
                            f"Failed to remove associated value entity #{value_entity.id()}"
                        )

                # Remove the property/quantity entity itself
                prop_removed = self.context.remove_entity(prop_entity_to_remove)
                if not prop_removed:
                    logger.error(f"Failed to remove property/quantity entity #{prop_id}")
                    # Should we rollback value removal? Complex. For now, log error.

                # Mark modified if the property list was changed, even if sub-entity removal failed
                return self.context.mark_modified()
            else:
                # Should not be reached due to guard clause, but return False if somehow it is
                return False

        except Exception as e:
            logger.error(
                f"Error removing property/quantity '{prop_name}' from PSet/QtoSet {pset_id}: {e}"
            )
            return False

    def add_property_to_pset(self, pset_id: int, prop: Property) -> IfcProperty | None:
        """Implementation of the interface method."""
        pset_entity = self.context.ifc_by_id(pset_id)
        if not pset_entity:
            logger.error(f"Property set or quantity set with ID {pset_id} not found.")
            return None

        try:
            # Check if property already exists by name using utility functions
            is_qto = False
            prop_list_attr = None

            if ifc_utils.is_element_quantity(pset_entity):
                is_qto = True
                prop_list_attr = "Quantities"
            elif ifc_utils.is_property_set(pset_entity):
                prop_list_attr = "HasProperties"
            else:
                logger.error(f"Cannot add property to unsupported PSet type: {pset_entity.is_a()}")
                return None

            if ifc_utils.has_attribute_value(pset_entity, prop_list_attr):
                prop_list = ifc_utils.ensure_list(getattr(pset_entity, prop_list_attr))
                for p in prop_list:
                    # Use is_attribute_value
                    if ifc_utils.is_attribute_value(p, "Name", prop.name):
                        logger.error(
                            f"Property/Quantity '{prop.name}' already exists in PSet/QtoSet {pset_id} (#{p.id()}). Add operation aborted as per interface contract."
                        )
                        return None

            # --- Proceed with validation and adding if not found ---
            if not prop.ifc_value:
                logger.error(f"Cannot add property '{prop.name}' without IfcValue data.")
                return None

            # Determine if adding to PSet or QtoSet and call appropriate helper
            if is_qto:
                # Check if the unit type is suitable for a quantity
                # COUNT is handled by _add_quantity_property, UNKNOWN is not suitable for QtoSet
                if prop.ifc_value.unit_type in (
                    IfcUnitType.UNKNOWN,
                ):  # QUANTITY_CONFIG handles other unsupported types
                    logger.error(
                        f"Cannot add property '{prop.name}' with unit type '{prop.ifc_value.unit_type.name}' to an IfcElementQuantity (QtoSet)."
                    )
                    return None
                # Call helper for quantities
                return self._add_quantity_property(pset_entity, prop)
            else:  # It's an IfcPropertySet
                # Call helper for single value properties
                # This assumes we only add IfcPropertySingleValue here. Extend if other IfcProperty types are needed.
                if prop.ifc_value.value_type is None:  # Still need IfcValueType for this check
                    logger.error(f"Cannot add property '{prop.name}' with unknown value type.")
                    return None
                # Check if value type is suitable (e.g., not a complex type that needs a different IfcProperty subtype)
                # For now, assume IfcPropertySingleValue is sufficient for basic types handled by value_handler
                return self._add_single_value_property(pset_entity, prop)

        except Exception as e:
            logger.error(f"Error adding property '{prop.name}' to PSet/QtoSet {pset_id}: {e}")
            # Re-raise specific adapter errors, otherwise return None
            if isinstance(e, IfcAdapterError):
                raise
            return None

    def get_objects_of(self, pset_id: int) -> list[IfcObject]:
        """Get elements associated with a property set or quantity set."""
        pset_entity = self.context.ifc_by_id(pset_id)
        if not pset_entity:
            raise IfcAdapterError(f"Property set or quantity set with ID {pset_id} not found")

        result = []
        try:
            # Use get_inverse which is safer than direct attribute access
            inverse_refs = self.context.ifc_model.get_inverse(pset_entity)
            object_adapter = None
            processed_obj_ids = set()

            for ref in inverse_refs:
                if not ifc_utils.is_rel_defines_by_properties(ref):
                    continue
                if not ifc_utils.has_attribute(ref, "RelatedObjects"):
                    continue

                if object_adapter is None:
                    from .objects import IosObjectAdapter

                    object_adapter = IosObjectAdapter(self.context)

                related_objects = ifc_utils.ensure_iterable(ref.RelatedObjects)

                for obj in related_objects:
                    if not ifc_utils.is_object(obj):
                        continue
                    if obj.id() in processed_obj_ids:
                        continue

                    result.append(object_adapter.create_model(obj))
                    processed_obj_ids.add(obj.id())
            return result
        except Exception as e:
            logger.error(f"Error getting elements for PSet/QtoSet {pset_id}: {e}")
            return []


class IosPropertyAdapter(IosBaseAdapter[IfcProperty], IPropertyAdapter):
    """Adapter for IfcProperty and IfcQuantity entities."""

    def __init__(self, context: "IosModelContext"):
        super().__init__(context)
        self._value_handler = IosValueUnitHandler(context)

    def create_model(self, entity: Any) -> IfcProperty:
        # Add check for entity validity using utility function
        if not ifc_utils.is_property_or_quantity(entity):
            raise IfcAdapterError(f"Cannot create IfcProperty model from invalid entity: {entity}")
        return IfcProperty(entity, self)

    def get_psets_of(self, property_id: int) -> list[IfcPSet]:
        """Get property sets or quantity sets containing a property or quantity."""
        prop_entity = self.context.ifc_by_id(property_id)
        if not prop_entity:
            raise IfcAdapterError(f"Property or quantity with ID {property_id} not found")
        # Use utility function
        if not ifc_utils.is_property_or_quantity(prop_entity):
            raise IfcAdapterError(
                f"Entity {property_id} is not an IfcProperty or IfcPhysicalQuantity, but {prop_entity.is_a()}"
            )

        try:
            result = []
            pset_adapter = IosPSetAdapter(self.context)
            processed_pset_ids = set()

            # Use get_inverse to find containing PSet/QtoSet
            inverse_refs = self.context.ifc_model.get_inverse(prop_entity)

            for ref in inverse_refs:
                if ref.id() in processed_pset_ids:
                    continue
                is_pset = ifc_utils.is_property_set(ref)
                is_qto = ifc_utils.is_element_quantity(ref)
                if not (is_pset or is_qto):
                    continue

                # Determine the attribute name and check if the property is in the list
                prop_list_attr = None
                if is_pset:
                    prop_list_attr = "HasProperties"
                elif is_qto:
                    prop_list_attr = "Quantities"

                if prop_list_attr is None:  # Should not happen if is_pset or is_qto is true
                    logger.error(f"Unexpected PSet/QtoSet type for entity {ref.id()}: {ref.is_a()}")
                    continue

                if not ifc_utils.has_attribute(ref, prop_list_attr):
                    continue

                prop_list_iter = ifc_utils.ensure_iterable(getattr(ref, prop_list_attr))
                # Simplified check: Ensure p is not None before accessing id()
                is_in_list = any(p and p.id() == property_id for p in prop_list_iter)
                if not is_in_list:
                    continue

                # If all checks pass, add it
                try:
                    result.append(pset_adapter.create_model(ref))
                    processed_pset_ids.add(ref.id())
                except Exception as e:
                    logger.error(f"Error creating PSet/QtoSet model for entity {ref.id()}: {e}")

            return result
        except Exception as e:
            logger.error(f"Error getting PSet/QtoSet for property/quantity {property_id}: {e}")
            return []

    def get_value(self, property_id: int) -> IfcValue | None:
        """Get the value of a property or quantity as an IfcValue object."""
        prop_entity = self.context.ifc_by_id(property_id)
        if not prop_entity:
            raise IfcAdapterError(f"Property or quantity with ID {property_id} not found")
        # Use utility function
        if not ifc_utils.is_property_or_quantity(prop_entity):
            logger.warning(
                f"Entity {property_id} is not a property or quantity ({prop_entity.is_a()}). Cannot get value."
            )
            return None

        return self._value_handler.get_ifc_value_from_entity(prop_entity)

    def set_value(self, property_id: int, value: "IfcValue") -> bool:
        """Set the value of a property or quantity using an IfcValue object."""
        prop_entity = self.context.ifc_by_id(property_id)
        if not prop_entity:
            raise IfcAdapterError(f"Property or quantity with ID {property_id} not found")

        # Use utility function
        if not ifc_utils.is_property_or_quantity(prop_entity):
            raise IfcAdapterError(
                f"Entity {property_id} ({prop_entity.is_a()}) is not an IfcProperty or IfcPhysicalQuantity, cannot set value."
            )

        try:
            ifc_value_raw = value.value
            unit_type = value.unit_type
            prefix = value.prefix
            modified = False
            needs_value_update = False
            needs_unit_update = False  # Initialize here

            # Use utility function
            if ifc_utils.is_single_value_property(prop_entity):
                # Keep track of the old value entity before creating the new one using utility function
                old_nominal_value = (
                    prop_entity.NominalValue
                    if ifc_utils.has_attribute(prop_entity, "NominalValue")
                    else None
                )
                old_nominal_value_id = old_nominal_value.id() if old_nominal_value else -1

                ifc_value_entity = self._value_handler.create_ifc_value_entity(value)
                if not ifc_value_entity:
                    raise IfcAdapterError(
                        f"Failed to create IfcValue entity for property {property_id}"
                    )
                new_value_entity_id = ifc_value_entity.id()

                needs_value_update = True
                if old_nominal_value:
                    try:
                        # Compare based on wrappedValue and type
                        current_raw = old_nominal_value.wrappedValue
                        new_raw = ifc_value_entity.wrappedValue
                        if old_nominal_value.is_a() == ifc_value_entity.is_a():
                            if isinstance(new_raw, float) and isinstance(current_raw, float):
                                if convert.is_close(current_raw, new_raw):
                                    needs_value_update = False
                            elif current_raw == new_raw:
                                needs_value_update = False
                    except Exception as cmp_err:
                        logger.debug(
                            f"Comparison error for NominalValue, assuming update needed: {cmp_err}"
                        )
                        pass  # Fallback to update

                if needs_value_update:
                    prop_entity.NominalValue = ifc_value_entity
                    modified = True
                    logger.debug(f"Updated NominalValue for IfcPropertySingleValue {property_id}")
                    # Remove the old value entity if it existed and is different
                    if old_nominal_value and old_nominal_value_id != new_value_entity_id:
                        self.context.remove_entity(old_nominal_value)
                        logger.debug(f"Removed old NominalValue entity #{old_nominal_value_id}")
                else:
                    # If value didn't need update, but we created a new value entity anyway, remove the unused new one.
                    if old_nominal_value_id != new_value_entity_id:
                        logger.debug(
                            f"Value unchanged, removing newly created (unused) value entity #{new_value_entity_id}"
                        )
                        self.context.remove_entity(ifc_value_entity)

                # Handle Unit assignment for IfcPropertySingleValue using utility function
                unit_entity = self._value_handler.get_or_create_unit(unit_type, prefix)
                current_unit = (
                    prop_entity.Unit if ifc_utils.has_attribute(prop_entity, "Unit") else None
                )
                needs_unit_update = False  # Reset before check
                if ifc_utils.has_attribute(
                    prop_entity, "Unit"
                ):  # Check if instance has the attribute
                    if (
                        (unit_entity and not current_unit)
                        or (not unit_entity and current_unit)
                        or (unit_entity and current_unit and unit_entity.id() != current_unit.id())
                    ):
                        needs_unit_update = True

                    if needs_unit_update:
                        prop_entity.Unit = unit_entity  # Assign or remove unit
                        modified = True
                        logger.debug(
                            f"Updated Unit for IfcPropertySingleValue {property_id} to {unit_entity.id() if unit_entity else 'None'}"
                        )
                elif unit_entity:
                    # Schema doesn't allow direct unit, but a unit was provided/created. Log warning.
                    logger.warning(
                        f"Schema does not allow direct assignment of 'Unit' to IfcPropertySingleValue '{prop_entity.Name}'. Unit #{unit_entity.id()} not assigned directly."
                    )

                if not modified and not needs_value_update and not needs_unit_update:
                    logger.debug(
                        f"Value and unit for property {property_id} were already up-to-date."
                    )
                    return False  # No changes made

                return self.context.mark_modified() if modified else False

            # --- Handle IfcQuantity subclasses using IfcEntityType and utility function ---
            attr_name = None
            expected_unit = None
            converted_value = None

            # Map entity type to attribute name, expected unit, and perform conversion
            # This section can also be refactored using QUANTITY_CONFIG if desired for consistency
            q_config = QUANTITY_CONFIG.get(
                unit_type
            )  # Get config based on incoming value's unit type

            if q_config and ifc_utils.is_entity_type(prop_entity, q_config.qto_type):
                attr_name = q_config.ifc_attr
                expected_unit = unit_type  # The unit of the incoming value is what we expect to set
                converted_value = q_config.convert_func(ifc_value_raw)
                if converted_value is None:
                    raise ValueError(
                        f"{attr_name} for {prop_entity.Name} ({prop_entity.is_a()}) must be {q_config.error_msg_value_type}, got '{ifc_value_raw}'"
                    )

            # Fallback or explicit mapping if QUANTITY_CONFIG isn't fully aligned or for robustness
            # This part might become redundant if QUANTITY_CONFIG is comprehensive and strictly followed.
            elif ifc_utils.is_entity_type(prop_entity, IfcEntityType.QUANTITY_LENGTH):
                attr_name, expected_unit = "LengthValue", IfcUnitType.LENGTH
                converted_value = convert.as_float(ifc_value_raw)
                if converted_value is None:
                    raise ValueError("LengthValue must be Real")
            elif ifc_utils.is_entity_type(prop_entity, IfcEntityType.QUANTITY_AREA):
                attr_name, expected_unit = "AreaValue", IfcUnitType.AREA
                converted_value = convert.as_float(ifc_value_raw)
                if converted_value is None:
                    raise ValueError("AreaValue must be Real")
            elif ifc_utils.is_entity_type(prop_entity, IfcEntityType.QUANTITY_VOLUME):
                attr_name, expected_unit = "VolumeValue", IfcUnitType.VOLUME
                converted_value = convert.as_float(ifc_value_raw)
                if converted_value is None:
                    raise ValueError("VolumeValue must be Real")
            elif ifc_utils.is_entity_type(prop_entity, IfcEntityType.QUANTITY_WEIGHT):
                attr_name, expected_unit = "WeightValue", IfcUnitType.MASS
                converted_value = convert.as_float(ifc_value_raw)
                if converted_value is None:
                    raise ValueError("WeightValue must be Real")
            elif ifc_utils.is_entity_type(prop_entity, IfcEntityType.QUANTITY_COUNT):
                attr_name, expected_unit = "CountValue", IfcUnitType.COUNT
                converted_value = convert.as_int(ifc_value_raw)
                if converted_value is None:
                    converted_value = convert.as_float(ifc_value_raw)
                    if converted_value is None:
                        raise ValueError("CountValue must be Integer or Real")
            elif ifc_utils.is_entity_type(prop_entity, IfcEntityType.QUANTITY_TIME):
                attr_name, expected_unit = "TimeValue", IfcUnitType.TIME
                converted_value = convert.as_float(ifc_value_raw)
                if converted_value is None:
                    raise ValueError("TimeValue must be Real")
            else:
                logger.error(
                    f"Cannot set value for unhandled property/quantity type {prop_entity.is_a()} (ID: {property_id})"
                )
                return False

            # --- Set value and unit for Quantities ---
            needs_value_update = False  # Reset before check
            if attr_name:
                # Check for unit mismatch (warning only)
                # The `expected_unit` here is derived from the prop_entity's type,
                # while `unit_type` is from the incoming `IfcValue`.
                # A warning should be issued if the incoming `unit_type` is not compatible
                # with the `prop_entity`'s inherent unit type (e.g. trying to set LengthValue with an Area unit)
                # The `QUANTITY_CONFIG` approach above aligns `expected_unit` with `unit_type` from `IfcValue`.
                # If not using `QUANTITY_CONFIG` for this part, the original logic for `expected_unit` is fine.
                # For now, let's assume `expected_unit` is the inherent unit of the quantity type.
                # The `q_config` check above already tries to align this.

                # If `q_config` was used, `expected_unit` is `unit_type`.
                # If fallback was used, `expected_unit` is from the hardcoded map.
                # We should warn if `unit_type` (from IfcValue) doesn't match `expected_unit` (inherent to Quantity type)
                # unless it's a case where the Quantity type itself doesn't dictate a strict unit (e.g. Count).
                if (
                    unit_type != expected_unit
                    and expected_unit != IfcUnitType.COUNT
                    and unit_type != IfcUnitType.UNKNOWN
                ):
                    logger.warning(
                        f"Setting value for {prop_entity.is_a()} {property_id} (expects {expected_unit.name}) "
                        f"but IfcValue has unit type {unit_type.name}."
                    )

                current_value = (
                    getattr(prop_entity, attr_name)
                    if ifc_utils.has_attribute(prop_entity, attr_name)
                    else None
                )
                needs_value_update = True  # Assume update needed unless proven otherwise
                if current_value is not None:
                    try:
                        if isinstance(converted_value, float) and isinstance(
                            current_value, (float, int)
                        ):
                            if convert.is_close(float(current_value), converted_value):
                                needs_value_update = False
                        elif isinstance(converted_value, int) and isinstance(current_value, int):
                            if current_value == converted_value:
                                needs_value_update = False
                        elif convert.is_close(float(current_value), float(converted_value)):
                            needs_value_update = False
                    except Exception as cmp_err:
                        logger.debug(
                            f"Comparison error for quantity value, assuming update needed: {cmp_err}"
                        )
                        pass

                if needs_value_update:
                    setattr(prop_entity, attr_name, converted_value)
                    modified = True
                    logger.debug(f"Updated {attr_name} for {prop_entity.is_a()} {property_id}")

                needs_unit_update = False
                if (
                    expected_unit and expected_unit != IfcUnitType.COUNT
                ):  # Use expected_unit (inherent to Qto type)
                    # The unit to be set should be derived from the incoming IfcValue's unit_type and prefix
                    unit_entity = self._value_handler.get_or_create_unit(unit_type, prefix)
                    current_unit = (
                        prop_entity.Unit if ifc_utils.has_attribute(prop_entity, "Unit") else None
                    )

                    if (
                        (unit_entity and not current_unit)
                        or (not unit_entity and current_unit)
                        or (unit_entity and current_unit and unit_entity.id() != current_unit.id())
                    ):
                        needs_unit_update = True

                    if needs_unit_update:
                        if ifc_utils.has_attribute(prop_entity, "Unit"):
                            prop_entity.Unit = unit_entity
                            modified = True
                            logger.debug(
                                f"Updated Unit for {prop_entity.is_a()} {property_id} to {unit_entity.id() if unit_entity else 'None'}"
                            )
                        elif unit_entity:
                            logger.warning(
                                f"Schema does not allow direct assignment of 'Unit' to {prop_entity.is_a()} '{prop_entity.Name}'. Unit #{unit_entity.id()} not assigned."
                            )
                    elif not unit_entity and expected_unit != IfcUnitType.UNKNOWN:
                        logger.warning(
                            f"Could not get/create unit {unit_type.name} (Prefix: {prefix.name}) for quantity {property_id}. Unit not assigned."
                        )

            if modified:
                return self.context.mark_modified()
            else:
                if not needs_value_update and not needs_unit_update:
                    logger.debug(
                        f"Value and unit for property/quantity {property_id} were already up-to-date."
                    )
                return False

        except (ValueError, TypeError) as conv_err:
            logger.error(
                f"Error converting value '{value.value}' for property/quantity {property_id} (Entity type: {prop_entity.is_a()}): {conv_err}"
            )
            return False
        except Exception as ex:
            logger.error(f"Error setting value for property/quantity {property_id}: {ex}")
            if isinstance(ex, IfcAdapterError):
                raise
            raise IfcAdapterError(f"Failed to set property/quantity value: {ex}") from ex
