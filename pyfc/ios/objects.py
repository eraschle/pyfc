import logging
from typing import Any, Iterable

import ifcopenshell as ios
import ifcopenshell.util.element as ios_elem
from pyfc.adapters import IObjectAdapter, IObjectTypeAdapter
from pyfc.errors import IfcAdapterError
from pyfc.ios import utilities as ifc_utils
from pyfc.ios.properties import (
    IosPropertyAdapter,
    IosPSetAdapter,
)
from pyfc.models import (
    IfcEntityType,
    IfcObject,
    IfcObjectBase,
    IfcObjectType,
    IfcProperty,
    IfcPSet,
    Property,
    IPSetDefinition,
    PropertySet,
    QuantitySet,
)

from .base import IosBaseAdapter


logger = logging.getLogger(__name__)


def has_property(entity: ios.entity_instance) -> bool:
    """Check if a property set has properties or quantities."""
    # This helper seems less relevant now with specific PSet/Qto handling, but keep for now if used elsewhere
    return ifc_utils.has_attribute_value(entity, "HasProperties") or ifc_utils.has_attribute_value(
        entity, "Quantities"
    )


def find_property(entity: ios.entity_instance, prop_name: str) -> ios.entity_instance | None:
    """Find a property or quantity by name in a property set or quantity set."""
    # This helper seems less relevant now with specific PSet/Qto handling, but keep for now if used elsewhere
    if ifc_utils.has_attribute_value(entity, "HasProperties"):
        for prop in ifc_utils.ensure_iterable(entity.HasProperties):
            if ifc_utils.is_attribute_value(prop, "Name", prop_name):
                return prop
    if ifc_utils.has_attribute_value(entity, "Quantities"):
        for qto in ifc_utils.ensure_iterable(entity.Quantities):
            if ifc_utils.is_attribute_value(qto, "Name", prop_name):
                return qto
    return None


