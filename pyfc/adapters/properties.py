from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pyfc.models import (
        IfcObject,
        IfcProperty,
        IfcPSet,
        IfcValue,
        Property,  # Added for type hint
    )
from .base import IBaseAdapter


class IPSetAdapter(IBaseAdapter["IfcPSet"], Protocol):
    def get_properties(self, pset_id: int) -> list["IfcProperty"]:
        """
        Returns a list of properties for the given property set.

        Parameters
        ----------
        pset_id : int
            The ID of the property set to retrieve properties for.

        Returns
        -------
        list[IfcProperty]
            A list of properties for the property set.
        """
        ...

    def get_objects_of(self, pset_id: int) -> list["IfcObject"]:
        """
        Returns a list of elements associated with the given property set.

        Parameters
        ----------
        pset_id : int
            The ID of the property set to retrieve elements for.

        Returns
        -------
        list[IfcObject]
            A list of elements associated with the property set.
        """
        ...

    def add_property_to_pset(self, pset_id: int, prop: "Property") -> "IfcProperty | None":
        """
        Adds a new IfcProperty (e.g., IfcPropertySingleValue) to the *specific*
        IfcPropertySet entity identified by pset_id.

        This method operates directly on the target PSet. It creates the necessary
        IfcProperty entity and its associated IFC value entity based on the provided
        Property data object, then adds the new IfcProperty to the 'HasProperties'
        attribute of the IfcPropertySet.

        If a property with the same name (`prop.name`) already exists within this
        specific PSet (`pset_id`), the behavior might vary by implementation (e.g.,
        raise error, return None, or update - returning None or raising Error is
        recommended to enforce explicit update logic elsewhere if needed).

        Parameters
        ----------
        pset_id : int
            The IFC ID of the specific IfcPropertySet entity to modify.
        prop : Property
            The Property data object containing the name and IfcValue for the
            new property to be created and added.

        Returns
        -------
        IfcProperty | None
            The model representation of the *newly created* IfcProperty entity,
            or None if the operation failed (e.g., property name conflict, invalid input).
        """
        ...

    def remove_property_from_pset(self, pset_id: int, prop_name: str) -> bool:
        """
        Removes an IfcProperty from the *specific* IfcPropertySet entity identified
        by pset_id, based on the property name.

        This method finds the IfcProperty entity with the given `prop_name` within
        the 'HasProperties' attribute of the target IfcPropertySet and removes it
        from that collection.

        Important: This removes the property from the PSet's list. The IfcProperty
        entity itself (and potentially its associated value entity) will likely be
        deleted by the underlying IFC library if it's no longer referenced (which
        it shouldn't be after removal from the PSet).

        Parameters
        ----------
        pset_id : int
            The IFC ID of the specific IfcPropertySet entity to modify.
        prop_name : str
            The name of the IfcProperty to remove from this PSet.

        Returns
        -------
        bool
            True if the property was found within the PSet and successfully removed,
            False otherwise (e.g., no property with that name existed in the specified PSet).
        """
        ...


class IPropertyAdapter(IBaseAdapter["IfcProperty"], Protocol):
    def get_psets_of(self, property_id: int) -> list["IfcPSet"]:
        """
        Returns a list of property sets that contain the property with the given ID.

        Parameters
        ----------
        property_id : int
            The ID of the property to retrieve property sets for.
        Returns
        -------
        list[IfcPSet]
            A list of property sets that contain the property.
        """
        ...

    def get_value(self, property_id: int) -> "IfcValue | None":
        """
        Returns the value of the property, including type, unit, and prefix information.

        Parameters
        ----------
        property_id : int
            The ID of the property to retrieve the value for.

        Returns
        -------
        IfcValue | None
            An IfcValue object containing the value and its metadata, or None if retrieval fails.
        """
        ...

    def set_value(self, property_id: int, value: "IfcValue") -> bool:
        """
        Sets the value of the property using the provided IfcValue object.

        Parameters
        ----------
        property_id : int
            The ID of the property to set the value for.
        value : IfcValue
            The IfcValue object containing the new value and its metadata.
        Returns
        -------
        bool
            True if the value was set successfully, False otherwise.
        """
        ...
