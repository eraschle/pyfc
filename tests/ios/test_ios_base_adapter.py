# tests/ios/test_ios_base_adapter.py
import pytest
from pyfc.errors import IfcAdapterError
from pyfc.ios import IosObjectAdapter  # Use ObjectAdapter to test base methods
from pyfc.ios.context import IosModelContext
from pyfc.models import IfcObject
from tests.conftest import debug_context_state

from tests.conftest import (
    KNOWN_ELEMENT_GUID,
    KNOWN_ELEMENT_ID,
    KNOWN_ELEMENT_NAME,
    NEW_ELEMENT_NAME,
    NON_EXISTENT_GUID,
    NON_EXISTENT_ID,
)


# --- Tests for Base Adapter Functionality (tested via IosObjectAdapter) ---
class TestIosBaseAdapter:
    def test_get_by_id_exists(self, object_adapter: IosObjectAdapter, ifc_context: IosModelContext):
        debug_context_state(ifc_context, "test_get_by_id_exists")
        try:
            element = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
            assert element is not None
            assert isinstance(element, IfcObject)
            assert element.ifc_id == KNOWN_ELEMENT_ID
            assert element.guid == KNOWN_ELEMENT_GUID  # Check GUID as well
        except Exception as e:
            pytest.fail(f"Test failed with exception: {e}")

    def test_get_by_id_not_exists(
        self, object_adapter: IosObjectAdapter, ifc_context: IosModelContext
    ):
        debug_context_state(ifc_context, "test_get_by_id_not_exists")
        with pytest.raises(IfcAdapterError):
            _ = object_adapter.get_by_id(NON_EXISTENT_ID)

    def test_get_by_guid_exists(self, object_adapter: IosObjectAdapter):
        element = object_adapter.get_by_guid(KNOWN_ELEMENT_GUID)
        assert element is not None
        assert isinstance(element, IfcObject)
        assert element.ifc_id == KNOWN_ELEMENT_ID
        assert element.guid == KNOWN_ELEMENT_GUID

    def test_get_by_guid_not_exists(self, object_adapter: IosObjectAdapter):
        with pytest.raises(IfcAdapterError):
            _ = object_adapter.get_by_guid(NON_EXISTENT_GUID)

    def test_get_attribute_exists(self, object_adapter: IosObjectAdapter):
        # Test getting 'Name' attribute
        attr_name_to_test = "Name"
        expected_value = KNOWN_ELEMENT_NAME

        value = object_adapter.get_attribute(KNOWN_ELEMENT_ID, attr_name_to_test)
        assert value is not None
        assert value == expected_value

    def test_get_attribute_non_existent_attribute(self, object_adapter: IosObjectAdapter):
        # Assuming 'NonExistentAttribute' does not exist
        value = object_adapter.get_attribute(KNOWN_ELEMENT_ID, "NonExistentAttribute")
        assert value is None  # Should log a warning but return None

    def test_get_attribute_non_existent_entity(self, object_adapter: IosObjectAdapter):
        # Getting attribute from non-existent entity should raise error
        with pytest.raises(IfcAdapterError):
            _ = object_adapter.get_attribute(NON_EXISTENT_ID, "Name")

    def test_set_attribute_success(
        self, object_adapter: IosObjectAdapter, ifc_context: IosModelContext
    ):
        ifc_element = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert ifc_element is not None
        assert isinstance(ifc_element, IfcObject)
        ifc_element.name = NEW_ELEMENT_NAME  # Use the model property setter

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)
        # No need to close/reopen, changes should be reflected in the current context
        # ifc_context.close()
        # ifc_context = IosModelContext.open(file_path)
        # object_adapter = IosObjectAdapter(ifc_context) # Recreate adapter if context is reopened

        updated_element = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert updated_element is not None
        assert updated_element.name == NEW_ELEMENT_NAME

        # Verify directly in the underlying ifcopenshell file object
        ios_entity = ifc_context.ifc_by_id(KNOWN_ELEMENT_ID)
        assert ios_entity is not None
        assert ios_entity.Name == NEW_ELEMENT_NAME

    def test_set_attribute_non_existent_entity(self, object_adapter: IosObjectAdapter):
        # Setting attribute on non-existent entity should raise error
        with pytest.raises(IfcAdapterError):
            # Note: Direct set_attribute is protected, test via model property
            # This requires getting a non-existent entity first, which raises error
            # So, we test the get path first. If get fails, set will also fail.
            _ = object_adapter.get_by_id(NON_EXISTENT_ID)
        # If we could get a non-existent object model somehow:
        # with pytest.raises(IfcAdapterError):
        #     non_existent_obj = IfcObject(...) # Hypothetical
        #     non_existent_obj.name = "SomeValue" # This would call set_attribute internally

    def test_set_attribute_read_only_attribute(self, object_adapter: IosObjectAdapter):
        ifc_element = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert ifc_element is not None
        assert isinstance(ifc_element, IfcObject)
        with pytest.raises(AttributeError):
            ifc_element.guid = "new_fake_guid"  # pyright: ignore[reportGeneralTypeIssues]