class IosObjectBaseAdapter[TModel: IfcObjectBase](IosBaseAdapter[TModel]):
    """Base adapter for IfcObjectBase entities (Objects and ObjectTypes)."""

    def get_psets(self, base_id: int, include_qto: bool = False) -> list[IfcPSet]:
        """
        Get property sets (IfcPropertySet) and optionally quantity sets
        (IfcElementQuantity) associated with an object/type.
        """
        entity = self.context.ifc_by_id(base_id)
        if not entity:
            logger.error(f"Element with ID {base_id} not found.")
            return []
        try:
            # Find related Psets/Qtos via IfcRelDefinesByProperties
            defined_sets = {}  # Use dict to store by ID to avoid duplicates
            if ifc_utils.has_attribute(entity, "IsDefinedBy"):
                relationships = ifc_utils.ensure_iterable(entity.IsDefinedBy)

                for relation in relationships:
                    # Ensure it's the correct relationship type
                    if not ifc_utils.is_rel_defines_by_properties(relation):
                        continue
                    # Ensure the relationship points to a property definition
                    if not ifc_utils.has_attribute(relation, "RelatingPropertyDefinition"):
                        continue

                    pset_entity = relation.RelatingPropertyDefinition
                    # Check if it's a valid PSet
                    is_valid_pset = ifc_utils.is_property_set(pset_entity)
                    # Check if it's a valid Qto (only if requested)
                    is_valid_qto = include_qto and ifc_utils.is_element_quantity(pset_entity)

                    # Skip if it's neither a PSet nor a requested Qto
                    if not (is_valid_pset or is_valid_qto):
                        continue
                    # Ensure it has a name
                    if not ifc_utils.has_attribute(pset_entity, "Name"):
                        continue

                    # Add to dict using ID as key to prevent duplicates if multiple relations point to the same set
                    if pset_entity.id() not in defined_sets:
                        defined_sets[pset_entity.id()] = pset_entity

            result = []
            pset_adapter = IosPSetAdapter(self.context)
            for _, pset_entity in defined_sets.items():
                try:
                    # Create model using the PSet adapter (which handles both PSet/Qto)
                    model = pset_adapter.create_model(pset_entity)
                    if model:  # Ensure model creation was successful
                        result.append(model)
                except Exception as e:
                    logger.error(f"Failed to create model for PSet/Qto {pset_entity.id()}: {e}")

            return result
        except Exception as e:
            logger.error(f"Error getting property/quantity sets for element {base_id}: {e}")
            return []

    def get_pset_by_name(self, base_id: int, pset_name: str) -> IfcPSet | None:
        """
        Get a specific property set or quantity set by name for an object/type.
        """
        # Implementation remains largely the same, but always include Qtos in the initial fetch
        psets = self.get_psets(
            base_id, include_qto=True
        )  # Always include Qtos when searching by name
        if not psets:
            # Adjusted log message for clarity
            logger.debug(
                f"No PSet/Qto found for element {base_id} when searching for '{pset_name}'"
            )
            return None

        for pset in psets:
            # Direct name comparison
            if pset.name == pset_name:
                return pset
        logger.debug(f"PSet/QtoSet '{pset_name}' not found for element {base_id}")
        return None

    def get_property(self, base_id: int, pset_name: str, prop_name: str) -> IfcProperty | None:
        """
        Get a specific property/quantity model from a named property/quantity set
        associated with the object/type.
        """
        # Implementation uses get_pset_by_name and then the model's get_property
        pset_model = self.get_pset_by_name(base_id, pset_name)
        if not pset_model:
            return None

        # Use the get_property method of the IfcPSet model instance
        # This leverages the PSet adapter internally if needed, or uses cached properties
        prop_model = pset_model.get_property(prop_name)

        if not prop_model:
            logger.debug(
                f"Property/quantity '{prop_name}' not found in PSet/QtoSet '{pset_name}' (ID: {pset_model.ifc_id}) for element {base_id}"
            )
        return prop_model

    # --- Helper methods (internal consistency checks) ---
    def _is_property_set(self, entity: ios.entity_instance) -> bool:
        """Check if the entity is a property set or quantity set."""
        # This helper remains useful internally
        return ifc_utils.is_pset_or_qto(entity)

    def _remove_properties_from_pset(self, pset_id: int, props_to_remove: Iterable[str]) -> bool:
        """Remove properties from a property set or quantity set."""
        # This helper seems less used now that removal is delegated, but keep for potential internal use
        pset_adapter = IosPSetAdapter(self.context)
        any_changes = False

        for prop_name in props_to_remove:
            logger.debug(f"Removing property/quantity '{prop_name}' from PSet/QtoSet {pset_id}")
            try:
                # Use the PSet adapter's method
                removed = pset_adapter.remove_property_from_pset(pset_id, prop_name)
                if not removed:
                    logger.warning(
                        f"Adapter did not remove property/quantity '{prop_name}' from PSet/QtoSet {pset_id} (may not exist)."
                    )
                any_changes = any_changes or removed
            except Exception as rem_err:
                logger.error(
                    f"Error removing property/quantity '{prop_name}' from PSet/QtoSet {pset_id}: {rem_err}"
                )
        if any_changes:
            self.context.mark_modified()
        return any_changes

    def _create_pset_model(self, entity: Any) -> IfcPSet:
        """Helper to create a PSet/QtoSet model from an entity using the adapter."""
        # This helper remains useful
        pset_adapter = IosPSetAdapter(self.context)
        return pset_adapter.create_model(entity)

    def _create_property_model(self, entity: Any) -> IfcProperty:
        """Helper to create a property/quantity model from an entity using the adapter."""
        # This helper remains useful
        prop_adapter = IosPropertyAdapter(self.context)
        return prop_adapter.create_model(entity)

    def add_new_pset_to(self, base_id: int, pset_definition: IPSetDefinition) -> IfcPSet | None:
        """
        Implementation of the interface method to add a new IfcPropertySet or
        IfcElementQuantity based on the PSetDefinition.
        """
        base_entity = self.context.ifc_by_id(base_id)
        if not base_entity:
            logger.error(f"Cannot add PSet/Qto: Base entity {base_id} not found.")
            return None

        # Check if a PSet/Qto with this name is already DIRECTLY associated
        existing_pset = self.get_pset_by_name(base_id, pset_definition.name)
        if existing_pset:
            logger.error(
                f"Cannot add PSet/Qto: A set named '{pset_definition.name}' already exists directly on entity {base_id}."
            )
            return None

        pset_entity = None
        rel_entity = None
        # Track created property models for logging/debugging, not direct rollback here
        created_prop_models: list[IfcProperty] = []

        try:
            # --- Determine IFC type and properties based on PSetDefinition type ---
            if isinstance(pset_definition, QuantitySet):
                pset_ifc_type = IfcEntityType.ELEMENT_QUANTITY
                # For Qto, MethodOfMeasurement is often needed/recommended
                kwargs = {
                    "GlobalId": ios.guid.new(),
                    "OwnerHistory": self.context.owner_history,
                    "Name": pset_definition.name,
                    "MethodOfMeasurement": getattr(
                        pset_definition, "method_of_measurement", "BaseQuantities"
                    ),
                    "Quantities": [],
                }
                logger.debug(f"Preparing to create IfcElementQuantity '{pset_definition.name}'")
            elif isinstance(pset_definition, PropertySet):
                pset_ifc_type = IfcEntityType.PROPERTY_SET
                kwargs = {
                    "GlobalId": ios.guid.new(),
                    "OwnerHistory": self.context.owner_history,
                    "Name": pset_definition.name,
                    "HasProperties": [],
                }
                logger.debug(f"Preparing to create IfcPropertySet '{pset_definition.name}'")
            else:
                logger.error(f"Unsupported PSetDefinition type: {type(pset_definition)}")
                raise RuntimeError(f"Unsupported PSetDefinition type: {type(pset_definition)}")
            # --- End determination ---

            pset_entity = self.context.create_entity(pset_ifc_type, **kwargs)
            if not pset_entity:
                # Log the kwargs for debugging if creation fails
                logger.error(f"Failed to create {pset_ifc_type.value} entity with kwargs: {kwargs}")
                raise IfcAdapterError(f"Failed to create {pset_ifc_type.value} entity.")
            logger.debug(
                f"Created new {pset_ifc_type.value} '{pset_definition.name}' (#{pset_entity.id()})"
            )

            # Create the relationship
            # Use ensure_tuple for RelatedObjects, even for a single object
            rel_entity = self.context.create_entity(
                IfcEntityType.REL_DEFINES_BY_PROPERTIES,
                GlobalId=ios.guid.new(),
                OwnerHistory=self.context.owner_history,
                RelatedObjects=ifc_utils.ensure_tuple([base_entity]),  # Ensure it's a tuple
                RelatingPropertyDefinition=pset_entity,
            )
            if not rel_entity:
                # Rollback: Remove the just-created PSet/Qto entity
                logger.error(
                    f"Failed to create IfcRelDefinesByProperties for PSet/Qto {pset_entity.id()}. "
                    "Rolling back PSet/Qto creation."
                )
                self.context.remove_entity(pset_entity)
                raise IfcAdapterError(
                    f"Failed to create IfcRelDefinesByProperties for {pset_entity.id()}."
                )
            logger.debug(
                f"Created relationship {rel_entity.is_a()} (#{rel_entity.id()}) "
                f"linking {base_entity.id()} and {pset_entity.id()}"
            )

            # Add properties/quantities using the PSet adapter
            pset_adapter = IosPSetAdapter(self.context)
            success = True
            for prop_data in pset_definition.properties:
                try:
                    # Use the PSet adapter's method to add the property/quantity
                    created_prop_model = pset_adapter.add_property_to_pset(
                        pset_entity.id(), prop_data
                    )
                    if created_prop_model:
                        created_prop_models.append(created_prop_model)
                        logger.debug(
                            f"Successfully added property/qto '{prop_data.name}' to {pset_entity.id()}"
                        )
                    else:
                        # Adapter method failed (e.g., duplicate name, invalid value)
                        logger.error(
                            f"Adapter failed to add property/qto '{prop_data.name}' to new PSet/Qto '{pset_definition.name}' (#{pset_entity.id()})."
                        )
                        success = False
                        # break # Optional: Stop on first failure

                except Exception as prop_err:
                    # Catch unexpected errors during property addition
                    logger.error(
                        f"Error adding property/qto '{prop_data.name}' to new PSet/Qto '{pset_definition.name}' (#{pset_entity.id()}): {prop_err}"
                    )
                    success = False
                    # break # Optional: Stop on first failure

            if not success:
                # Rollback attempt: Remove the relationship and the PSet/Qto.
                # The PSet adapter's add_property_to_pset should ideally handle
                # its own partial creations/rollbacks if it fails internally.
                # Here, we remove the main entities created in *this* method.
                logger.warning(
                    f"Rolling back PSet/Qto creation for '{pset_definition.name}' (#{pset_entity.id()}) due to property/qto addition errors."
                )
                if rel_entity:
                    logger.debug(f"Removing relationship {rel_entity.id()}")
                    self.context.remove_entity(rel_entity)
                if pset_entity:
                    # Removing the PSet/Qto should ideally cascade-delete its properties/quantities
                    # if they are not referenced elsewhere (ifcopenshell behavior).
                    logger.debug(f"Removing PSet/Qto {pset_entity.id()}")
                    self.context.remove_entity(pset_entity)
                return None

            # If all properties were added successfully, mark modified and return the model
            logger.info(
                f"Successfully added PSet/Qto '{pset_definition.name}' (#{pset_entity.id()}) with {len(created_prop_models)} properties/qtos to {base_id}."
            )
            self.context.mark_modified()
            # Create and return the model for the newly created PSet/Qto
            return pset_adapter.create_model(pset_entity)

        except Exception as e:
            # Catch errors during PSet/Qto or relationship creation
            logger.error(
                f"Error during add_new_pset_to for '{pset_definition.name}' on {base_id}: {e}"
            )
            # More comprehensive rollback if entities were partially created before the exception
            if rel_entity:  # If relationship exists, remove it
                logger.debug(f"Rolling back relationship {rel_entity.id()} due to error: {e}")
                self.context.remove_entity(rel_entity)
            if pset_entity:  # If PSet/Qto exists, remove it
                # Check if it still exists (might have been removed in a nested try-except)
                if self.context.ifc_by_id(pset_entity.id()):
                    logger.debug(f"Rolling back PSet/Qto {pset_entity.id()} due to error: {e}")
                    self.context.remove_entity(pset_entity)
            return None

    # --- Passe Docstring an ---
    def remove_pset_from(self, base_id: int, pset_name: str) -> bool:
        """
        Implementation of the interface method to remove the association
        between an object/type and a named IfcPropertySet or IfcElementQuantity.
        """
        # Implementation structure remains similar: find the relationship and remove/modify it.
        base_entity = self.context.ifc_by_id(base_id)
        if not base_entity:
            logger.error(f"Cannot remove PSet/Qto: Base entity {base_id} not found.")
            return False

        rel_to_remove: ios.entity_instance | None = None
        pset_entity: ios.entity_instance | None = None
        is_shared = False
        rel_id_to_remove = -1  # For logging

        # Find the IfcRelDefinesByProperties relationship linking the base_entity and the named PSet/Qto
        if ifc_utils.has_attribute(base_entity, "IsDefinedBy"):
            rels = ifc_utils.ensure_iterable(base_entity.IsDefinedBy)
            for rel in rels:
                if not ifc_utils.is_rel_defines_by_properties(rel):
                    continue
                if not ifc_utils.has_attribute(rel, "RelatingPropertyDefinition"):
                    continue

                prop_def = rel.RelatingPropertyDefinition
                # Check if it's a PSet or Qto AND if the name matches
                if ifc_utils.is_pset_or_qto(prop_def) and ifc_utils.is_attribute_value(
                    prop_def, "Name", pset_name
                ):
                    # Found the relationship and the target PSet/Qto
                    rel_to_remove = rel
                    pset_entity = prop_def
                    rel_id_to_remove = rel.id()
                    # Check if the relationship is shared among multiple objects
                    related_objects = ifc_utils.ensure_list(getattr(rel, "RelatedObjects", None))
                    is_shared = len(related_objects) > 1
                    break  # Found the first matching relationship, stop searching

        if not rel_to_remove or not pset_entity:
            logger.debug(
                f"No direct relationship found for PSet/Qto '{pset_name}' on entity {base_id}."
            )
            return False

        # Relationship found, proceed with removal logic
        try:
            pset_id_str = str(pset_entity.id())
            if is_shared:
                # If shared, only remove the current object from the relation's RelatedObjects list
                logger.info(
                    f"Removing entity {base_id} from shared relationship #{rel_id_to_remove} with PSet/Qto '{pset_name}' (#{pset_id_str})"
                )
                current_objects = ifc_utils.ensure_list(rel_to_remove.RelatedObjects)
                # Filter out the base_entity by ID
                new_objects = [obj for obj in current_objects if obj.id() != base_id]

                if len(new_objects) < len(current_objects):
                    # Update the relationship with the modified list (must be a tuple)
                    rel_to_remove.RelatedObjects = ifc_utils.ensure_tuple(new_objects)
                    logger.debug(
                        f"Updated RelatedObjects for relation #{rel_id_to_remove}: {len(new_objects)} remaining."
                    )
                    # Optional: If the relation becomes empty, remove it entirely?
                    if not new_objects:
                        logger.info(
                            f"Relationship #{rel_id_to_remove} became empty after removing {base_id}, removing the relationship entity."
                        )
                        self.context.remove_entity(rel_to_remove)
                        # Here one could also check if the pset_entity is now orphaned and remove it.
                        # Requires careful inverse checking.
                    return (
                        self.context.mark_modified()
                    )  # Mark modified even if relation not removed (just updated)
                else:
                    # This case should ideally not happen if we found the relation via base_entity
                    logger.warning(
                        f"Entity {base_id} was expected but not found in RelatedObjects of shared relation #{rel_id_to_remove} for PSet/Qto '{pset_name}'."
                    )
                    return False  # Object wasn't actually in the list
            else:
                # If not shared, remove the entire relationship entity
                logger.info(
                    f"Removing exclusive relationship #{rel_id_to_remove} between entity {base_id} and PSet/Qto '{pset_name}' (#{pset_id_str})"
                )
                removed = self.context.remove_entity(rel_to_remove)
                if removed:
                    logger.debug(f"Successfully removed relationship #{rel_id_to_remove}.")
                    # Optional: Check if pset_entity is now orphaned and remove it.
                    # inverse_refs = self.context.ifc_model.get_inverse(pset_entity) # Example check
                    # is_orphaned = not any(ref.is_a(IfcEntityType.REL_DEFINES_BY_PROPERTIES.value) for ref in inverse_refs if ref and ref.id() != rel_id_to_remove)
                    # if is_orphaned:
                    #     logger.info(f"Removing orphaned PSet/Qto '{pset_name}' (#{pset_id_str})")
                    #     self.context.remove_entity(pset_entity) # Be cautious with cascade deletes
                    return self.context.mark_modified()
                else:
                    # Log if context.remove_entity fails unexpectedly
                    logger.error(f"Context failed to remove relationship #{rel_id_to_remove}.")
                    return False
        except Exception as ex:
            logger.error(
                f"Error removing relationship #{rel_id_to_remove} for PSet/Qto '{pset_name}' from entity {base_id}: {ex}"
            )
            return False

    # --- Passe Docstring an ---
    def add_property_to_pset(
        self, base_id: int, pset_name: str, prop: Property
    ) -> IfcProperty | None:
        """
        Implementation of the interface method to add a property/quantity
        to an existing PSet/Qto associated with the object/type.
        """
        # Implementation remains similar: Find the target PSet/Qto associated with base_id
        # and delegate the property addition to the PSet adapter.
        base_entity = self.context.ifc_by_id(base_id)
        if not base_entity:
            logger.error(f"Cannot add property: Base entity {base_id} not found.")
            return None

        target_pset_entity: ios.entity_instance | None = None
        # Find the specific PSet/Qto entity directly associated with this object via relationships
        if ifc_utils.has_attribute(base_entity, "IsDefinedBy"):
            rels = ifc_utils.ensure_iterable(base_entity.IsDefinedBy)
            for rel in rels:
                if not ifc_utils.is_rel_defines_by_properties(rel):
                    continue
                if not ifc_utils.has_attribute(rel, "RelatingPropertyDefinition"):
                    continue

                prop_def = rel.RelatingPropertyDefinition
                # Check if it's a PSet or Qto AND the name matches
                if ifc_utils.is_pset_or_qto(prop_def) and ifc_utils.is_attribute_value(
                    prop_def, "Name", pset_name
                ):
                    target_pset_entity = prop_def
                    break  # Found the first matching PSet/Qto, stop searching

        if not target_pset_entity:
            logger.error(
                f"PSet/Qto '{pset_name}' not found directly associated with object {base_id}."
            )
            return None

        # Found the target PSet/Qto, delegate property addition to the PSet adapter
        try:
            pset_adapter = IosPSetAdapter(self.context)
            logger.debug(
                f"Delegating addition of property '{prop.name}' to PSet/Qto adapter for set ID {target_pset_entity.id()}"
            )
            new_prop_model = pset_adapter.add_property_to_pset(target_pset_entity.id(), prop)
            if new_prop_model:
                self.context.mark_modified()  # Mark modified on successful addition
            return new_prop_model
        except Exception as ex:
            # Catch errors from the PSet adapter call
            logger.error(
                f"Error adding property '{prop.name}' to PSet/Qto '{pset_name}' (ID: {target_pset_entity.id()}) for object {base_id}: {ex}"
            )
            return None

    def remove_property_from_pset(self, base_id: int, pset_name: str, prop_name: str) -> bool:
        """
        Implementation of the interface method to remove a property/quantity
        from an existing PSet/Qto associated with the object/type.
        """
        # Implementation remains similar: Find the target PSet/Qto associated with base_id
        # and delegate the property removal to the PSet adapter.
        base_entity = self.context.ifc_by_id(base_id)
        if not base_entity:
            logger.error(f"Cannot remove property: Base entity {base_id} not found.")
            return False

        target_pset_entity: ios.entity_instance | None = None
        # Find the specific PSet/Qto entity directly associated with this object
        if ifc_utils.has_attribute(base_entity, "IsDefinedBy"):
            relationships = ifc_utils.ensure_iterable(base_entity.IsDefinedBy)
            for relation in relationships:
                if not ifc_utils.is_rel_defines_by_properties(relation):
                    continue
                if not ifc_utils.has_attribute(relation, "RelatingPropertyDefinition"):
                    continue

                prop_def = relation.RelatingPropertyDefinition
                # Check if it's a PSet or Qto AND the name matches
                if ifc_utils.is_pset_or_qto(prop_def) and ifc_utils.is_attribute_value(
                    prop_def, "Name", pset_name
                ):
                    target_pset_entity = prop_def
                    break  # Found the first matching PSet/Qto

        if not target_pset_entity:
            logger.error(
                f"PSet/Qto '{pset_name}' not found directly associated with object {base_id}."
            )
            return False

        # Found the target PSet/Qto, delegate property removal to the PSet adapter
        try:
            pset_adapter = IosPSetAdapter(self.context)
            logger.debug(
                f"Delegating removal of property '{prop_name}' to PSet/Qto adapter for set ID {target_pset_entity.id()}"
            )
            removed = pset_adapter.remove_property_from_pset(target_pset_entity.id(), prop_name)
            if removed:
                self.context.mark_modified()  # Mark modified on successful removal
            return removed
        except Exception as e:
            # Catch errors from the PSet adapter call
            logger.error(
                f"Error removing property '{prop_name}' from PSet/Qto '{pset_name}' (ID: {target_pset_entity.id()}) for object {base_id}: {e}"
            )
            return False


