import logging
from typing import Any, Iterable

import ifcopenshell as ios
import ifcopenshell.guid
import ifcopenshell.util.element as ios_elem

from pyfc.adapters import IObjectAdapter, IObjectTypeAdapter
from pyfc.errors import IfcAdapterError
from pyfc.models import (
    IfcObject,
    IfcObjectType,
    IfcProperty,
    IfcPSet,
    IfcUnitType,
    Property,
    PropertySet,
)

# Import IfcEntityType
from pyfc.models.ifc_types import IfcEntityType
from pyfc.models.objects import IfcObjectBase

from .base import IosBaseAdapter
from .properties import IosPropertyAdapter, IosPSetAdapter

logger = logging.getLogger(__name__)


# These helpers don't need IfcEntityType as they operate on already retrieved entities
def has_property(entity: ios.entity_instance) -> bool:
    """Check if a property set has properties or quantities."""
    has_props = hasattr(entity, "HasProperties") and entity.HasProperties
    has_qtos = hasattr(entity, "Quantities") and entity.Quantities
    return has_props or has_qtos


def find_property(entity: ios.entity_instance, prop_name: str) -> ios.entity_instance | None:
    """Find a property or quantity by name in a property set or quantity set."""
    if hasattr(entity, "HasProperties") and entity.HasProperties:
        for prop in entity.HasProperties:
            if prop.Name == prop_name:
                return prop
    if hasattr(entity, "Quantities") and entity.Quantities:
        for qto in entity.Quantities:
            if qto.Name == prop_name:
                return qto
    return None


