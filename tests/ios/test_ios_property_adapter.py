import pytest

from pyfc.errors import IfcAdapterError
from pyfc.ios import (
    IosModelContext,
    IosObjectAdapter,
    IosPropertyAdapter,
    IosPSetAdapter,
)
from pyfc.models import (
    IfcPrefix,
    IfcUnitType,
    IfcValue,
    IfcValueType,
    Property,
    PropertySet,
    value_factory,
)

from .conftest import (
    KNOWN_ELEMENT_ID,
    KNOWN_NORMAL_PROP_NAME,
    KNOWN_NORMAL_PROP_VALUE,
    KNOWN_NORMAL_PSET_ID,
    KNOWN_PROP_NAME_IN_PSET,
    KNOWN_PROP_VALUE_IN_PSET,
    KNOWN_QTO_ID,
    NON_EXISTENT_ID,
)


@pytest.fixture
def property_adapter(ifc_context: IosModelContext) -> IosPropertyAdapter:
    """Fixture to provide an IosPropertyAdapter instance."""
    return IosPropertyAdapter(ifc_context)


@pytest.fixture
def object_adapter(ifc_context: IosModelContext) -> IosObjectAdapter:
    """Fixture to provide an IosObjectAdapter instance."""
    return IosObjectAdapter(ifc_context)


@pytest.fixture
def pset_adapter(ifc_context: IosModelContext) -> IosPSetAdapter:
    """Fixture to provide an IosPSetAdapter instance."""
    return IosPSetAdapter(ifc_context)


@pytest.fixture
def known_quantity_id(ifc_context: IosModelContext) -> int:
    """Fixture to get the ID of a known quantity property (e.g., Width)."""
    # Find the QTO set first
    qto_set = ifc_context.ifc_by_id(KNOWN_QTO_ID)
    if not qto_set or not qto_set.is_a("IfcElementQuantity"):
        pytest.fail(f"Could not find QTO set with ID {KNOWN_QTO_ID}")

    # Find the specific quantity property within the QTO set
    for quantity in qto_set.Quantities:
        if quantity.Name == KNOWN_PROP_NAME_IN_PSET:
            return quantity.id()
    pytest.fail(f"Could not find quantity '{KNOWN_PROP_NAME_IN_PSET}' in QTO set {KNOWN_QTO_ID}")


@pytest.fixture
def known_normal_property_id(ifc_context: IosModelContext) -> int:
    """Fixture to get the ID of a known normal property."""
    pset = ifc_context.ifc_by_id(KNOWN_NORMAL_PSET_ID)
    if not pset or not pset.is_a("IfcPropertySet"):
        pytest.fail(f"Could not find PSet with ID {KNOWN_NORMAL_PSET_ID}")

    for prop in pset.HasProperties:
        if prop.Name == KNOWN_NORMAL_PROP_NAME:
            return prop.id()
    pytest.fail(
        f"Could not find property '{KNOWN_NORMAL_PROP_NAME}' in PSet {KNOWN_NORMAL_PSET_ID}"
    )