class IosObjectAdapter(IosObjectBaseAdapter[IfcObject], IObjectAdapter):
    """Adapter for IfcObject entities (occurrences)."""

    def create_model(self, entity: Any) -> IfcObject:
        """Create an IfcObject model from an entity."""
        return IfcObject(entity, self)

    def get_object_type(self, element_id: int) -> IfcObjectType | None:
        """Get the IfcObjectType associated with this IfcObject instance."""
        entity = self.context.ifc_by_id(element_id)
        if not entity:
            logger.error(f"Element with ID {element_id} not found when getting object type.")
            return None
        try:
            # Use ifcopenshell utility which handles different relation types (IsTypedBy, DefinesType)
            type_entity = ios_elem.get_type(entity)
            if not type_entity:
                logger.debug(f"Element {element_id} ({entity.is_a()}) has no type defined.")
                return None
            # Ensure the found type is actually an IfcObjectType
            if not ifc_utils.is_type_object(type_entity):
                logger.warning(
                    f"Entity {type_entity.id()} found as type for {element_id}, but it is a {type_entity.is_a()}, not an IfcTypeObject."
                )
                return None

            type_adapter = IosObjectTypeAdapter(self.context)
            return type_adapter.create_model(type_entity)
        except Exception as e:
            logger.error(f"Error getting type for element {element_id}: {e}")
            return None