class IfcObjectBaseAdapter[TModel: IfcObjectBase](IosBaseAdapter[TModel]):
    """Base adapter for IfcObjectBase entities."""

    def get_psets(self, element_id: int, pset_name_filter: str | None = None) -> list[IfcPSet]:
        """Get property sets and quantity sets for an element."""
        entity = self.context.ifc_by_id(element_id)
        if not entity:
            raise IfcAdapterError(f"Element with ID {element_id} not found")
        try:
            defined_psets = {}

            if hasattr(entity, "IsDefinedBy"):
                for rel in entity.IsDefinedBy:
                    # Use IfcEntityType for check
                    if not rel.is_a(IfcEntityType.REL_DEFINES_BY_PROPERTIES):
                        continue
                    if not hasattr(rel, "RelatingPropertyDefinition"):
                        continue

                    pset_entity = rel.RelatingPropertyDefinition
                    # Use IfcEntityType for checks
                    if (
                        pset_entity
                        and (
                            pset_entity.is_a(IfcEntityType.PROPERTY_SET)
                            or pset_entity.is_a(IfcEntityType.ELEMENT_QUANTITY)
                        )
                        and hasattr(pset_entity, "Name")
                    ):
                        if pset_name_filter and pset_entity.Name != pset_name_filter:
                            continue
                        if pset_entity.Name not in defined_psets:
                            defined_psets[pset_entity.Name] = pset_entity

            result = []
            pset_adapter = IosPSetAdapter(self.context)
            for _, pset_entity in defined_psets.items():
                result.append(pset_adapter.create_model(pset_entity))

            return result
        except Exception as e:
            logger.error(f"Error getting property/quantity sets for element {element_id}: {e}")
            return []

    def add_pset(self, element_id: int, pset_data: PropertySet) -> IfcPSet:
        """Add a property set or quantity set to an element."""
        entity = self.context.ifc_by_id(element_id)
        if not entity:
            raise IfcAdapterError(f"Element with ID {element_id} not found")

        pset_name = pset_data.name
        existing_psets = self.get_psets(element_id, pset_name_filter=pset_name)
        if len(existing_psets) > 0:
            # If PSet exists, update its properties instead of raising error?
            # For now, raise error to match previous behavior.
            raise IfcAdapterError(
                f"Property set '{pset_name}' already exists on element {element_id}"
            )

        try:
            pset_adapter = IosPSetAdapter(self.context)

            # Use updated IfcUnitType logic
            is_qto = False
            if pset_data.properties:
                for prop in pset_data.properties:
                    if prop.ifc_value and prop.ifc_value.unit_type not in (
                        IfcUnitType.UNKNOWN,
                        IfcUnitType.COUNT,
                    ):
                        is_qto = True
                        logger.debug(
                            f"Detected property '{prop.name}' requires IfcElementQuantity for PSet '{pset_data.name}'."
                        )
                        break

            # Use IfcEntityType for creation
            if is_qto:
                for prop in pset_data.properties:
                    if not prop.ifc_value or prop.ifc_value.unit_type == IfcUnitType.UNKNOWN:
                        raise IfcAdapterError(
                            f"Cannot add property '{prop.name}' without a unit to IfcElementQuantity '{pset_data.name}'."
                        )
                pset_entity = self.context.create_entity(
                    IfcEntityType.ELEMENT_QUANTITY, Name=pset_data.name
                )
                logger.info(f"Created IfcElementQuantity '{pset_data.name}' ({pset_entity.id()})")
            else:
                pset_entity = self.context.create_entity(
                    IfcEntityType.PROPERTY_SET, Name=pset_data.name
                )
                logger.info(f"Created IfcPropertySet '{pset_data.name}' ({pset_entity.id()})")

            # Use IfcEntityType for creation
            self.context.create_entity(
                IfcEntityType.REL_DEFINES_BY_PROPERTIES,
                GlobalId=ifcopenshell.guid.new(),
                OwnerHistory=self.context.owner_history,
                RelatedObjects=[entity],
                RelatingPropertyDefinition=pset_entity,
            )
            logger.info(f"Related PSet/QtoSet '{pset_data.name}' to element {element_id}")

            created_props = []
            for prop_data in pset_data.properties:
                try:
                    created_prop = pset_adapter.add_property(pset_entity.id(), prop_data)
                    created_props.append(created_prop)
                except IfcAdapterError as prop_err:
                    logger.error(
                        f"Failed to add property/quantity '{prop_data.name}' to PSet/QtoSet '{pset_data.name}': {prop_err}"
                    )

            self.context.mark_modified()
            return pset_adapter.create_model(pset_entity)

        except Exception as e:
            logger.error(
                f"Error adding PSet/QtoSet '{pset_data.name}' to element {element_id}: {e}"
            )
            if isinstance(e, IfcAdapterError):
                raise
            raise IfcAdapterError(f"Failed to add PSet/QtoSet: {e}")

    def remove_pset(self, element_id: int, pset_name: str) -> bool:
        """Remove a property set or quantity set relationship from an element, and potentially the set itself."""
        entity = self.context.ifc_by_id(element_id)
        if not entity:
            raise IfcAdapterError(f"Element with ID {element_id} not found")
        try:
            rel_to_remove = None
            pset_entity = None
            modified = False

            rels_to_check = list(entity.IsDefinedBy or [])
            for rel in rels_to_check:
                # Use IfcEntityType for check
                if not rel.is_a(IfcEntityType.REL_DEFINES_BY_PROPERTIES):
                    continue
                if not hasattr(rel, "RelatingPropertyDefinition"):
                    continue

                current_pset = rel.RelatingPropertyDefinition
                if (
                    current_pset
                    and hasattr(current_pset, "Name")
                    and current_pset.Name == pset_name
                ):
                    rel_to_remove = rel
                    pset_entity = current_pset
                    break

            if rel_to_remove:
                rel_to_remove_id = rel_to_remove.id()
                self.context.remove_entity(rel_to_remove)
                modified = True
                logger.info(
                    f"Removed relationship {rel_to_remove_id} linking PSet/QtoSet '{pset_name}' to element {element_id}"
                )

                if pset_entity:
                    inverse_refs = self.context.ifc_model.get_inverse(pset_entity)
                    is_orphaned = True
                    for ref in inverse_refs:
                        # Use IfcEntityType for check
                        if ref.is_a(IfcEntityType.REL_DEFINES_BY_PROPERTIES):
                            is_orphaned = False
                            break
                    if is_orphaned:
                        logger.info(
                            f"PSet/QtoSet '{pset_name}' ({pset_entity.id()}) is orphaned. Removing entity and its contents."
                        )
                        pset_adapter = IosPSetAdapter(self.context)
                        props_to_remove = pset_adapter.get_properties(pset_entity.id())
                        for prop_model in props_to_remove:
                            prop_entity = self.context.ifc_by_id(prop_model.ifc_id)
                            if prop_entity:
                                # Remove value entity if it exists (for SingleValue)
                                if (
                                    prop_entity.is_a(IfcEntityType.PROPERTY_SINGLE_VALUE)
                                    and hasattr(prop_entity, "NominalValue")
                                    and prop_entity.NominalValue
                                ):
                                    # Check if value entity exists before removing
                                    value_entity = self.context.ifc_by_id(
                                        prop_entity.NominalValue.id()
                                    )
                                    if value_entity:
                                        self.context.remove_entity(value_entity)
                                # Remove the property/quantity entity itself
                                self.context.remove_entity(prop_entity)
                        # Remove the PSet/QtoSet entity
                        self.context.remove_entity(pset_entity)
                        modified = True  # Ensure modified is true if pset is removed

            else:
                logger.warning(
                    f"PSet/QtoSet '{pset_name}' not found associated with element {element_id} via IfcRelDefinesByProperties."
                )
                return False

            if modified:
                return self.context.mark_modified()
            return False

        except Exception as e:
            logger.error(f"Error removing PSet/QtoSet '{pset_name}' from element {element_id}: {e}")
            return False

    def _is_property_set(self, entity: ios.entity_instance) -> bool:
        """Check if the entity is a property set or quantity set."""
        return entity.is_a("IfcPropertySet") or entity.is_a("IfcElementQuantity")

    def _remove_properties_from_pset(self, pset_id: int, props_to_remove: Iterable[str]) -> bool:
        """Remove properties from a property set or quantity set."""
        pset_adapter = IosPSetAdapter(self.context)
        any_changes = False

        for prop_name in props_to_remove:
            logger.debug(f"Removing property/quantity '{prop_name}' from PSet/QtoSet {pset_id}")
            try:
                removed = pset_adapter.remove_property(pset_id, prop_name)
                if not removed:
                    logger.error(
                        f"Adapter failed to remove property/quantity '{prop_name}' from PSet/QtoSet {pset_id}"
                    )
                any_changes = any_changes or removed
            except Exception as rem_err:
                logger.error(
                    f"Error removing property/quantity '{prop_name}' from PSet/QtoSet {pset_id}: {rem_err}"
                )
                any_changes = any_changes or False
        return any_changes

    def update_properties(
        self, pset_id: int, properties: list[Property], remove_others: bool = False
    ) -> bool:
        """Update properties/quantities in a property set or quantity set using adapter methods."""
        pset_entity = self.context.ifc_by_id(pset_id)
        if not pset_entity:
            raise IfcAdapterError(f"Property set or quantity set with ID {pset_id} not found")
        if not self._is_property_set(pset_entity):
            raise IfcAdapterError(
                f"Entity {pset_id} is not an IfcPropertySet or IfcElementQuantity."
            )

        try:
            pset_adapter = IosPSetAdapter(self.context)
            prop_adapter = IosPropertyAdapter(self.context)

            current_prop_map = {prop.name: prop for prop in pset_adapter.get_properties(pset_id)}
            incoming_prop_data = {prop.name: prop for prop in properties}
            any_change_successful = False

            for prop_name, prop_data in incoming_prop_data.items():
                if not prop_data.ifc_value:
                    logger.warning(
                        f"Skipping property '{prop_name}' in update_properties for PSet {pset_id}: missing IfcValue."
                    )
                    continue

                if prop_name not in current_prop_map:
                    # Add new property/quantity if it wasn't found
                    logger.debug(
                        f"Adding new property/quantity '{prop_name}' to PSet/QtoSet {pset_id}"
                    )
                    try:
                        # Use the PSet adapter's add_property method
                        added_prop = pset_adapter.add_property(pset_id, prop_data)
                        if added_prop:
                            any_change_successful = True
                            # Update current_prop_map if needed for subsequent logic
                            current_prop_map[prop_name] = added_prop
                        else:
                            logger.error(
                                f"Adapter failed to add property/quantity '{prop_name}' to PSet/QtoSet {pset_id}"
                            )
                    except Exception as add_err:
                        logger.error(
                            f"Error adding property/quantity '{prop_name}' to PSet/QtoSet {pset_id}: {add_err}"
                        )
                    continue

                # --- Update existing property/quantity ---
                existing_prop_model = current_prop_map[prop_name]
                # Compare IfcValue objects directly (dataclass comparison handles frozen=True)
                if existing_prop_model.value != prop_data.ifc_value:
                    logger.debug(
                        f"Updating property/quantity '{prop_name}' in PSet/QtoSet {pset_id}"
                    )
                    try:
                        success = prop_adapter.set_value(
                            existing_prop_model.ifc_id, prop_data.ifc_value
                        )
                        if success:
                            any_change_successful = True
                        else:
                            logger.error(
                                f"Adapter failed to update property/quantity '{prop_name}' in PSet/QtoSet {pset_id}"
                            )
                    except Exception as set_err:
                        logger.error(
                            f"Error calling set_value for property/quantity '{prop_name}' in PSet/QtoSet {pset_id}: {set_err}"
                        )

            # --- Remove properties/quantities not in the incoming list ---
            if remove_others:
                props_to_remove = set(current_prop_map.keys()) - set(incoming_prop_data.keys())
                changes = self._remove_properties_from_pset(pset_id, props_to_remove)
                any_change_successful = any_change_successful or changes

            return any_change_successful

        except Exception as e:
            logger.error(f"Error updating properties/quantities for PSet/QtoSet {pset_id}: {e}")
            if isinstance(e, IfcAdapterError):
                raise
            raise IfcAdapterError(
                f"Failed to update properties/quantities for PSet/QtoSet {pset_id}: {e}"
            )

    def get_property(self, element_id: int, pset_name: str, prop_name: str) -> IfcProperty | None:
        """Get a specific property/quantity model from an element's PSet/QtoSet."""
        psets = self.get_psets(element_id, pset_name_filter=pset_name)
        if not psets:
            logger.debug(f"PSet/QtoSet '{pset_name}' not found for element {element_id}")
            return None

        pset_model = psets[0]
        pset_adapter = IosPSetAdapter(self.context)
        properties = pset_adapter.get_properties(pset_model.ifc_id)

        for prop_model in properties:
            if prop_model.name == prop_name:
                return prop_model

        logger.debug(
            f"Property/quantity '{prop_name}' not found in PSet/QtoSet '{pset_name}' for element {element_id}"
        )
        return None

    def _create_pset_model(self, entity: Any) -> IfcPSet:
        """Helper to create a PSet/QtoSet model from an entity using the adapter."""
        pset_adapter = IosPSetAdapter(self.context)
        return pset_adapter.create_model(entity)

    def _create_property_model(self, entity: Any) -> IfcProperty:
        """Helper to create a property/quantity model from an entity using the adapter."""
        prop_adapter = IosPropertyAdapter(self.context)
        return prop_adapter.create_model(entity)


