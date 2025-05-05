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
    IfcValueType,
    Property,
)

# Import IfcEntityType
from pyfc.models.ifc_types import IfcEntityType
from pyfc.utils import convert

from .base import IosBaseAdapter

# Import the handler class
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
            # Use IfcEntityType for checks
            if (
                pset_entity.is_a(IfcEntityType.PROPERTY_SET)
                and hasattr(pset_entity, "HasProperties")
                and pset_entity.HasProperties
            ):
                prop_entities = pset_entity.HasProperties
            elif (
                pset_entity.is_a(IfcEntityType.ELEMENT_QUANTITY)
                and hasattr(pset_entity, "Quantities")
                and pset_entity.Quantities
            ):
                prop_entities = pset_entity.Quantities
            else:
                logger.debug(
                    f"PSet/QtoSet {pset_id} ({pset_entity.is_a()}) has no properties or quantities defined."
                )
                return []

            result = []
            if prop_entities:
                property_adapter = IosPropertyAdapter(self.context)
                for prop_entity in prop_entities:
                    # Use IfcEntityType for checks
                    if prop_entity.is_a(IfcEntityType.PROPERTY) or prop_entity.is_a(
                        IfcEntityType.PHYSICAL_QUANTITY
                    ):
                        result.append(property_adapter.create_model(prop_entity))
                    else:
                        logger.warning(
                            f"Skipping non-property/quantity entity found in PSet/QtoSet {pset_id}\n"
                            f"Entity: '{prop_entity}' (#{prop_entity.id()}, Type: {prop_entity.is_a()})"
                        )
            return result

        except Exception as e:
            logger.error(f"Error getting properties/quantities for PSet/QtoSet {pset_id}: {e}")
            return []

    def _add_single_value_property(
        self, pset_entity: ios.entity_instance, prop: Property
    ) -> IfcProperty:
        """Adds an IfcPropertySingleValue to an IfcPropertySet, handling units."""
        property_adapter = IosPropertyAdapter(self.context)
        value_handler = property_adapter._value_handler

        ifc_value = prop.ifc_value
        if not ifc_value:
            raise IfcAdapterError(f"Cannot add property '{prop.name}' without an IfcValue.")

        if ifc_value.unit_type not in (IfcUnitType.UNKNOWN, IfcUnitType.COUNT):
            logger.warning(
                f"Adding property '{prop.name}' with unit '{ifc_value.unit_type.name}' to an IfcPropertySet (ID: {pset_entity.id()}). "
                f"Ensure this is not intended as an IfcElementQuantity."
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

        # Use updated IfcUnitType logic
        if ifc_value.unit_type not in (IfcUnitType.UNKNOWN, IfcUnitType.COUNT):
            unit_entity = value_handler.get_or_create_unit(ifc_value.unit_type, ifc_value.prefix)
            if unit_entity:
                prop_entity.Unit = unit_entity
                logger.debug(
                    f"Assigned unit #{unit_entity.id()} ({unit_entity.is_a()}) to property '{prop.name}'"
                )
            else:
                logger.warning(
                    f"Could not determine or create unit for type '{ifc_value.unit_type.name}' (prefix: {ifc_value.prefix.name}) for property '{prop.name}'. Unit not assigned."
                )

        if not hasattr(pset_entity, "HasProperties"):
            pset_entity.HasProperties = []

        props = list(pset_entity.HasProperties or [])
        existing_index = -1
        prop_to_remove = None
        for i, existing_prop in enumerate(props):
            if existing_prop.Name == prop.name:
                existing_index = i
                prop_to_remove = existing_prop
                logger.warning(
                    f"Property '{prop.name}' already exists in PSet {pset_entity.id()}. Replacing it."
                )
                break

        if existing_index != -1:
            props[existing_index] = prop_entity
            if prop_to_remove:
                # Also remove the old NominalValue entity if it exists
                if (
                    prop_to_remove.is_a(IfcEntityType.PROPERTY_SINGLE_VALUE)
                    and hasattr(prop_to_remove, "NominalValue")
                    and prop_to_remove.NominalValue
                ):
                    self.context.remove_entity(prop_to_remove.NominalValue)
                self.context.remove_entity(prop_to_remove)
                logger.debug(f"Removed old property entity #{prop_to_remove.id()} and its value")
        else:
            props.append(prop_entity)

        pset_entity.HasProperties = tuple(props)

        logger.debug(
            f"Added/Updated IfcPropertySingleValue '{prop.name}' (#{prop_entity.id()}) in PSet {pset_entity.id()}"
        )
        self.context.mark_modified()
        return property_adapter.create_model(prop_entity)

    def _add_quantity_property(
        self, qto_entity: ios.entity_instance, prop: Property
    ) -> IfcProperty:
        """Adds an IfcQuantity* to an IfcElementQuantity."""
        property_adapter = IosPropertyAdapter(self.context)
        value_handler = property_adapter._value_handler

        ifc_value = prop.ifc_value
        if not ifc_value:
            raise IfcAdapterError(f"Cannot add quantity '{prop.name}' without an IfcValue.")

        # Use IfcEntityType for quantity types
        quantity_type: IfcEntityType | None = None
        value_attribute: str | None = None

        # Determine Quantity Type and Value Attribute based on unit_type
        if ifc_value.unit_type == IfcUnitType.LENGTH:
            quantity_type = IfcEntityType.QUANTITY_LENGTH
            value_attribute = "LengthValue"
        elif ifc_value.unit_type == IfcUnitType.AREA:
            quantity_type = IfcEntityType.QUANTITY_AREA
            value_attribute = "AreaValue"
        elif ifc_value.unit_type == IfcUnitType.VOLUME:
            quantity_type = IfcEntityType.QUANTITY_VOLUME
            value_attribute = "VolumeValue"
        elif ifc_value.unit_type == IfcUnitType.MASS:
            quantity_type = IfcEntityType.QUANTITY_WEIGHT
            value_attribute = "WeightValue"
        elif ifc_value.unit_type == IfcUnitType.COUNT:
            # Allow REAL or INTEGER for CountValue based on IfcValue
            if ifc_value.value_type not in (IfcValueType.INTEGER, IfcValueType.REAL):
                logger.warning(
                    f"IfcQuantityCount expects Integer or Real value, but got {ifc_value.value_type.value} for value '{ifc_value.value}'. Attempting conversion."
                )
            quantity_type = IfcEntityType.QUANTITY_COUNT
            value_attribute = "CountValue"
        elif ifc_value.unit_type == IfcUnitType.TIME:
            quantity_type = IfcEntityType.QUANTITY_TIME
            value_attribute = "TimeValue"
        else:
            raise IfcAdapterError(
                f"Cannot determine Quantity type for unit '{ifc_value.unit_type.name}'. "
                f"Cannot add property '{prop.name}' to QtoSet {qto_entity.id()}."
            )

        try:
            # Ensure value is of the correct type (float for most, int/float for count)
            entity_value: Any
            if value_attribute == "CountValue":
                # Allow float or int based on IfcValue, prefer int if possible
                entity_value = convert.as_int(ifc_value.value)
                if entity_value is None:
                    entity_value = convert.as_float(ifc_value.value)
                    if entity_value is None:
                        raise ValueError("CountValue must be Integer or Real")
            elif value_attribute == "TimeValue":
                entity_value = float(ifc_value.value)
            else:
                entity_value = float(ifc_value.value)

            unit_entity = None
            if ifc_value.unit_type not in (IfcUnitType.COUNT, IfcUnitType.UNKNOWN):
                unit_entity = value_handler.get_or_create_unit(
                    ifc_value.unit_type, ifc_value.prefix
                )

            create_kwargs = {
                "Name": prop.name,
                value_attribute: entity_value,
            }
            if unit_entity:
                create_kwargs["Unit"] = unit_entity
            elif ifc_value.unit_type not in (IfcUnitType.COUNT, IfcUnitType.UNKNOWN):
                logger.warning(
                    f"Could not determine or create unit for type '{ifc_value.unit_type.name}' (prefix: {ifc_value.prefix.name}) for quantity '{prop.name}'. Unit not assigned."
                )

            # Use IfcEntityType enum member for creation
            prop_entity = self.context.create_entity(quantity_type, **create_kwargs)

        except (ValueError, TypeError) as ve:
            raise IfcAdapterError(
                f"Invalid value '{ifc_value.value}' for {quantity_type.value} '{prop.name}': {ve}"
            ) from ve
        except Exception as e:
            raise IfcAdapterError(
                f"Error creating quantity entity {quantity_type.value} for '{prop.name}': {e}"
            ) from e

        if not hasattr(qto_entity, "Quantities"):
            qto_entity.Quantities = []

        quantities = list(qto_entity.Quantities or [])
        existing_index = -1
        qto_to_remove = None
        for i, existing_qto in enumerate(quantities):
            if existing_qto.Name == prop.name:
                existing_index = i
                qto_to_remove = existing_qto
                logger.warning(
                    f"Quantity '{prop.name}' already exists in QtoSet {qto_entity.id()}. Replacing it."
                )
                break

        if existing_index != -1:
            quantities[existing_index] = prop_entity
            if qto_to_remove:
                self.context.remove_entity(qto_to_remove)
                logger.debug(f"Removed old quantity entity #{qto_to_remove.id()}")
        else:
            quantities.append(prop_entity)

        qto_entity.Quantities = tuple(quantities)

        logger.debug(
            f"Added/Updated {quantity_type.value} '{prop.name}' (#{prop_entity.id()}) in QtoSet {qto_entity.id()}"
        )
        self.context.mark_modified()
        return property_adapter.create_model(prop_entity)

    def add_property(self, pset_id: int, prop: Property) -> IfcProperty:
        """
        Add or update a property or quantity in a property set or quantity set.
        Dispatches to specific helper methods.
        """
        pset_entity = self.context.ifc_by_id(pset_id)
        if not pset_entity:
            raise IfcAdapterError(f"Property set or quantity set with ID {pset_id} not found")

        if not prop.ifc_value:
            raise IfcAdapterError(f"Cannot add property '{prop.name}' without an IfcValue.")

        try:
            # Use IfcEntityType for checks
            if pset_entity.is_a(IfcEntityType.PROPERTY_SET):
                return self._add_single_value_property(pset_entity, prop)
            elif pset_entity.is_a(IfcEntityType.ELEMENT_QUANTITY):
                if prop.ifc_value.unit_type == IfcUnitType.UNKNOWN:
                    raise IfcAdapterError(
                        f"Cannot add property '{prop.name}' without a defined unit (UnitType is UNKNOWN) "
                        f"to an IfcElementQuantity (ID: {pset_id}). Quantities must have units (or be IfcQuantityCount)."
                    )
                return self._add_quantity_property(pset_entity, prop)
            else:
                raise IfcAdapterError(
                    f"Cannot add properties/quantities to entity type {pset_entity.is_a()} (ID: {pset_id})"
                )

        except Exception as exp:
            logger.error(
                f"Error adding/updating property/quantity '{prop.name}' to set {pset_id}: {exp}"
            )
            if isinstance(exp, IfcAdapterError):
                raise
            raise IfcAdapterError(f"Failed to add/update property/quantity: {exp}") from exp

    def remove_property(self, pset_id: int, prop_name: str) -> bool:
        """Remove a property or quantity from a property set or quantity set."""
        pset_entity = self.context.ifc_by_id(pset_id)
        if not pset_entity:
            raise IfcAdapterError(f"Property set or quantity set with ID {pset_id} not found")

        prop_entity_to_remove = None
        modified = False
        is_qto = False

        try:
            # Use IfcEntityType for checks
            if pset_entity.is_a(IfcEntityType.ELEMENT_QUANTITY):
                is_qto = True
                if hasattr(pset_entity, "Quantities") and pset_entity.Quantities:
                    quantities = list(pset_entity.Quantities)
                    initial_len = len(quantities)
                    new_quantities = [q for q in quantities if q.Name != prop_name]
                    if len(new_quantities) < initial_len:
                        prop_entity_to_remove = next(
                            (q for q in quantities if q.Name == prop_name), None
                        )
                        pset_entity.Quantities = tuple(new_quantities)
                        modified = True

            elif pset_entity.is_a(IfcEntityType.PROPERTY_SET):
                if hasattr(pset_entity, "HasProperties") and pset_entity.HasProperties:
                    properties = list(pset_entity.HasProperties)
                    initial_len = len(properties)
                    new_properties = [p for p in properties if p.Name != prop_name]
                    if len(new_properties) < initial_len:
                        prop_entity_to_remove = next(
                            (p for p in properties if p.Name == prop_name), None
                        )
                        pset_entity.HasProperties = tuple(new_properties)
                        modified = True
            else:
                logger.warning(
                    f"Property removal not supported for PSet type: {pset_entity.is_a()}. "
                    f"Only IfcPropertySet and IfcElementQuantity are currently handled."
                )
                return False

            if modified:
                if prop_entity_to_remove:
                    prop_type = "Quantity" if is_qto else "Property"
                    logger.info(
                        f"Removed {prop_type} '{prop_name}' (#{prop_entity_to_remove.id()}) from PSet/QtoSet {pset_id}"
                    )
                    # Also remove the value entity if it's a single value property
                    if (
                        prop_entity_to_remove.is_a(IfcEntityType.PROPERTY_SINGLE_VALUE)
                        and hasattr(prop_entity_to_remove, "NominalValue")
                        and prop_entity_to_remove.NominalValue
                    ):
                        self.context.remove_entity(prop_entity_to_remove.NominalValue)
                    # Remove the property/quantity entity itself
                    self.context.remove_entity(prop_entity_to_remove)
                return self.context.mark_modified()
            else:
                logger.debug(
                    f"Property/quantity '{prop_name}' not found in PSet/QtoSet {pset_id} for removal."
                )
                return False

        except Exception as e:
            logger.error(
                f"Error removing property/quantity {prop_name} from PSet/QtoSet {pset_id}: {e}"
            )
            return False

    def get_objects_of(self, pset_id: int) -> list[IfcObject]:
        """Get elements associated with a property set or quantity set."""
        pset_entity = self.context.ifc_by_id(pset_id)
        if not pset_entity:
            raise IfcAdapterError(f"Property set or quantity set with ID {pset_id} not found")

        result = []
        try:
            inverse_refs = self.context.ifc_model.get_inverse(pset_entity)
            object_adapter = None
            processed_obj_ids = set()

            for ref in inverse_refs:
                # Use IfcEntityType for check
                if ref.is_a(IfcEntityType.REL_DEFINES_BY_PROPERTIES) and hasattr(
                    ref, "RelatedObjects"
                ):
                    if object_adapter is None:
                        from .objects import IosObjectAdapter

                        object_adapter = IosObjectAdapter(self.context)

                    for obj in ref.RelatedObjects:
                        # Use IfcEntityType for check
                        if obj.is_a(IfcEntityType.OBJECT) and obj.id() not in processed_obj_ids:
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
        return IfcProperty(entity, self)

    def get_psets_of(self, property_id: int) -> list[IfcPSet]:
        """Get property sets or quantity sets containing a property or quantity."""
        prop_entity = self.context.ifc_by_id(property_id)
        if not prop_entity:
            raise IfcAdapterError(f"Property or quantity with ID {property_id} not found")
        # Use IfcEntityType for checks
        if not (
            prop_entity.is_a(IfcEntityType.PROPERTY)
            or prop_entity.is_a(IfcEntityType.PHYSICAL_QUANTITY)
        ):
            raise IfcAdapterError(
                f"Entity {property_id} is not an IfcProperty or IfcPhysicalQuantity, but {prop_entity.is_a()}"
            )

        try:
            result = []
            pset_adapter = IosPSetAdapter(self.context)
            processed_pset_ids = set()

            inverse_refs = self.context.ifc_model.get_inverse(prop_entity)
            for ref in inverse_refs:
                # Use IfcEntityType for checks
                is_pset = ref.is_a(IfcEntityType.PROPERTY_SET)
                is_qto = ref.is_a(IfcEntityType.ELEMENT_QUANTITY)

                if (is_pset or is_qto) and ref.id() not in processed_pset_ids:
                    is_in_list = False
                    if is_pset and hasattr(ref, "HasProperties"):
                        is_in_list = prop_entity in (ref.HasProperties or [])
                    elif is_qto and hasattr(ref, "Quantities"):
                        is_in_list = prop_entity in (ref.Quantities or [])

                    if is_in_list:
                        try:
                            result.append(pset_adapter.create_model(ref))
                            processed_pset_ids.add(ref.id())
                        except Exception as e:
                            logger.error(
                                f"Error creating PSet/QtoSet model for entity {ref.id()}: {e}"
                            )

            return result
        except Exception as e:
            logger.error(f"Error getting PSet/QtoSet for property/quantity {property_id}: {e}")
            return []

    def get_value(self, property_id: int) -> IfcValue | None:
        """Get the value of a property or quantity as an IfcValue object."""
        prop_entity = self.context.ifc_by_id(property_id)
        if not prop_entity:
            raise IfcAdapterError(f"Property or quantity with ID {property_id} not found")
        # Use IfcEntityType for checks
        if not (
            prop_entity.is_a(IfcEntityType.PROPERTY)
            or prop_entity.is_a(IfcEntityType.PHYSICAL_QUANTITY)
        ):
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

        # Use IfcEntityType for checks
        if not (
            prop_entity.is_a(IfcEntityType.PROPERTY)
            or prop_entity.is_a(IfcEntityType.PHYSICAL_QUANTITY)
        ):
            raise IfcAdapterError(
                f"Entity {property_id} ({prop_entity.is_a()}) is not an IfcProperty or IfcPhysicalQuantity, cannot set value."
            )

        try:
            ifc_value_raw = value.value
            unit_type = value.unit_type
            prefix = value.prefix
            modified = False

            # Use IfcEntityType for check
            if prop_entity.is_a(IfcEntityType.PROPERTY_SINGLE_VALUE):
                # Keep track of the old value entity before creating the new one
                old_nominal_value = getattr(prop_entity, "NominalValue", None)

                ifc_value_entity = self._value_handler.create_ifc_value_entity(value)
                if not ifc_value_entity:
                    raise IfcAdapterError(
                        f"Failed to create IfcValue entity for property {property_id}"
                    )

                needs_update = True
                if old_nominal_value:
                    try:
                        current_raw = old_nominal_value.wrappedValue
                        new_raw = ifc_value_entity.wrappedValue
                        if isinstance(new_raw, float) and isinstance(current_raw, float):
                            if convert.is_close(current_raw, new_raw):
                                needs_update = False
                        elif current_raw == new_raw:
                            needs_update = False
                    except Exception:
                        pass  # Fallback to update

                if needs_update:
                    prop_entity.NominalValue = ifc_value_entity
                    modified = True
                    logger.debug(f"Updated NominalValue for IfcPropertySingleValue {property_id}")
                    # Remove the old value entity if it existed and is different
                    if old_nominal_value and old_nominal_value.id() != ifc_value_entity.id():
                        self.context.remove_entity(old_nominal_value)
                        logger.debug(f"Removed old NominalValue entity #{old_nominal_value.id()}")

                # Use updated IfcUnitType logic
                unit_entity = self._value_handler.get_or_create_unit(unit_type, prefix)
                current_unit = getattr(prop_entity, "Unit", None)

                if (
                    (unit_entity and not current_unit)
                    or (not unit_entity and current_unit)
                    or (unit_entity and current_unit and unit_entity.id() != current_unit.id())
                ):
                    prop_entity.Unit = unit_entity
                    modified = True
                    logger.debug(
                        f"Updated Unit for IfcPropertySingleValue {property_id} to {unit_entity.id() if unit_entity else 'None'}"
                    )

                if not modified and not needs_update:
                    logger.debug(
                        f"Value and unit for property {property_id} were already up-to-date."
                    )
                    # If value didn't need update, but we created a new value entity anyway (e.g. due to comparison error), remove the unused new one.
                    if (
                        not needs_update
                        and old_nominal_value
                        and old_nominal_value.id() != ifc_value_entity.id()
                    ):
                        self.context.remove_entity(ifc_value_entity)
                    return False

                return self.context.mark_modified() if modified else False

            # --- Handle IfcQuantity subclasses using IfcEntityType ---
            attr_name = None
            expected_unit = None
            converted_value = None

            if prop_entity.is_a(IfcEntityType.QUANTITY_LENGTH):
                attr_name, expected_unit = "LengthValue", IfcUnitType.LENGTH
                converted_value = float(ifc_value_raw)
            elif prop_entity.is_a(IfcEntityType.QUANTITY_AREA):
                attr_name, expected_unit = "AreaValue", IfcUnitType.AREA
                converted_value = float(ifc_value_raw)
            elif prop_entity.is_a(IfcEntityType.QUANTITY_VOLUME):
                attr_name, expected_unit = "VolumeValue", IfcUnitType.VOLUME
                converted_value = float(ifc_value_raw)
            elif prop_entity.is_a(IfcEntityType.QUANTITY_WEIGHT):
                attr_name, expected_unit = "WeightValue", IfcUnitType.MASS
                converted_value = float(ifc_value_raw)
            elif prop_entity.is_a(IfcEntityType.QUANTITY_COUNT):
                attr_name, expected_unit = "CountValue", IfcUnitType.COUNT
                # Allow float or int based on IfcValue, prefer int if possible
                converted_value = convert.as_int(ifc_value_raw)
                if converted_value is None:
                    converted_value = convert.as_float(ifc_value_raw)
                    if converted_value is None:
                        raise ValueError("CountValue must be Integer or Real")
            elif prop_entity.is_a(IfcEntityType.QUANTITY_TIME):
                attr_name, expected_unit = "TimeValue", IfcUnitType.TIME
                converted_value = float(ifc_value_raw)
            else:
                logger.error(
                    f"Cannot set value for unhandled property/quantity type {prop_entity.is_a()} (ID: {property_id})"
                )
                return False

            # --- Set value for Quantities ---
            needs_update = False
            if attr_name:
                if unit_type != expected_unit:
                    logger.warning(
                        f"Setting value for {prop_entity.is_a()} {property_id} but IfcValue has unit type {unit_type.name} (expected {expected_unit.name})"
                    )

                current_value = getattr(prop_entity, attr_name, None)
                needs_update = True
                if current_value is not None:
                    if isinstance(converted_value, float) and isinstance(
                        current_value, (float, int)
                    ):
                        if convert.is_close(current_value, converted_value):
                            needs_update = False
                    elif isinstance(converted_value, int) and isinstance(current_value, int):
                        if current_value == converted_value:
                            needs_update = False
                    # Add more comparisons if needed (e.g. int vs float for Count)
                    elif convert.is_close(
                        float(current_value), float(converted_value)
                    ):  # Fallback float compare
                        needs_update = False

                if needs_update:
                    setattr(prop_entity, attr_name, converted_value)
                    modified = True
                    logger.debug(f"Updated {attr_name} for {prop_entity.is_a()} {property_id}")

                # Update unit for quantities (except Count)
                if expected_unit and expected_unit != IfcUnitType.COUNT:
                    unit_entity = self._value_handler.get_or_create_unit(expected_unit, prefix)
                    current_unit = getattr(prop_entity, "Unit", None)

                    if (
                        (unit_entity and not current_unit)
                        or (not unit_entity and current_unit)
                        or (unit_entity and current_unit and unit_entity.id() != current_unit.id())
                    ):
                        prop_entity.Unit = unit_entity
                        modified = True
                        logger.debug(
                            f"Updated Unit for {prop_entity.is_a()} {property_id} to {unit_entity.id() if unit_entity else 'None'}"
                        )

            if modified:
                return self.context.mark_modified()
            else:
                if not needs_update:
                    logger.debug(
                        f"Value and unit for property/quantity {property_id} were already up-to-date."
                    )
                return False

        except (ValueError, TypeError) as conv_err:
            logger.error(
                f"Error converting value '{value.value}' for property/quantity {property_id} (Entity type: {prop_entity.is_a()}): {conv_err}"
            )
            return False
        except Exception as e:
            logger.error(f"Error setting value for property/quantity {property_id}: {e}")
            if isinstance(e, IfcAdapterError):
                raise
            raise IfcAdapterError(f"Failed to set property/quantity value: {e}") from e
