from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pyfc.models import (
        IfcObject,
        IfcProperty,
        IfcPSet,
        IfcValue,
        Property,
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

    def add_property(self, pset_id: int, prop: "Property") -> "IfcProperty":
        """
        Adds a property to the given property set.

        Parameters
        ----------
        pset_id : int
            The ID of the property set to add the property to.
        prop : Property
            The property to add to the property set.

        Returns
        -------
        IfcProperty
            The added property.
        """
        ...

    def remove_property(self, pset_id: int, prop_name: str) -> bool:
        """
        Removes a property from the given property set.

        This function does not delete the property and all relations to it.

        Parameters
        ----------
        pset_id : int
            The ID of the property set to add the property to.
        prop_name : str
            The name of the property to remove.

        Returns
        -------
        bool
            True if the property was removed successfully, False otherwise.
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
        list[IfcElement]
            A list of elements associated with the property set.
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
        Any | None
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

        The adapter implementation is responsible for interpreting the IfcValue
        and creating/updating the appropriate IFC entities (value, unit, property).
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
