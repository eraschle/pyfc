# Check if the source IFC file exists at the start of the test session
import logging
import shutil
from pathlib import Path
from typing import Iterable

import pytest
from pyfc.adapters.objects import IObjectAdapter, IObjectTypeAdapter
from pyfc.adapters.properties import IPropertyAdapter, IPSetAdapter

from pyfc.ios.context import IosModelContext
from pyfc.ios.objects import IosObjectAdapter, IosObjectTypeAdapter
from pyfc.ios.properties import IosPropertyAdapter, IosPSetAdapter

# --- Project Imports ---
from pyfc.repository import IModelContext

# --- Constants ---
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
KNOWN_PSET_QTO_ID_ON_ELEMENT = 77  # ID of the IfcElementQuantity attached to the element
KNOWN_PSET_QTO_NAME_ON_ELEMENT = "Qto_WallBaseQuantities"  # Name of the IfcElementQuantity
KNOWN_PSET_QTO_ID = 77  # Added: Explicit ID for the Quantity Set (same as KNOWN_PSET_ID_ON_ELEMENT)
KNOWN_PSET_QTO_NAME = "Qto_WallBaseQuantities"  # Added: Explicit Name for the Quantity Set
# Property/Quantity: IfcQuantityLength #74 (within #77)
KNOWN_PROP_QTO_ID_IN_PSET = 74
KNOWN_PROP_QTO_NAME_IN_PSET = "Width"
KNOWN_PROP_QTO_VALUE_IN_PSET = 200.000000000079  # LengthValue from #74

# Property Set: IfcPropertySet #80 (related to #68 via #81)
KNOWN_NORMAL_PSET_ID = 80
KNOWN_NORMAL_PSET_NAME = "Test_PropertySet"
# Property: IfcPropertySingleValue #79 (within #80)
KNOWN_NORMAL_PROP_ID = 79  # ID of the IfcPropertySingleValue within the normal PSet
KNOWN_NORMAL_PROPERTY_ID = 79  # Added: Explicit ID for the normal property (KNOWN_NORMAL_PROP_ID)
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

BUILDING_ID_NO_TYPE = 6
# --- End of Constants ---


# --- Basic File Setup ---
ASSETS_DIR = Path(__file__).parent / "data"
IFC_SOURCE = ASSETS_DIR / "sample.ifc"

if not IFC_SOURCE.is_file():
    pytest.skip(f"Test IFC file not found at {IFC_SOURCE}", allow_module_level=True)


@pytest.fixture(scope="function")  # Use "function" scope for isolation
def test_ifc_file(tmp_path_factory: pytest.TempPathFactory) -> Iterable[Path]:
    """Copies the test IFC file to a temporary location for isolated testing."""
    temp_dir = tmp_path_factory.mktemp("ifc_test")
    temp_file = temp_dir / IFC_SOURCE.name
    shutil.copy(IFC_SOURCE, temp_file)
    # Verify the file was copied correctly
    assert temp_file.exists(), f"Test file was not copied to {temp_file}"
    assert temp_file.stat().st_size > 0, f"Test file at {temp_file} is empty"
    print(f"Test IFC file copied to: {temp_file} (size: {temp_file.stat().st_size} bytes)")
    yield temp_file
    # Teardown (implicit via tmp_path_factory)


# --- Parametrized Fixtures for Adapters ---
# List of adapter implementations to test
IMPLEMENTATIONS = [
    "ios",
]


def debug_context_state(context: IosModelContext | None, label: str = "Context") -> None:
    """Print debug information about the context state."""
    if not context:
        logging.debug(f"{label}: Context is None")
        return

    if not context.ifc_model:
        logging.debug(f"{label}: IFC model is None")
        return

    try:
        entity_count = len(context.ifc_model.by_type("IfcProduct"))
        project_info = context.get_project()
        file_path = context.file_path

        logging.debug(f"{label}: Model loaded with {entity_count} entities")
        if project_info:
            logging.debug(f"{label}: Project: {project_info.get('name', 'Unknown')}")
        if file_path:
            logging.debug(f"{label}: File path: {file_path}")
    except Exception as e:
        logging.debug(f"{label}: Error getting context state: {e}")


@pytest.fixture(params=IMPLEMENTATIONS, scope="function")
def ifc_context(request, test_ifc_file: Path) -> Iterable[IModelContext]:
    """
    Provides a model context for the requested implementation, parameterized.
    Opens the test IFC file within the specific context.
    Yields the context and handles potential cleanup.
    """
    impl_name = request.param
    context: IModelContext | None = None

    if impl_name == "ios":
        context = IosModelContext.open(str(test_ifc_file))

    # --- Add elif blocks for other implementations here ---
    # elif impl_name == "native":
    #    context = NativeModelContext.open(str(test_ifc_file))

    if context is None:
        pytest.fail(f"Failed to create context for implementation '{impl_name}'")

    try:
        debug_context_state(context, "model_context fixture setup")
        yield context
    finally:
        if context and hasattr(context, "close"):
            debug_context_state(context, "model_context fixture teardown")
            context.close()


@pytest.fixture(scope="function")
def object_adapter(ifc_context: IModelContext) -> IObjectAdapter:
    """Provides an IObjectAdapter instance for the current implementation context."""
    if isinstance(ifc_context, IosModelContext):
        return IosObjectAdapter(ifc_context)
    # --- Add elif blocks for other context types here ---
    # elif isinstance(model_context, NativeModelContext):
    #     return NativeObjectAdapter(model_context)
    else:
        raise TypeError(f"Unsupported context type for IObjectAdapter: {type(ifc_context)}")


@pytest.fixture(scope="function")
def object_type_adapter(ifc_context: IModelContext) -> IObjectTypeAdapter:
    """Provides an IObjectTypeAdapter instance for the current implementation context."""
    if isinstance(ifc_context, IosModelContext):
        return IosObjectTypeAdapter(ifc_context)
    # --- Add elif blocks for other context types here ---
    # elif isinstance(model_context, NativeModelContext):
    #     return NativeObjectTypeAdapter(model_context)
    else:
        raise TypeError(f"Unsupported context type for IObjectTypeAdapter: {type(ifc_context)}")


@pytest.fixture(scope="function")
def pset_adapter(ifc_context: IModelContext) -> IPSetAdapter:
    """Provides an IPSetAdapter instance for the current implementation context."""
    if isinstance(ifc_context, IosModelContext):
        return IosPSetAdapter(ifc_context)
    # --- Add elif blocks for other context types here ---
    # elif isinstance(model_context, NativeModelContext):
    #     return NativePSetAdapter(model_context)
    else:
        raise TypeError(f"Unsupported context type for IPSetAdapter: {type(ifc_context)}")


@pytest.fixture(scope="function")
def property_adapter(ifc_context: IModelContext) -> IPropertyAdapter:
    """Provides an IPropertyAdapter instance for the current implementation context."""
    if isinstance(ifc_context, IosModelContext):
        return IosPropertyAdapter(ifc_context)
    # --- Add elif blocks for other context types here ---
    # elif isinstance(model_context, NativeModelContext):
    #     return NativePropertyAdapter(model_context)
    else:
        raise TypeError(f"Unsupported context type for IPropertyAdapter: {type(ifc_context)}")
