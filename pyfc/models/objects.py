import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyfc.adapters import (
        IObjectAdapter,
        IObjectBaseAdapter,
        IObjectTypeAdapter,
    )

    # Füge PSetDefinition und Property zum Import aus .properties hinzu
    from .properties import (
        IfcProperty,
        IfcPSet,
        Property,
        IPSetDefinition,
    )

from .attribute import IfcAttributeDescriptor
from .base import ABaseModel

logger = logging.getLogger(__name__)


class IfcObjectBase(ABaseModel):
    guid: str = IfcAttributeDescriptor(ifc_attr="GlobalId", read_only=True)  # pyright: ignore[reportAssignmentType]

    # Ensure adapter type hint uses the generic TModel
    def __init__(self, entity: Any, adapter: "IObjectBaseAdapter[IfcObjectBase]"):
        super().__init__(entity)
        self._adapter = adapter

    def get_psets(self, include_qto: bool = False) -> list["IfcPSet"]:
        """
        Returns a list of property sets (IfcPropertySet) and optionally
        quantity sets (IfcElementQuantity) associated with this object/type.

        Parameters
        ----------
        include_qto : bool
            If True, include quantity sets (IfcElementQuantity) in the result.
            If False, exclude quantity sets. Defaults to False.

        Returns
        -------
        list[IfcPSet]
            A list of IfcPSet models representing the found IfcPropertySet
            and potentially IfcElementQuantity entities.
        """
        return self._adapter.get_psets(self.ifc_id, include_qto)

    def pset_by_name(self, pset_name: str) -> "IfcPSet | None":
        """
        Returns a specific property set or quantity set by name associated
        with this object/type.

        Parameters
        ----------
        pset_name : str
            The name of the property set or quantity set.

        Returns
        -------
        IfcPSet | None
            The IfcPSet model representing the found IfcPropertySet or
            IfcElementQuantity, or None if not found.
        """
        # Adapter handles searching both Psets and Qtos
        return self._adapter.get_pset_by_name(self.ifc_id, pset_name)

    def get_properties(self) -> list["IfcProperty"]:
        """
        Returns a flat list of all properties and quantities from all directly
        associated property sets and quantity sets.

        Returns
        -------
        list[IfcProperty]
            A list of all IfcProperty models (representing properties and quantities)
            found in the associated sets.
        """
        properties: list[IfcProperty] = []
        # Hole alle PSets und Qtos by setting include_qto=True
        for property_set in self.get_psets(include_qto=True):
            properties.extend(property_set.properties)
        return properties

    def prop_by_name(self, prop_name: str) -> "IfcProperty | None":
        """
        Returns a property or quantity by its name by searching through all
        associated property sets and quantity sets.

        Note: This searches across all sets. If multiple properties/quantities
        with the same name exist in different sets, the first one found is returned.
        Use get_property(pset_name, prop_name) for a specific property.

        Parameters
        ----------
        prop_name : str
            The name of the property or quantity.

        Returns
        -------
        IfcProperty | None
            The IfcProperty model if found, otherwise None.
        """
        for prop in self.get_properties():
            # Direct name comparison is correct here
            if prop.name == prop_name:
                return prop
        return None

    def add_new_pset(self, pset_definition: "IPSetDefinition") -> "IfcPSet | None":
        """
        Adds a new IfcPropertySet or IfcElementQuantity to this object/type
        based on the provided PropertySet or QuantitySet data object.

        This delegates the creation and linking to the associated adapter's
        `add_new_pset_to` method.

        Parameters
        ----------
        pset_definition : PSetDefinition
            The PropertySet or QuantitySet object defining the set to add.
            Validation rules defined in the data class (e.g., in __post_init__)
            should have been checked before calling this method.

        Returns
        -------
        IfcPSet | None
            The model object for the newly created IfcPropertySet or
            IfcElementQuantity, or None if creation failed (e.g., name conflict).
        """
        logger.debug(f"Requesting adapter to add new PSet/Qto '{pset_definition.name}' to {self}")
        return self._adapter.add_new_pset_to(self.ifc_id, pset_definition)

    # --- Passe Docstring an ---
    def remove_pset(self, pset_name: str) -> bool:
        """
        Removes the direct association of an IfcPropertySet or IfcElementQuantity
        (by name) from this object instance or type.

        This delegates the removal to the associated adapter's `remove_pset_from` method.
        The PSet/Qto entity itself might persist if referenced elsewhere.

        Parameters
        ----------
        pset_name : str
            The name of the IfcPropertySet or IfcElementQuantity to disassociate
            from this object/type.

        Returns
        -------
        bool
            True if the set association was successfully removed, False otherwise
            (e.g., no set with that name was directly associated).
        """
        logger.debug(f"Requesting adapter to remove PSet/Qto '{pset_name}' from {self}")
        return self._adapter.remove_pset_from(self.ifc_id, pset_name)

    # --- Passe Docstring an ---
    def get_property(self, pset_name: str, prop_name: str) -> "IfcProperty | None":
        """
        Gets a specific property or quantity model by its PSet/Qto name and
        property/quantity name directly associated with this object/type.

        Delegates to the adapter's `get_property` method.

        Parameters
        ----------
        pset_name : str
            The name of the property set or quantity set containing the property/quantity.
        prop_name : str
            The name of the property or quantity.

        Returns
        -------
        IfcProperty | None
            The property/quantity model object if found, otherwise None.
        """
        logger.debug(f"Requesting adapter to get property '{pset_name}.{prop_name}' from {self}")
        return self._adapter.get_property(self.ifc_id, pset_name, prop_name)

    # --- Passe Docstring an ---
    def add_property_to_pset(self, pset_name: str, prop: "Property") -> "IfcProperty | None":
        """
        Adds a single property or quantity to an *existing* IfcPropertySet or
        IfcElementQuantity associated with this object/type.

        Delegates to the adapter's `add_property_to_pset` method. Does not
        create the PSet/Qto if it doesn't exist.

        Parameters
        ----------
        pset_name : str
            The name of the existing IfcPropertySet or IfcElementQuantity to modify.
        prop : Property
            The Property data object defining the property/quantity to add.

        Returns
        -------
        IfcProperty | None
            The newly created IfcProperty model object within the set, or None if the
            operation failed (e.g., PSet/Qto not found, property name conflict).
        """
        logger.debug(
            f"Requesting adapter to add property '{prop.name}' to PSet/Qto '{pset_name}' on {self}"
        )
        # Adapter protocol ensures method exists
        return self._adapter.add_property_to_pset(self.ifc_id, pset_name, prop)

    # --- Passe Docstring an ---
    def remove_property_from_pset(self, pset_name: str, prop_name: str) -> bool:
        """
        Removes a single property or quantity from an *existing* IfcPropertySet or
        IfcElementQuantity associated with this object/type.

        Delegates to the adapter's `remove_property_from_pset` method.

        Parameters
        ----------
        pset_name : str
            The name of the existing IfcPropertySet or IfcElementQuantity to modify.
        prop_name : str
            The name of the property or quantity to remove.

        Returns
        -------
        bool
            True if the property/quantity was successfully removed, False otherwise
            (e.g., PSet/Qto not found, property not found within the set).
        """
        logger.debug(
            f"Requesting adapter to remove property '{prop_name}' from PSet/Qto '{pset_name}' on {self}"
        )
        # Adapter protocol ensures method exists
        return self._adapter.remove_property_from_pset(self.ifc_id, pset_name, prop_name)


class IfcObjectType(IfcObjectBase):
    def __init__(self, entity: Any, adapter: "IObjectTypeAdapter"):
        super().__init__(entity, adapter)
        self._adapter = adapter

    @property
    def instances(self) -> list["IfcObject"]:
        """Returns the object instances (IfcObject) defined by this type (IfcObjectType)."""
        # Adapter protocol ensures method exists
        return self._adapter.get_instances_of(self.ifc_id)


class IfcObject(IfcObjectBase):
    def __init__(self, entity: Any, adapter: "IObjectAdapter"):  # Use specific adapter type
        super().__init__(entity, adapter)
        self._adapter = adapter

    @property
    def object_type(self) -> "IfcObjectType | None":
        """Returns the IfcObjectType defining this object instance, if any."""
        # Adapter protocol ensures method exists
        return self._adapter.get_object_type(self.ifc_id)