class IosObjectTypeAdapter(IosObjectBaseAdapter[IfcObjectType], IObjectTypeAdapter):
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
        # Ensure the entity is actually a type object before proceeding
        if not ifc_utils.is_type_object(type_entity):
            logger.warning(
                f"Entity {type_id} is not an IfcTypeObject, "
                f"but {type_entity.is_a()}. Cannot get instances."
            )
            return []
        try:
            instances = []
            if ifc_utils.has_attribute(type_entity, "Types"):
                type_relationships = ifc_utils.ensure_iterable(type_entity.Types)
                for relation in type_relationships:
                    if not ifc_utils.is_rel_defines_by_type(relation):
                        continue
                    if not ifc_utils.has_attribute(relation, "RelatedObjects"):
                        continue
                    related_objects = ifc_utils.ensure_iterable(relation.RelatedObjects)
                    instances.extend(obj for obj in related_objects if obj is not None)

            result = []
            object_adapter = IosObjectAdapter(self.context)
            processed_ids = set()
            for instance in instances:
                if not instance or not ifc_utils.is_object(instance):
                    continue
                if instance.id() in processed_ids:
                    continue
                try:
                    model = object_adapter.create_model(instance)
                    if model:
                        result.append(model)
                        processed_ids.add(instance.id())
                except Exception as model_err:
                    logger.error(
                        f"Failed to create model for instance {instance.id()} of type {type_id}: {model_err}"
                    )

            return result
        except Exception as e:
            logger.error(f"Error getting instances of type {type_id}: {e}")
            return []
