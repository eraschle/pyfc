# tests/ios/conftest.py
import shutil
from collections.abc import Iterable
from pathlib import Path

import ifcopenshell
import pytest
from _pytest.tmpdir import TempPathFactory

from pyfc.ios import (
    IosObjectAdapter,
    IosObjectTypeAdapter,
    IosPropertyAdapter,
    IosPSetAdapter,
)
from pyfc.ios.context import IosModelContext

from . import debug_context_state  # Import from __init__.py

# --- Constants ---
# Assuming your test IFC file is in tests/data/
TEST_ASSETS_DIR = Path(__file__).parent.parent / "data"
# Use sample.ifc as the test source
TEST_IFC_SOURCE = TEST_ASSETS_DIR / "sample.ifc"

# --- Values from tests/data/sample.ifc ---
# Element: IfcWall #68
KNOWN_ELEMENT_ID = 68
KNOWN_ELEMENT_GUID = "0DyViLJJ175RvWQi1rE7a6"
KNOWN_ELEMENT_NAME = "Test Wall Element"
KNOWN_ELEMENT_TYPE = "IfcWall"  # Added: The IFC class name for element #68

# Type: IfcWallType #66 (related to #68 via #69)
KNOWN_TYPE_ID = 66
KNOWN_TYPE_GUID = "0_8SeeJGr948J4bU1RPXce"
KNOWN_TYPE_NAME = "Test Wall Type"

# PSet/Quantity: IfcElementQuantity #77 (related to #68 via #78)
KNOWN_PSET_ID_ON_ELEMENT = 77  # ID of the IfcElementQuantity attached to the element
KNOWN_PSET_NAME_ON_ELEMENT = "Qto_WallBaseQuantities"  # Name of the IfcElementQuantity
KNOWN_QTO_ID = (
    77  # Added: Explicit ID for the Quantity Set (same as KNOWN_PSET_ID_ON_ELEMENT)
)
KNOWN_QTO_NAME = "Qto_WallBaseQuantities"  # Added: Explicit Name for the Quantity Set

# Property/Quantity: IfcQuantityLength #74 (within #77)
KNOWN_PROP_ID_IN_PSET = 74
KNOWN_PROP_NAME_IN_PSET = "Width"
KNOWN_PROP_VALUE_IN_PSET = 200.000000000079  # LengthValue from #74

# Property Set: IfcPropertySet #80 (related to #68 via #81)
KNOWN_NORMAL_PSET_ID = 80
KNOWN_NORMAL_PSET_NAME = "Test_PropertySet"

# Property: IfcPropertySingleValue #79 (within #80)
KNOWN_NORMAL_PROP_ID = 79  # ID of the IfcPropertySingleValue within the normal PSet
KNOWN_NORMAL_PROPERTY_ID = (
    79  # Added: Explicit ID for the normal property (same as KNOWN_NORMAL_PROP_ID)
)
KNOWN_NORMAL_PROP_NAME = "TestProperty"
KNOWN_NORMAL_PROP_VALUE = "Test Value"

# New constants for tests with normal PropertySets
NEW_NORMAL_PSET_NAME = "Test_NewNormalPset"
NEW_NORMAL_PROP_NAME = "NormalTestProp"
NEW_NORMAL_PROP_VALUE = "Normal Test Value"

NON_EXISTENT_ID = 999999
NON_EXISTENT_GUID = "zzzzzzzzzzzzzzzzzzzzzz"
NON_EXISTENT_PSET_NAME = "Pset_DoesNotExist"
NON_EXISTENT_PROP_NAME = "PropDoesNotExist"

NEW_PSET_NAME = "Test_NewPset"
NEW_PROP_NAME = "Test_NewProp"
NEW_PROP_VALUE = "TestValue123"
NEW_PROP_NAME_2 = "Test_AnotherProp"
NEW_PROP_VALUE_2 = 42.5
UPDATED_PROP_VALUE = "UpdatedValue"
NEW_ELEMENT_NAME = "Updated Test Wall Name"

# Building ID from sample.ifc (used for testing elements without types)
BUILDING_ID_NO_TYPE = 6
# --- End of Constants ---


# Check if the source IFC file exists at the start of the test session
if not TEST_IFC_SOURCE.is_file():
    pytest.skip(
        f"Test IFC file not found at {TEST_IFC_SOURCE}", allow_module_level=True
    )


@pytest.fixture(scope="function")  # Use "function" scope for isolation
def test_ifc_file(tmp_path_factory: TempPathFactory) -> Iterable[Path]:
    """Copies the test IFC file to a temporary location for isolated testing."""
    # Create a unique temporary directory for each test function
    temp_dir = tmp_path_factory.mktemp("ifc_test")
    temp_file = temp_dir / TEST_IFC_SOURCE.name
    shutil.copy(TEST_IFC_SOURCE, temp_file)
    # Verify the file was copied correctly
    assert temp_file.exists(), f"Test file was not copied to {temp_file}"
    assert temp_file.stat().st_size > 0, f"Test file at {temp_file} is empty"
    print(
        f"Test IFC file copied to: {temp_file} (size: {temp_file.stat().st_size} bytes)"
    )
    yield temp_file
    # Teardown happens automatically when the fixture scope ends


@pytest.fixture
def ifc_context(test_ifc_file: Path) -> Iterable[IosModelContext]:
    """Provides an opened IfcModelContext for the copied test file."""
    ifc_file = None
    context = None
    try:
        ifc_file = ifcopenshell.open(str(test_ifc_file))
        assert isinstance(ifc_file, ifcopenshell.file)
        context = IosModelContext(ifc_file, test_ifc_file)
        # Verify the context is properly initialized
        assert context.ifc_model is not None, (
            f"IFC model was not loaded correctly from {test_ifc_file}"
        )
        assert context.file_path is not None, (
            f"File path is None in context for {test_ifc_file}"
        )
        debug_context_state(context, "ifc_context fixture setup")
        yield context
    finally:
        if context:
            debug_context_state(context, "ifc_context fixture teardown")
            context.close()  # Ensure the file handle is released


@pytest.fixture
def object_adapter(ifc_context: IosModelContext) -> IosObjectAdapter:
    """Provides an IosObjectAdapter instance."""
    adapter = IosObjectAdapter(ifc_context)
    # Verify the adapter is properly initialized
    assert adapter.context is not None, "Adapter context is None"
    assert adapter.context.ifc_model is not None, "Adapter's IFC model is None"
    return adapter


@pytest.fixture
def object_type_adapter(ifc_context: IosModelContext) -> IosObjectTypeAdapter:
    """Provides an IosObjectTypeAdapter instance."""
    return IosObjectTypeAdapter(ifc_context)


@pytest.fixture
def pset_adapter(ifc_context: IosModelContext) -> IosPSetAdapter:
    """Provides an IosPSetAdapter instance."""
    return IosPSetAdapter(ifc_context)


@pytest.fixture
def property_adapter(ifc_context: IosModelContext) -> IosPropertyAdapter:
    """Provides an IosPropertyAdapter instance."""
    return IosPropertyAdapter(ifc_context)