class IosObjectAdapter(IfcObjectBaseAdapter[IfcObject], IObjectAdapter):
    """Adapter for IfcObject entities (occurrences)."""

    def create_model(self, entity: Any) -> IfcObject:
        """Create an IfcObject model from an entity."""
        return IfcObject(entity, self)

    def get_object_type(self, element_id: int) -> IfcObjectType | None:
        """Get the IfcObjectType associated with this IfcObject instance."""
        entity = self.context.ifc_by_id(element_id)
        if not entity:
            raise IfcAdapterError(f"Element with ID {element_id} not found")
        try:
            type_entity = ios_elem.get_type(entity)
            if type_entity:
                type_adapter = IosObjectTypeAdapter(self.context)
                return type_adapter.create_model(type_entity)

            return None
        except Exception as e:
            logger.error(f"Error getting type for element {element_id}: {e}")
            return None


class IosObjectTypeAdapter(IfcObjectBaseAdapter[IfcObjectType], IObjectTypeAdapter):
    """Adapter for IfcObjectType entities (definitions)."""

    def create_model(self, entity: Any) -> IfcObjectType:
        """Create an IfcObjectType model from an entity."""
        return IfcObjectType(entity, self)

    def get_instances_of(self, type_id: int) -> list[IfcObject]:
        """Get IfcObject instances that are defined by this IfcObjectType."""
        type_entity = self.context.ifc_by_id(type_id)
        if not type_entity:
            logger.warning(f"Type entity with ID {type_id} not found.")
            return []
        # Use IfcEntityType.TYPE_OBJECT which maps to "IfcTypeObject"
        if not type_entity.is_a(IfcEntityType.TYPE_OBJECT):
            logger.warning(
                f"Entity {type_id} is not an IfcTypeObject, but {type_entity.is_a()}. Cannot get instances."
            )
            return []

        try:
            instances = []
            if hasattr(type_entity, "Types"):
                for rel in type_entity.Types:
                    # Use IfcEntityType for check
                    if rel.is_a(IfcEntityType.REL_DEFINES_BY_TYPE) and hasattr(
                        rel, "RelatedObjects"
                    ):
                        instances.extend(rel.RelatedObjects)

            result = []
            object_adapter = IosObjectAdapter(self.context)
            processed_ids = set()  # Avoid duplicates
            for instance in instances:
                # Use IfcEntityType for check
                if instance.is_a(IfcEntityType.OBJECT) and instance.id() not in processed_ids:
                    result.append(object_adapter.create_model(instance))
                    processed_ids.add(instance.id())

            return result
        except Exception as e:
            logger.error(f"Error getting instances of type {type_id}: {e}")
            return []
