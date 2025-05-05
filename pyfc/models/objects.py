import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyfc.adapters import (
        IObjectAdapter,
        IObjectBaseAdapter,
        IObjectTypeAdapter,
    )

    from .properties import IfcProperty, IfcPSet, PropertySet

from .attribute import IfcAttributeDescriptor
from .base import ABaseModel

logger = logging.getLogger(__name__)


class IfcObjectBase(ABaseModel):
    guid: str = IfcAttributeDescriptor(ifc_attr="GlobalId", read_only=True)  # pyright: ignore[reportAssignmentType]

    def __init__(self, entity: Any, adapter: "IObjectBaseAdapter[IfcObjectBase]"):
        super().__init__(entity)
        self._adapter = adapter

    def get_psets(self) -> list["IfcPSet"]:
        """
        Returns a list of property sets associated with this object.

        Returns
        -------
        list[IfcPSet]
            A list of IfcPSet objects representing the property sets associated with this object.
        """
        return self._adapter.get_psets(self.ifc_id)

    def pset_by_name(self, pset_name: str) -> "IfcPSet | None":
        """
        Returns a property set by its name.

        Parameters
        ----------
        pset_name : str
            The name of the property set.

        Returns
        -------
        IfcPSet | None
            The property set if found, otherwise None.
        """
        property_sets = self._adapter.get_psets(self.ifc_id, pset_name)
        if len(property_sets) == 0:
            return None
        return property_sets[0]

    def add_pset(self, pset: "PropertySet") -> "IfcPSet":
        """
        Adds a property set to this object.

        Parameters
        ----------
        pset : IfcPropertySet
            The property set to add.
        """
        return self._adapter.add_pset(self.ifc_id, pset)

    def remove_pset(self, to_remove: str) -> bool:
        """
        Removes a property set from this object.

        Parameters
        ----------
        to_remove : str | IfcPSet
            The name or instance of the property set to remove.
        """
        return self._adapter.remove_pset(self.ifc_id, to_remove)

    def get_properties(self) -> list["IfcProperty"]:
        """
        Returns a flat list of all properties in the object.

        Returns
        -------
        list[IfcProperty]
            A list of all properties of the object.
        """
        properties: list[IfcProperty] = []
        for property_set in self.get_psets():
            properties.extend(property_set.properties)
        return properties

    def prop_by_name(self, prop_name: str) -> "IfcProperty | None":
        """
        Returns a property by its name.

        Parameters
        ----------
        prop_name : str
            The name of the property.

        Returns
        -------
        IfcProperty | None
            The property if found, otherwise None.
        """
        for prop in self.get_properties():
            if prop.name != prop_name:
                continue
            return prop
        return None


class IfcObjectType(IfcObjectBase):
    def __init__(self, entity: Any, adapter: "IObjectTypeAdapter"):
        super().__init__(entity, adapter)
        self._adapter = adapter

    @property
    def instances(self) -> list["IfcObject"]:
        return self._adapter.get_instances_of(self.ifc_id)


class IfcObject(IfcObjectBase):
    def __init__(self, entity: Any, adapter: "IObjectAdapter"):
        super().__init__(entity, adapter)
        self._adapter = adapter

    @property
    def object_type(self) -> IfcObjectType | None:
        return self._adapter.get_object_type(self.ifc_id)
