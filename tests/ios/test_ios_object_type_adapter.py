# tests/ios/test_ios_object_type_adapter.py
from pyfc.ios import IosObjectTypeAdapter
from pyfc.models import IfcObject, IfcObjectType

from tests.conftest import (
    KNOWN_ELEMENT_ID,
    KNOWN_TYPE_GUID,
    KNOWN_TYPE_ID,
    NON_EXISTENT_ID,
)


# --- Tests for IosObjectTypeAdapter ---
class TestIosObjectTypeAdapter:
    def test_get_instances_of_type(self, object_type_adapter: IosObjectTypeAdapter):
        elements = object_type_adapter.get_instances_of(KNOWN_TYPE_ID)
        assert elements is not None
        assert isinstance(elements, list)
        assert len(elements) >= 1  # IfcWallType #66 defines IfcWall #68
        assert any(
            elem.ifc_id == KNOWN_ELEMENT_ID for elem in elements
        )  # Check if known element is found
        assert all(isinstance(e, IfcObject) for e in elements)

    def test_get_instances_of_type_non_existent_type(
        self, object_type_adapter: IosObjectTypeAdapter
    ):
        # Should not raise error, just return empty list if type doesn't exist
        # or has no instances
        elements = object_type_adapter.get_instances_of(NON_EXISTENT_ID)
        assert elements == []

    def test_get_type_psets(self, object_type_adapter: IosObjectTypeAdapter):
        # IfcWallType #66 does not have Psets/Quantities in sample.ifc
        psets = object_type_adapter.get_psets(KNOWN_TYPE_ID)
        assert psets is not None
        assert isinstance(psets, list)
        assert len(psets) == 0  # Expecting no Psets on this type in the sample file

    def test_get_type_by_id(self, object_type_adapter: IosObjectTypeAdapter):
        obj_type = object_type_adapter.get_by_id(KNOWN_TYPE_ID)
        assert obj_type is not None
        assert isinstance(obj_type, IfcObjectType)
        assert obj_type.ifc_id == KNOWN_TYPE_ID
        assert obj_type.guid == KNOWN_TYPE_GUID
