# pyfc/models/properties.py
import logging
from typing import TYPE_CHECKING, Any, Protocol, List

if TYPE_CHECKING:
    from pyfc.adapters import (
        IPropertyAdapter,
        IPSetAdapter,
    )

from dataclasses import dataclass

from pyfc.validation.properties import validate_pset_definition

from .base import ABaseModel
from .objects import IfcObject
from .value import (
    IfcPrefix,
    IfcUnitType,
    IfcValue,
    IfcValueType,
    ValueFactory,
)

logger = logging.getLogger(__name__)


@dataclass
class Property:
    """
    Data class representing a property to be added or updated.
    Contains the property name and an IfcValue object holding the value and its metadata.
    """

    name: str
    ifc_value: IfcValue

    @property
    def value(self) -> Any:
        return self.ifc_value.value if self.ifc_value else None

    @property
    def value_type(self) -> IfcValueType | None:  # Return None if no ifc_value
        return self.ifc_value.value_type if self.ifc_value else None

    @property
    def unit_type(self) -> IfcUnitType:
        return self.ifc_value.unit_type if self.ifc_value else IfcUnitType.UNKNOWN

    @property
    def prefix(self) -> IfcPrefix:
        return self.ifc_value.prefix if self.ifc_value else IfcPrefix.NONE


class IfcProperty(ABaseModel):
    def __init__(self, entity: Any, adpater: "IPropertyAdapter") -> None:
        super().__init__(entity)
        self._adapter: IPropertyAdapter = adpater

    def property_sets(self) -> list["IfcPSet"]:
        """
        Returns the property sets which contain this property.

        Returns
        -------
        list[IfcPSet]
            A list of IfcPSet objects representing the property sets of the property.
        """
        return self._adapter.get_psets_of(self.ifc_id)

    @property
    def value(self) -> IfcValue | None:
        """
        Returns the value of the property as an IfcValue object,
        including type, unit, and prefix information retrieved from the adapter.

        Returns
        -------
        IfcValue | None
            The IfcValue object representing the property's value and metadata, or None if retrieval fails.
        """
        return self._adapter.get_value(self.ifc_id)

    @value.setter
    def value(self, value: Any | IfcValue) -> None:
        """
        Sets the value of the property using an IfcValue object.

        Accepts either a raw Python value (int, float, str, bool) or a pre-constructed IfcValue object.
        If a raw value is provided, it uses the ValueFactory to create an IfcValue,
        inferring type and using default units/prefixes unless the existing property provides context
        (though the adapter handles the final IFC entity creation based on the IfcValue).

        Parameters
        ----------
        value : Any | IfcValue
            The raw Python value or an IfcValue object to set.

        Returns
        -------
        bool
            True if the value was set successfully, False otherwise.
        """
        if value is None:
            logger.warning(
                f"Attempted to set None value for property {self.ifc_id}. Operation skipped."
            )
            return
        ifc_value_to_set: IfcValue
        if isinstance(value, IfcValue):
            ifc_value_to_set = value
        else:
            # Create IfcValue using the factory from the raw Python value
            # Try to retain existing unit/prefix context if possible?
            # For simplicity now, let factory infer/use defaults. Adapter handles final creation.
            try:
                # TODO: Potentially enhance factory call to use existing unit/prefix as hints?
                # current_ifc_value = self.value # Get current value to extract hints
                # if current_ifc_value:
                #    ifc_value_to_set = value_factory.create(value, unit_type=current_ifc_value.unit_type, prefix=current_ifc_value.prefix)
                # else:
                ifc_value_to_set = ValueFactory.create(value)
            except ValueError as e:
                logger.error(f"Failed to create IfcValue for property {self.ifc_id}: {e}")
                return

        logger.debug(f"Requesting adapter to set value for P:{self.ifc_id} to {ifc_value_to_set}")
        self._adapter.set_value(self.ifc_id, ifc_value_to_set)


class IfcPSet(ABaseModel):
    def __init__(self, entity: Any, adapter: "IPSetAdapter"):
        super().__init__(entity)
        self._adapter: IPSetAdapter = adapter

    def get_elements(self) -> list["IfcObject"]:
        """
        Returns the elements that are associated with this property set.

        Returns
        -------
        list[base.AIfcObjectBase]
            A list of AIfcObjectBase objects representing the elements associated with the property set.
        """
        return self._adapter.get_objects_of(self.ifc_id)

    @property
    def properties(self) -> list[IfcProperty]:
        """
        Returns the properties of the property set.

        Returns
        -------
        list[IfcProperty]
            A list of IfcProperty objects representing the properties of the property set.
        """
        return self._adapter.get_properties(self.ifc_id)

    def get_property(self, prop_name: str) -> "IfcProperty | None":
        """
        Gets a property within this specific property set by its name.

        Parameters
        ----------
        prop_name : str
            The name of the property to retrieve from this PSet.

        Returns
        -------
        IfcProperty | None
            The IfcProperty model object if found within this PSet, otherwise None.
        """
        # Iterate over properties already retrieved via the adapter's get_properties
        # This avoids an extra adapter call if properties are already cached/fetched.
        for prop in self.properties:
            if prop.name == prop_name:
                return prop
        logger.debug(f"Property '{prop_name}' not found in cached properties for {self}")
        # Optional: Could add a direct adapter call here as a fallback,
        # but usually relying on self.properties is sufficient.
        # return self._adapter.get_property_by_name(self.ifc_id, prop_name) # If adapter had this method
        return None

    def add_property(self, prop: "Property") -> "IfcProperty | None":
        """
        Adds a new property directly to this specific IfcPropertySet instance.

        Parameters
        ----------
        prop : Property
            The Property data object defining the property to add to this PSet.

        Returns
        -------
        IfcProperty | None
            The newly created IfcProperty model object, or None if the operation failed
            (e.g., property name conflict within this PSet).
        """
        logger.debug(f"Requesting adapter to add property '{prop.name}' to {self}")
        # Type hint for adapter is IPSetAdapter, which has the method
        return self._adapter.add_property_to_pset(self.ifc_id, prop)

    def remove_property(self, prop_name: str) -> bool:
        """
        Removes a property (by name) directly from this specific IfcPropertySet instance.

        Parameters
        ----------
        prop_name : str
            The name of the property to remove from this PSet.

        Returns
        -------
        bool
            True if the property was found and removed from this PSet, False otherwise.
        """
        logger.debug(f"Requesting adapter to remove property '{prop_name}' from {self}")
        return self._adapter.remove_property_from_pset(self.ifc_id, prop_name)


class IPSetDefinition(Protocol):
    name: str
    properties: list[Property]


@dataclass
class PropertySet(IPSetDefinition):
    name: str
    properties: List[Property]

    def __post_init__(self):
        validate_pset_definition(self)


@dataclass
class QuantitySet(IPSetDefinition):
    name: str
    properties: List[Property]

    def __post_init__(self):
        validate_pset_definition(self)
