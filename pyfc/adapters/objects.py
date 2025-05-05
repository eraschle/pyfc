from typing import TYPE_CHECKING, Protocol

from .base import IBaseAdapter

if TYPE_CHECKING:
    from pyfc.models import (
        IfcObject,
        IfcObjectBase,
        IfcObjectType,
        IfcProperty,
        IfcPSet,
        Property,
        PropertySet,
    )


class IObjectBaseAdapter[TModel: IfcObjectBase](IBaseAdapter[TModel], Protocol):
    def get_psets(
        self, element_id: int, pset_name_filter: str | None = None
    ) -> list["IfcPSet"]:
        """
        Returns a list of property sets for the given element.
        If a pset_name_filter is provided, only property sets matching that name are returned.

        Parameters
        ----------
        element_id : int
            The IFC ID of the element to retrieve property sets for.
        pset_name_filter : str | None, optional
            The name of the property set to filter by (default is None, which returns all property sets).

        Returns
        -------
        list[IfcPSet]
            A list of property sets for the element.
        """
        ...

    def add_pset(self, element_id: int, pset_data: "PropertySet") -> "IfcPSet":
        """
        Adds a property set to the given element.

        Parameters
        ----------
        element_id : int
            The IFC ID of the element to add the property set to.
        pset_data : PropertySet
            The property set data to add.

        Returns
        -------
        IfcPSet
            The created property set.
        """
        ...

    def remove_pset(self, element_id: int, pset_name: str) -> bool:
        """
        Removes a property set from the given element.

        Parameters
        ----------
        element_id : int
            The IFC ID of the element to remove the property set from.
        pset_name : str
            The name of the property set to remove.

        Returns
        -------
        bool
            True if the property set was removed successfully, False otherwise.
        """
        ...

    def update_properties(self, pset_id: int, properties: list["Property"]) -> bool:
        """
        Updates the properties of the property set with the given ID.

        Only properties with a valid value (not None) are processed.
        Existing properties will be updated, new properties will be added to the property set.

        Parameters
        ----------
        pset_id : int
            The ID of the property set to update.
        properties : list[Property]
            A list of properties to update in the property set.

        Returns
        -------
        bool
            True if the properties were updated successfully, False otherwise.
        """
        ...

    def get_property(
        self, element_id: int, pset_name: str, prop_name: str
    ) -> "IfcProperty | None":
        """
        Returns the value of the specified property in the given property set for the element.

        Parameters
        ----------
        element_id : int
            The IFC ID of the element to retrieve the property value for.
        pset_name : str
            The name of the property set to retrieve the property from.
        prop_name : str
            The name of the property to retrieve.

        Returns
        -------
        IfcProperty
            The property value, or None if not found.
        """
        ...


class IObjectAdapter(IObjectBaseAdapter["IfcObject"], Protocol):
    def get_object_type(self, element_id: int) -> "IfcObjectType | None":
        """
        Returns the type of the element with the given IFC ID.
        if the element has no type or the type is not found, None is returned.

        Parameters
        ----------
        element_id : int
            The IFC ID of the element to retrieve the type for.

        Returns
        -------
        IfcObjectType | None
            The type of the element, or None if not found.
        """
        ...


class IObjectTypeAdapter(IObjectBaseAdapter["IfcObjectType"], Protocol):
    def get_instances_of(self, type_id: int) -> list["IfcObject"]:
        """
        Returns a list of elements (instances) of the given type ID.

        Parameters
        ----------
        type_id : int
            The IFC ID of the element type to retrieve instances for.

        Returns
        -------
        list[IfcObject]
            A list of elements (instances) of the given type.
        """
        ...
