# tests/ios/test_ios_pset_adapter.py
import ifcopenshell
import pytest

from pyfc.errors import IfcAdapterError
from pyfc.ios import IosModelContext, IosPSetAdapter
from pyfc.models import (
    IfcObject,
    IfcProperty,
    IfcPSet,
    IfcUnitType,
    IfcValue,
    IfcValueType,
    Property,
    value_factory,
)

from .conftest import (
    KNOWN_ELEMENT_ID,
    KNOWN_NORMAL_PROP_NAME,
    KNOWN_NORMAL_PROP_VALUE,
    KNOWN_NORMAL_PSET_ID,
    KNOWN_PROP_NAME_IN_PSET,
    KNOWN_PSET_ID_ON_ELEMENT,
    NEW_NORMAL_PROP_NAME,
    NEW_NORMAL_PROP_VALUE,
    NEW_NORMAL_PSET_NAME,
    NEW_PROP_NAME,
    NEW_PROP_VALUE,
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
            NominalValue=ifc_context.create_entity(
                "IfcText", wrappedValue=NEW_NORMAL_PROP_VALUE
            ),
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
        props = pset_adapter.get_properties(KNOWN_PSET_ID_ON_ELEMENT)
        assert props is not None
        assert isinstance(props, list)
        assert len(props) > 0  # Qto_WallBaseQuantities has quantities
        # Check if the known Quantity (treated as property here) is present
        assert any(p.name == KNOWN_PROP_NAME_IN_PSET for p in props)
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

    def test_add_quantity_to_qto_set(
        self, pset_adapter: IosPSetAdapter, ifc_context: IosModelContext
    ):
        """Test adding a valid quantity (e.g., Length) to an IfcElementQuantity."""
        qto_set_id = KNOWN_PSET_ID_ON_ELEMENT  # This is an IfcElementQuantity
        new_quantity_name = "NewTestLength"
        new_quantity_value = 12.5

        # Create IfcValue first using the factory
        ifc_val = value_factory.create_length(new_quantity_value)

        # Create Property object using ifc_value argument
        prop_to_add = Property(name=new_quantity_name, ifc_value=ifc_val)

        added_prop = pset_adapter.add_property(qto_set_id, prop_to_add)

        assert added_prop is not None
        assert isinstance(added_prop, IfcProperty)
        assert added_prop.name == new_quantity_name
        assert added_prop.value is not None
        assert isinstance(added_prop.value, IfcValue)
        assert added_prop.value.value == pytest.approx(new_quantity_value)
        assert added_prop.value.value_type == IfcValueType.REAL
        assert added_prop.value.unit_type == IfcUnitType.LENGTH

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None
        ifc_context.save(file_path)

        new_ifc_context = IosModelContext.open(file_path)
        new_pset_adapter = IosPSetAdapter(new_ifc_context)
        qto_set = new_pset_adapter.get_by_id(qto_set_id)
        assert qto_set is not None
        new_prop = qto_set.prop_by_name(new_quantity_name)
        assert new_prop is not None
        assert new_prop.value is not None
        assert isinstance(new_prop.value, IfcValue)
        assert new_prop.value.value == pytest.approx(new_quantity_value)
        assert new_prop.value.unit_type == IfcUnitType.LENGTH

    def test_add_area_quantity_to_qto_set(
        self, pset_adapter: IosPSetAdapter, ifc_context: IosModelContext
    ):
        """Test adding a valid area quantity to an IfcElementQuantity."""
        qto_set_id = KNOWN_PSET_ID_ON_ELEMENT  # This is an IfcElementQuantity
        new_quantity_name = "NewTestArea"
        new_quantity_value = 55.75

        # Create IfcValue first using the factory
        ifc_val = value_factory.create_area(new_quantity_value)

        # Create Property object using ifc_value argument
        prop_to_add = Property(name=new_quantity_name, ifc_value=ifc_val)

        added_prop = pset_adapter.add_property(qto_set_id, prop_to_add)

        assert added_prop is not None
        assert isinstance(added_prop, IfcProperty)
        assert added_prop.name == new_quantity_name
        assert added_prop.value is not None
        assert isinstance(added_prop.value, IfcValue)
        assert added_prop.value.value == pytest.approx(new_quantity_value)
        assert added_prop.value.value_type == IfcValueType.REAL
        assert added_prop.value.unit_type == IfcUnitType.AREA

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None
        ifc_context.save(file_path)

        new_ifc_context = IosModelContext.open(file_path)
        new_pset_adapter = IosPSetAdapter(new_ifc_context)
        qto_set = new_pset_adapter.get_by_id(qto_set_id)
        assert qto_set is not None
        new_prop = qto_set.prop_by_name(new_quantity_name)
        assert new_prop is not None
        assert new_prop.value is not None
        assert isinstance(new_prop.value, IfcValue)
        assert new_prop.value.value == pytest.approx(new_quantity_value)
        assert new_prop.value.unit_type == IfcUnitType.AREA
        # Additionally check the underlying IFC entity's unit if possible/needed
        prop_entity = new_ifc_context.ifc_by_id(new_prop.ifc_id)
        assert prop_entity is not None
        assert prop_entity.is_a("IfcQuantityArea")
        assert hasattr(prop_entity, "AreaValue")
        assert prop_entity.AreaValue == pytest.approx(new_quantity_value)
        assert hasattr(prop_entity, "Unit")
        assert prop_entity.Unit is not None
        assert prop_entity.Unit.is_a("IfcSIUnit")
        assert prop_entity.Unit.UnitType == "AREAUNIT"

    def test_add_normal_property_to_normal_pset(
        self, pset_adapter: IosPSetAdapter, ifc_context: IosModelContext
    ):
        """Test adding a standard property (no unit) to an IfcPropertySet."""
        pset_id = KNOWN_NORMAL_PSET_ID  # This is an IfcPropertySet
        new_prop_name = "NewNormalProp"
        new_prop_value = "Some Text Value"

        # Create IfcValue first using the factory
        ifc_val = value_factory.create_text(new_prop_value)

        # Create Property object using ifc_value argument
        prop_to_add = Property(name=new_prop_name, ifc_value=ifc_val)

        added_prop = pset_adapter.add_property(pset_id, prop_to_add)

        assert added_prop is not None
        assert isinstance(added_prop, IfcProperty)
        assert added_prop.name == new_prop_name
        assert added_prop.value is not None
        assert isinstance(added_prop.value, IfcValue)
        assert added_prop.value.value == new_prop_value
        assert added_prop.value.value_type == IfcValueType.TEXT
        assert added_prop.value.unit_type == IfcUnitType.UNKNOWN

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None
        ifc_context.save(file_path)

        new_ifc_context = IosModelContext.open(file_path)
        new_pset_adapter = IosPSetAdapter(new_ifc_context)
        pset = new_pset_adapter.get_by_id(pset_id)
        assert pset is not None
        new_prop = pset.prop_by_name(new_prop_name)
        assert new_prop is not None
        assert new_prop.value is not None
        assert isinstance(new_prop.value, IfcValue)
        assert new_prop.value.value == new_prop_value
        assert new_prop.value.unit_type == IfcUnitType.UNKNOWN

    def test_add_property_with_unit_to_normal_pset(
        self, pset_adapter: IosPSetAdapter, ifc_context: IosModelContext
    ):
        """Test adding a property with a unit to a normal IfcPropertySet."""
        pset_id = KNOWN_NORMAL_PSET_ID  # This is an IfcPropertySet
        new_prop_name = "PropWithUnit"
        new_prop_value = 25.5
        unit = IfcUnitType.MASS

        # Create IfcValue first using the factory
        ifc_val = value_factory.create(
            new_prop_value, unit_type=unit
        )  # Factory infers REAL type

        # Create Property object using ifc_value argument
        prop_to_add = Property(name=new_prop_name, ifc_value=ifc_val)

        # This should succeed, potentially with a warning logged by the adapter
        added_prop = pset_adapter.add_property(pset_id, prop_to_add)

        assert added_prop is not None
        assert isinstance(added_prop, IfcProperty)
        assert added_prop.name == new_prop_name
        assert added_prop.value is not None
        assert isinstance(added_prop.value, IfcValue)
        assert added_prop.value.value == pytest.approx(new_prop_value)
        assert added_prop.value.value_type == IfcValueType.REAL
        assert (
            added_prop.value.unit_type == unit
        )  # Check if unit is correctly assigned/retrieved

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None
        ifc_context.save(file_path)

        new_ifc_context = IosModelContext.open(file_path)
        new_pset_adapter = IosPSetAdapter(new_ifc_context)
        pset = new_pset_adapter.get_by_id(pset_id)
        assert pset is not None
        new_prop = pset.prop_by_name(new_prop_name)
        assert new_prop is not None
        assert new_prop.value is not None
        assert isinstance(new_prop.value, IfcValue)
        assert new_prop.value.value == pytest.approx(new_prop_value)
        # Verify the unit was persisted and is read back correctly
        assert new_prop.value.unit_type == unit
        # Additionally check the underlying IFC entity's unit if possible/needed
        prop_entity = new_ifc_context.ifc_by_id(new_prop.ifc_id)
        assert prop_entity is not None
        assert hasattr(prop_entity, "Unit")
        assert prop_entity.Unit is not None
        assert prop_entity.Unit.is_a("IfcSIUnit")  # Assuming SI Unit was created
        assert (
            prop_entity.Unit.UnitType == "MASSUNIT"
        )  # Check the specific IFC unit type

    def test_add_normal_property_to_qto_set_raises_error(
        self, pset_adapter: IosPSetAdapter
    ):
        """Test that adding a standard property (no unit) to a QtoSet raises an error."""
        qto_set_id = KNOWN_PSET_ID_ON_ELEMENT  # This is an IfcElementQuantity
        ifc_val = value_factory.create_text("Some Value")
        prop_to_add = Property(name="InvalidNormalPropInQto", ifc_value=ifc_val)

        with pytest.raises(IfcAdapterError) as excinfo:
            _ = pset_adapter.add_property(qto_set_id, prop_to_add)
            excinfo.match("Quantities must have units (or be IfcQuantityCount)")

    def test_add_property_non_existent_pset(self, pset_adapter: IosPSetAdapter):
        # Create IfcValue first
        ifc_val = value_factory.create_text(NEW_PROP_VALUE)
        # Create Property object
        prop_to_add = Property(name=NEW_PROP_NAME, ifc_value=ifc_val)
        with pytest.raises(IfcAdapterError):
            _ = pset_adapter.add_property(NON_EXISTENT_ID, prop_to_add)

    def test_remove_property(
        self, pset_adapter: IosPSetAdapter, ifc_context: IosModelContext
    ):
        # Note: Removing an IfcQuantityLength via the property name
        success = pset_adapter.remove_property(
            KNOWN_PSET_ID_ON_ELEMENT, KNOWN_PROP_NAME_IN_PSET
        )
        assert success is True

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)

        ifc_file = ifcopenshell.open(file_path)
        assert isinstance(ifc_file, ifcopenshell.file)

        # New variable to avoid error in pytest fixture
        new_ifc_context = IosModelContext(ifc_file, file_path)
        new_pset_adapter = IosPSetAdapter(
            new_ifc_context
        )  # Recreate adapter with new context

        pset = new_pset_adapter.get_by_id(KNOWN_PSET_ID_ON_ELEMENT)
        assert pset is not None
        removed_prop = pset.prop_by_name(KNOWN_PROP_NAME_IN_PSET)
        assert removed_prop is None

    def test_remove_property_non_existent_prop(self, pset_adapter: IosPSetAdapter):
        success = pset_adapter.remove_property(
            KNOWN_PSET_ID_ON_ELEMENT, NON_EXISTENT_PROP_NAME
        )
        assert success is False

    def test_remove_property_non_existent_pset(self, pset_adapter: IosPSetAdapter):
        # Removing property from non-existent PSet should fail
        with pytest.raises(IfcAdapterError):
            _ = pset_adapter.remove_property(NON_EXISTENT_ID, KNOWN_PROP_NAME_IN_PSET)

    def test_get_objects_of_pset(
        self, pset_adapter: IosPSetAdapter
    ):  # Renamed method for clarity
        elements = pset_adapter.get_objects_of(KNOWN_PSET_ID_ON_ELEMENT)
        assert elements is not None
        assert isinstance(elements, list)
        # Check if the known element is associated with this PSet (Quantity Set)
        assert any(elem.ifc_id == KNOWN_ELEMENT_ID for elem in elements)
        assert all(isinstance(e, IfcObject) for e in elements)

    def test_get_objects_of_non_existent_pset(
        self, pset_adapter: IosPSetAdapter
    ):  # Renamed method
        # Getting elements for a non-existent PSet ID should raise error
        with pytest.raises(IfcAdapterError):
            _ = pset_adapter.get_objects_of(NON_EXISTENT_ID)
