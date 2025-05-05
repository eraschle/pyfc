# tests/ios/test_ios_pset_adapter.py
import ifcopenshell
import pytest

from pyfc.errors import IfcAdapterError
from pyfc.ios import IosModelContext, IosPSetAdapter
from pyfc.models import (
    IfcObject,
    IfcProperty,
    IfcPSet,
    IfcValue,
)

from tests.conftest import (
    KNOWN_ELEMENT_ID,
    KNOWN_NORMAL_PROP_NAME,
    KNOWN_NORMAL_PROP_VALUE,
    KNOWN_NORMAL_PSET_ID,
    KNOWN_PROP_QTO_NAME_IN_PSET,
    KNOWN_PSET_QTO_ID_ON_ELEMENT,
    NEW_NORMAL_PROP_NAME,
    NEW_NORMAL_PROP_VALUE,
    NEW_NORMAL_PSET_NAME,
    NON_EXISTENT_ID,
    NON_EXISTENT_PROP_NAME,
)


# --- Tests for IosPSetAdapter ---
class TestIosPSetAdapter:
    def test_create_normal_pset_model(
        self, pset_adapter: IosPSetAdapter, ifc_context: IosModelContext
    ):
        # Create a new PropertySet entity directly in the IFC file
        # This test focuses on the adapter's ability to *read* an existing entity
        # and create a model from it, not on creating the entity itself via the adapter.

        # Get element entity to associate with PropertySet
        element_entity = ifc_context.ifc_by_id(KNOWN_ELEMENT_ID)
        assert element_entity is not None

        # Create PropertySet entity
        prop_entity = ifc_context.create_entity(
            "IfcPropertySingleValue",
            Name=NEW_NORMAL_PROP_NAME,
            NominalValue=ifc_context.create_entity("IfcText", wrappedValue=NEW_NORMAL_PROP_VALUE),
        )
        pset_entity = ifc_context.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            Name=NEW_NORMAL_PSET_NAME,
            HasProperties=[prop_entity],
        )

        # Link PropertySet to element
        ifc_context.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            RelatingPropertyDefinition=pset_entity,
            RelatedObjects=[element_entity],
        )

        # Create model from the newly created entity using the adapter
        pset_model = pset_adapter.create_model(pset_entity)

        # Verify created model
        assert pset_model is not None
        assert isinstance(pset_model, IfcPSet)
        assert pset_model.name == NEW_NORMAL_PSET_NAME
        assert pset_model.ifc_id == pset_entity.id()  # Check ID matches

        # Verify properties within the model
        props = pset_model.properties
        assert len(props) == 1
        assert props[0].name == NEW_NORMAL_PROP_NAME
        assert props[0].value is not None
        assert isinstance(props[0].value, IfcValue)
        assert props[0].value.value == NEW_NORMAL_PROP_VALUE  # Check raw value
        assert props[0].ifc_id == prop_entity.id()  # Check property ID matches

    def test_get_properties_from_quantity_set(self, pset_adapter: IosPSetAdapter):
        # Note: This PSet is actually an IfcElementQuantity
        props = pset_adapter.get_properties(KNOWN_PSET_QTO_ID_ON_ELEMENT)
        assert props is not None
        assert isinstance(props, list)
        assert len(props) > 0  # Qto_WallBaseQuantities has quantities
        # Check if the known Quantity (treated as property here) is present
        assert any(p.name == KNOWN_PROP_QTO_NAME_IN_PSET for p in props)
        # The adapter should wrap IfcQuantityLength etc. as IfcProperty
        assert all(isinstance(p, IfcProperty) for p in props)

    def test_get_properties_from_normal_pset(self, pset_adapter: IosPSetAdapter):
        # This is a normal IfcPropertySet
        props = pset_adapter.get_properties(KNOWN_NORMAL_PSET_ID)
        assert props is not None
        assert isinstance(props, list)
        assert len(props) > 0
        # Check if the known Property is present
        assert any(p.name == KNOWN_NORMAL_PROP_NAME for p in props)
        assert all(isinstance(p, IfcProperty) for p in props)

        # Find the property and check its value
        prop = next((p for p in props if p.name == KNOWN_NORMAL_PROP_NAME), None)
        assert prop is not None
        assert prop.value is not None
        assert isinstance(prop.value, IfcValue)
        assert prop.value.value == KNOWN_NORMAL_PROP_VALUE  # Check raw value

    def test_get_properties_non_existent_pset(self, pset_adapter: IosPSetAdapter):
        # Getting properties of non-existent pset should raise error
        with pytest.raises(IfcAdapterError):
            _ = pset_adapter.get_properties(NON_EXISTENT_ID)

    def test_remove_property_non_existent_prop(self, pset_adapter: IosPSetAdapter):
        success = pset_adapter.remove_property_from_pset(
            KNOWN_PSET_QTO_ID_ON_ELEMENT, NON_EXISTENT_PROP_NAME
        )
        assert success is False

    def test_remove_property_non_existent_pset(self, pset_adapter: IosPSetAdapter):
        # Removing property from non-existent PSet should fail
        with pytest.raises(IfcAdapterError):
            _ = pset_adapter.remove_property_from_pset(NON_EXISTENT_ID, KNOWN_PROP_QTO_NAME_IN_PSET)

    def test_get_objects_of_pset(self, pset_adapter: IosPSetAdapter):  # Renamed method for clarity
        elements = pset_adapter.get_objects_of(KNOWN_PSET_QTO_ID_ON_ELEMENT)
        assert elements is not None
        assert isinstance(elements, list)
        # Check if the known element is associated with this PSet (Quantity Set)
        assert any(elem.ifc_id == KNOWN_ELEMENT_ID for elem in elements)
        assert all(isinstance(e, IfcObject) for e in elements)

    def test_get_objects_of_non_existent_pset(self, pset_adapter: IosPSetAdapter):  # Renamed method
        # Getting elements for a non-existent PSet ID should raise error
        with pytest.raises(IfcAdapterError):
            _ = pset_adapter.get_objects_of(NON_EXISTENT_ID)
