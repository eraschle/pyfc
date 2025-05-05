from typing import TYPE_CHECKING, Protocol, runtime_checkable

# Import PSetDefinition
from pyfc.models.properties import IPSetDefinition

from .base import IBaseAdapter

if TYPE_CHECKING:
    from pyfc.models import (
        IfcObject,
        IfcObjectBase,
        IfcObjectType,
        IfcProperty,
        IfcPSet,
        Property,
    )


@runtime_checkable
class IObjectBaseAdapter[TModel: "IfcObjectBase"](IBaseAdapter[TModel], Protocol):
    def get_psets(self, base_id: int, include_qto: bool) -> list["IfcPSet"]:
        """
        Returns a list of property sets (IfcPropertySet) and optionally
        quantity sets (IfcElementQuantity) associated with the object/type.

        Parameters
        ----------
        base_id : int
            The IFC ID of the object/type to retrieve sets for.
        include_qto : bool
            If True, include quantity sets (IfcElementQuantity) in the result.
            If False, exclude quantity sets.

        Returns
        -------
        list[IfcPSet]
            A list of IfcPSet models representing the found IfcPropertySet
            and potentially IfcElementQuantity entities.
        """
        ...

    def get_pset_by_name(self, base_id: int, pset_name: str) -> "IfcPSet | None":
        """
        Returns a specific property set or quantity set by name associated
        with the object/type.

        Parameters
        ----------
        base_id : int
            The IFC ID of the object/type to retrieve the set for.
        pset_name : str
            The name of the property set or quantity set to retrieve.

        Returns
        -------
        IfcPSet | None
            The IfcPSet model representing the found IfcPropertySet or
            IfcElementQuantity, or None if not found.
        """
        ...

    # Rename parameter and update type hint and docstring
    def add_new_pset_to(self, base_id: int, pset_definition: IPSetDefinition) -> "IfcPSet | None":
        """
        Creates a *new* IfcPropertySet or IfcElementQuantity entity, populates
        it with the given properties/quantities, and associates it with the
        specified IfcObject or IfcObjectType via an IfcRelDefinesByProperties
        relationship.

        This method is intended for creating and attaching a completely new PSet/Qto.
        If a set with the same name already exists *directly associated* with this
        object (base_id), the behavior should be to fail (return None or raise Error).

        Parameters
        ----------
        base_id : int
            The IFC ID of the IfcObject or IfcObjectType to which the new set will be added.
        pset_definition : PSetDefinition
            The PropertySet or QuantitySet data object containing the name and
            properties/quantities to be added.

        Returns
        -------
        IfcPSet | None
            The model representation of the *newly created* IfcPropertySet or
            IfcElementQuantity entity, or None if the operation failed (e.g.,
            name conflict, invalid input).
        """
        ...

    def remove_pset_from(self, base_id: int, pset_name: str) -> bool:
        """
        Removes the association between the specified IfcObject/IfcObjectType and
        an IfcPropertySet or IfcElementQuantity based on the set name.

        This method finds the IfcRelDefinesByProperties relationship that links the
        object (identified by base_id) to the IfcPropertySet/IfcElementQuantity
        (identified by pset_name) and removes that relationship.

        Important: This primarily removes the *link*. The IfcPropertySet/Qto entity
        itself will only be deleted by the underlying IFC library if it is no longer
        referenced after this relationship is removed.

        Parameters
        ----------
        base_id : int
            The IFC ID of the IfcObject or IfcObjectType from which the set association
            should be removed.
        pset_name : str
            The name of the IfcPropertySet or IfcElementQuantity whose association
            with the object should be removed.

        Returns
        -------
        bool
            True if the relationship linking the object and the named set was found
            and successfully removed, False otherwise.
        """
        ...

    def get_property(self, base_id: int, pset_name: str, prop_name: str) -> "IfcProperty | None":
        """
        Returns the specified property or quantity model from the given property
        set or quantity set associated with the object/type.

        Parameters
        ----------
        base_id : int
            The IFC ID of the object/type to retrieve the property/quantity from.
        pset_name : str
            The name of the property set or quantity set.
        prop_name : str
            The name of the property or quantity to retrieve.

        Returns
        -------
        IfcProperty | None
            The property/quantity model, or None if not found.
        """
        ...

    def add_property_to_pset(
        self, base_id: int, pset_name: str, prop: "Property"
    ) -> "IfcProperty | None":
        """
        Adds a single IfcProperty/IfcQuantity to an *existing* IfcPropertySet
        or IfcElementQuantity associated with the specified IfcObject or IfcObjectType.

        This method finds the PSet/Qto entity by `pset_name` directly associated
        with the object (`base_id`) and adds the new property/quantity defined
        by the `prop` data object to it.

        If no PSet/Qto with the specified name is directly associated, or if a
        property/quantity with the same name (`prop.name`) already exists within
        that set, the operation should fail (return None or raise error).
        This method does *not* create the PSet/Qto; use `add_new_pset_to` for that.

        Parameters
        ----------
        base_id : int
            The IFC ID of the IfcObject or IfcObjectType whose PSet/Qto is to be modified.
        pset_name : str
            The name of the *existing* IfcPropertySet or IfcElementQuantity
            associated with the object where the property/quantity should be added.
        prop : Property
            The Property data object containing the name and IfcValue for the
            new property/quantity to be created and added.

        Returns
        -------
        IfcProperty | None
            The model representation of the *newly created* IfcProperty/IfcQuantity
            entity within the set, or None if the operation failed.
        """
        ...

    def remove_property_from_pset(self, base_id: int, pset_name: str, prop_name: str) -> bool:
        """
        Removes a single IfcProperty/IfcQuantity from an *existing* IfcPropertySet
        or IfcElementQuantity associated with the specified IfcObject or IfcObjectType.

        This method finds the PSet/Qto entity by `pset_name` directly associated
        with the object (`base_id`) and removes the property/quantity identified
        by `prop_name` from it.

        Parameters
        ----------
        base_id : int
            The IFC ID of the IfcObject or IfcObjectType whose PSet/Qto is to be modified.
        pset_name : str
            The name of the *existing* IfcPropertySet or IfcElementQuantity
            from which the property/quantity should be removed.
        prop_name : str
            The name of the IfcProperty/IfcQuantity to remove.

        Returns
        -------
        bool
            True if the specified PSet/Qto was found associated with the object and the
            property/quantity was successfully removed from it. False otherwise.
        """
        ...


class IObjectAdapter(IObjectBaseAdapter["IfcObject"], Protocol):
    def get_object_type(self, element_id: int) -> "IfcObjectType | None":
        """
        Returns the type (IfcObjectType) of the element (IfcObject) with the
        given IFC ID. Returns None if the element has no type or the type is not found.

        Parameters
        ----------
        element_id : int
            The IFC ID of the element (IfcObject instance) to retrieve the type for.

        Returns
        -------
        IfcObjectType | None
            The type of the element, or None if not found.
        """
        ...


class IObjectTypeAdapter(IObjectBaseAdapter["IfcObjectType"], Protocol):
    def get_instances_of(self, type_id: int) -> list["IfcObject"]:
        """
        Returns a list of object instances (IfcObject) that are defined by the
        given type (IfcObjectType) ID.

        Parameters
        ----------
        type_id : int
            The IFC ID of the element type (IfcObjectType) to retrieve instances for.

        Returns
        -------
        list[IfcObject]
            A list of elements (IfcObject instances) of the given type.
        """
        ...
