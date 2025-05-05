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
    ValueFactory,
)

from tests.conftest import (
    KNOWN_NORMAL_PROP_NAME,
    KNOWN_NORMAL_PROP_VALUE,
    KNOWN_NORMAL_PSET_ID,
    KNOWN_PROP_QTO_NAME_IN_PSET,
    KNOWN_PROP_QTO_VALUE_IN_PSET,
    KNOWN_PSET_QTO_ID,
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
    qto_set = ifc_context.ifc_by_id(KNOWN_PSET_QTO_ID)
    if not qto_set or not qto_set.is_a("IfcElementQuantity"):
        pytest.fail(f"Could not find QTO set with ID {KNOWN_PSET_QTO_ID}")

    # Find the specific quantity property within the QTO set
    for quantity in qto_set.Quantities:
        if quantity.Name == KNOWN_PROP_QTO_NAME_IN_PSET:
            return quantity.id()
    pytest.fail(
        f"Could not find quantity '{KNOWN_PROP_QTO_NAME_IN_PSET}' in QTO set {KNOWN_PSET_QTO_ID}"
    )


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
        value_to_set = ValueFactory.create(
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

    def test_get_quantity_value(self, property_adapter: IosPropertyAdapter, known_quantity_id: int):
        ifc_value = property_adapter.get_value(known_quantity_id)
        assert ifc_value is not None
        assert isinstance(ifc_value, IfcValue)
        assert isinstance(ifc_value.value, (int, float))
        assert ifc_value.value == pytest.approx(KNOWN_PROP_QTO_VALUE_IN_PSET)
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
        value_to_set = ValueFactory.create(new_value, value_type=IfcValueType.TEXT)
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
        value_to_set = ValueFactory.create("Any Value", value_type=IfcValueType.TEXT)
        with pytest.raises(IfcAdapterError):
            _ = property_adapter.set_value(NON_EXISTENT_ID, value_to_set)

    # Add more tests:
    # - Setting value with incorrect type (e.g., text to a quantity) -> Should fail or coerce?
    # - Setting value with incorrect unit type (e.g., AREA unit to LENGTH quantity) -> Should fail?
    # - Setting value for properties with complex types if supported (e.g., IfcMeasureValue)
    # - Test setting boolean, integer values specifically