class TestIosPropertyAdapter:
    def test_set_quantity_value_success(
        self,
        property_adapter: IosPropertyAdapter,
        known_quantity_id: int,
        ifc_context: IosModelContext,
    ):
        """Test setting a value for a quantity property."""
        # Get the current value
        current_ifc_value = property_adapter.get_value(known_quantity_id)
        assert current_ifc_value is not None
        assert isinstance(current_ifc_value, IfcValue)
        assert isinstance(current_ifc_value.value, (int, float))
        current_value = current_ifc_value.value  # Extract raw value

        # Set a new value (different from the current one)
        new_value = current_value + 5.0
        # Create IfcValue object to pass to set_value
        value_to_set = value_factory.create(
            new_value, value_type=IfcValueType.REAL, unit_type=IfcUnitType.LENGTH
        )
        success = property_adapter.set_value(
            known_quantity_id,
            value_to_set,  # Pass IfcValue
        )
        assert success is True

        # Verify the value was updated in memory
        updated_ifc_value = property_adapter.get_value(known_quantity_id)
        assert updated_ifc_value is not None
        assert isinstance(updated_ifc_value, IfcValue)
        assert updated_ifc_value.value == pytest.approx(new_value)
        assert updated_ifc_value.value_type == IfcValueType.REAL
        assert updated_ifc_value.unit_type == IfcUnitType.LENGTH

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)
        new_context = IosModelContext.open(file_path)
        property_adapter = IosPropertyAdapter(new_context)  # Recreate adapter

        # Verify the value was persisted
        persisted_ifc_value = property_adapter.get_value(known_quantity_id)
        assert persisted_ifc_value is not None
        assert isinstance(persisted_ifc_value, IfcValue)
        assert persisted_ifc_value.value == pytest.approx(new_value)
        assert persisted_ifc_value.unit_type == IfcUnitType.LENGTH

    def test_set_value_different_types(
        self,
        property_adapter: IosPropertyAdapter,
        object_adapter: IosObjectAdapter,
        ifc_context: IosModelContext,
    ):
        # Create a new PropertySet with different property types
        props = [
            Property(
                name="TextProp",
                ifc_value=value_factory.create("Text Value", IfcValueType.TEXT),
            ),
            Property(name="IntProp", ifc_value=value_factory.create(42, IfcValueType.INTEGER)),
            Property(name="RealProp", ifc_value=value_factory.create(3.14, IfcValueType.REAL)),
            Property(
                name="BoolProp",
                ifc_value=value_factory.create(True, IfcValueType.BOOLEAN),
            ),
        ]
        pset_data = PropertySet(name="Test_MultiTypePset", properties=props)

        # Add the PSet to a known object
        added_pset = object_adapter.add_pset(KNOWN_ELEMENT_ID, pset_data)
        assert added_pset is not None
        assert len(added_pset.properties) == 4

        # Get the IDs of the newly created properties
        text_prop = added_pset.prop_by_name("TextProp")
        int_prop = added_pset.prop_by_name("IntProp")
        real_prop = added_pset.prop_by_name("RealProp")
        bool_prop = added_pset.prop_by_name("BoolProp")
        assert text_prop is not None
        assert int_prop is not None
        assert real_prop is not None
        assert bool_prop is not None

        # Change property values using property_adapter
        success1 = property_adapter.set_value(
            text_prop.ifc_id, value_factory.create("Updated Text", IfcValueType.TEXT)
        )
        success2 = property_adapter.set_value(
            int_prop.ifc_id, value_factory.create(99, IfcValueType.INTEGER)
        )
        success3 = property_adapter.set_value(
            real_prop.ifc_id, value_factory.create(2.71828, IfcValueType.REAL)
        )
        success4 = property_adapter.set_value(
            bool_prop.ifc_id, value_factory.create(False, IfcValueType.BOOLEAN)
        )

        assert success1 is True
        assert success2 is True
        assert success3 is True
        assert success4 is True

        updated_text_value = property_adapter.get_value(text_prop.ifc_id)
        assert updated_text_value is not None
        assert updated_text_value.value == "Updated Text"
        assert updated_text_value.value_type == IfcValueType.TEXT

        updated_int_value = property_adapter.get_value(int_prop.ifc_id)
        assert updated_int_value is not None
        assert updated_int_value.value == 99
        assert updated_int_value.value_type == IfcValueType.INTEGER

        updated_real_value = property_adapter.get_value(real_prop.ifc_id)
        assert updated_real_value is not None
        assert updated_real_value.value == pytest.approx(2.71828)
        assert updated_real_value.value_type == IfcValueType.REAL

        updated_bool_value = property_adapter.get_value(bool_prop.ifc_id)
        assert updated_bool_value is not None
        assert updated_bool_value.value is False
        # Erwarte LOGICAL, da der Schreibprozess zu IfcLogical standardisiert
        assert updated_bool_value.value_type == IfcValueType.LOGICAL

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)
        new_context = IosModelContext.open(file_path)
        prop_adapter_reloaded = IosPropertyAdapter(new_context)

        persisted_text = prop_adapter_reloaded.get_value(text_prop.ifc_id)
        assert persisted_text is not None
        persisted_int = prop_adapter_reloaded.get_value(int_prop.ifc_id)
        assert persisted_int is not None
        persisted_real = prop_adapter_reloaded.get_value(real_prop.ifc_id)
        assert persisted_real is not None
        persisted_bool = prop_adapter_reloaded.get_value(bool_prop.ifc_id)
        assert persisted_bool is not None

        assert persisted_text.value == "Updated Text"
        assert persisted_int.value == 99
        assert persisted_real.value == pytest.approx(2.71828)
        assert persisted_bool.value is False

    def test_get_quantity_value(self, property_adapter: IosPropertyAdapter, known_quantity_id: int):
        ifc_value = property_adapter.get_value(known_quantity_id)
        assert ifc_value is not None
        assert isinstance(ifc_value, IfcValue)
        assert isinstance(ifc_value.value, (int, float))
        assert ifc_value.value == pytest.approx(KNOWN_PROP_VALUE_IN_PSET)
        assert ifc_value.value_type == IfcValueType.REAL  # Or INTEGER depending on sample
        assert ifc_value.unit_type == IfcUnitType.LENGTH
        assert ifc_value.prefix == IfcPrefix.NONE

    def test_get_normal_property_value(
        self, property_adapter: IosPropertyAdapter, known_normal_property_id: int
    ):
        ifc_value = property_adapter.get_value(known_normal_property_id)
        assert ifc_value is not None
        assert isinstance(ifc_value, IfcValue)
        assert ifc_value.value == KNOWN_NORMAL_PROP_VALUE
        assert ifc_value.value_type == IfcValueType.TEXT  # Based on sample file
        assert ifc_value.unit_type == IfcUnitType.UNKNOWN
        assert ifc_value.prefix == IfcPrefix.NONE

    def test_get_value_non_existent(self, property_adapter: IosPropertyAdapter):
        with pytest.raises(IfcAdapterError):
            _ = property_adapter.get_value(NON_EXISTENT_ID)

    def test_set_normal_property_value_success(
        self,
        property_adapter: IosPropertyAdapter,
        known_normal_property_id: int,
        ifc_context: IosModelContext,
    ):
        new_value = "Updated Test Value"
        # Pass IfcValue
        value_to_set = value_factory.create(new_value, value_type=IfcValueType.TEXT)
        success = property_adapter.set_value(known_normal_property_id, value_to_set)
        assert success is True

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)
        new_context = IosModelContext.open(file_path)
        property_adapter = IosPropertyAdapter(new_context)

        updated_value = property_adapter.get_value(known_normal_property_id)
        assert updated_value is not None
        assert isinstance(updated_value, IfcValue)
        assert updated_value.value == new_value
        assert updated_value.value_type == IfcValueType.TEXT

    def test_set_value_non_existent(self, property_adapter: IosPropertyAdapter):
        value_to_set = value_factory.create("Any Value", value_type=IfcValueType.TEXT)
        with pytest.raises(IfcAdapterError):
            _ = property_adapter.set_value(NON_EXISTENT_ID, value_to_set)

    # Add more tests:
    # - Setting value with incorrect type (e.g., text to a quantity) -> Should fail or coerce?
    # - Setting value with incorrect unit type (e.g., AREA unit to LENGTH quantity) -> Should fail?
    # - Setting value for properties with complex types if supported (e.g., IfcMeasureValue)
    # - Test setting boolean, integer values specifically
