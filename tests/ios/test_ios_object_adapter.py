import pytest

from pyfc.errors import IfcAdapterError
from pyfc.ios import IosObjectAdapter
from pyfc.ios.context import IosModelContext
from pyfc.models import (
    IfcObject,
    IfcObjectType,
    IfcProperty,
    IfcPSet,
)
from pyfc.models.value import (
    IfcPrefix,
    IfcUnitType,
    IfcValue,
    IfcValueType,
)

from tests.conftest import (
    BUILDING_ID_NO_TYPE,
    KNOWN_ELEMENT_ID,
    KNOWN_ELEMENT_NAME,
    KNOWN_NORMAL_PROP_NAME,
    KNOWN_NORMAL_PROP_VALUE,
    KNOWN_NORMAL_PSET_ID,
    KNOWN_NORMAL_PSET_NAME,
    NON_EXISTENT_ID,
)


@pytest.fixture
def object_adapter(ifc_context: IosModelContext) -> IosObjectAdapter:
    """Fixture to provide an IosObjectAdapter instance."""
    return IosObjectAdapter(ifc_context)


class TestIosObjectAdapterInfo:
    def test_get_object_info_success(self, object_adapter: IosObjectAdapter):
        """Test retrieving basic information for a known object using get_by_id."""
        obj_model = object_adapter.get_by_id(KNOWN_ELEMENT_ID)  # Use get_by_id
        assert obj_model is not None
        assert isinstance(obj_model, IfcObject)
        assert obj_model.ifc_id == KNOWN_ELEMENT_ID
        assert obj_model.name == KNOWN_ELEMENT_NAME  # Access model property
        # Access object type via model property
        obj_type = obj_model.object_type
        assert obj_type is not None
        assert isinstance(obj_type, IfcObjectType)
        # Check underlying IFC type name if needed (requires context access or different approach)
        # underlying_entity = object_adapter.context.ifc_by_id(KNOWN_ELEMENT_ID)
        # assert underlying_entity.is_a("IfcWall") # Example check

    def test_get_object_info_no_type(self, object_adapter: IosObjectAdapter):
        """Test retrieving info for an object without a specific IfcObjectType."""
        obj_model = object_adapter.get_by_id(BUILDING_ID_NO_TYPE)  # Use get_by_id
        assert obj_model is not None
        assert obj_model.ifc_id == BUILDING_ID_NO_TYPE
        # Check object_type property
        assert obj_model.object_type is None  # Expect None if no type relation exists

    def test_get_object_info_not_found(self, object_adapter: IosObjectAdapter):
        """Test retrieving info for a non-existent object ID."""
        with pytest.raises(IfcAdapterError):
            # get_by_id raises error if not found
            _ = object_adapter.get_by_id(NON_EXISTENT_ID)

    def test_get_property_success(self, object_adapter: IosObjectAdapter):
        """Test finding a property by name within a known object using get_property."""
        # Use the correct adapter method: get_property
        prop = object_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, KNOWN_NORMAL_PROP_NAME
        )
        assert prop is not None
        assert isinstance(prop, IfcProperty)
        assert prop.name == KNOWN_NORMAL_PROP_NAME
        assert prop.value is not None
        assert isinstance(prop.value, IfcValue)
        assert prop.value.value == KNOWN_NORMAL_PROP_VALUE  # Check raw value
        assert prop.value.value_type == IfcValueType.TEXT  # Based on sample file
        assert prop.value.unit_type == IfcUnitType.UNKNOWN
        assert prop.value.prefix == IfcPrefix.NONE

    def test_get_property_prop_not_found(self, object_adapter: IosObjectAdapter):
        """Test finding a non-existent property by name using get_property."""
        # Use the correct adapter method: get_property
        prop = object_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, "NonExistentProp"
        )
        assert prop is None

    def test_get_property_pset_not_found(self, object_adapter: IosObjectAdapter):
        """Test finding a property when the PSet doesn't exist using get_property."""
        # Use the correct adapter method: get_property
        prop = object_adapter.get_property(
            KNOWN_ELEMENT_ID, "NonExistentPSet", KNOWN_NORMAL_PROP_NAME
        )
        assert prop is None

    def test_get_property_object_not_found(self, object_adapter: IosObjectAdapter):
        """Test finding a property for a non-existent object using get_property."""
        property = object_adapter.get_property(
            NON_EXISTENT_ID, KNOWN_NORMAL_PSET_NAME, KNOWN_NORMAL_PROP_NAME
        )
        assert property is None

    def test_get_pset_by_name_success(self, object_adapter: IosObjectAdapter):
        """Test finding a PSet by name for a known object using model's pset_by_name."""
        # Get the object model first
        obj_model = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert obj_model is not None

        # Use the model's method
        pset = obj_model.pset_by_name(KNOWN_NORMAL_PSET_NAME)

        assert pset is not None
        assert isinstance(pset, IfcPSet)
        assert pset.name == KNOWN_NORMAL_PSET_NAME
        assert pset.ifc_id == KNOWN_NORMAL_PSET_ID

    def test_get_pset_by_name_not_found(self, object_adapter: IosObjectAdapter):
        """Test finding a non-existent PSet by name using model's pset_by_name."""
        # Get the object model first
        obj_model = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert obj_model is not None

        # Use the model's method
        pset = obj_model.pset_by_name("NonExistentPSet")
        assert pset is None

    def test_get_pset_by_name_object_not_found(self, object_adapter: IosObjectAdapter):
        """Test finding a PSet for a non-existent object."""
        with pytest.raises(IfcAdapterError):
            # First step (get_by_id) will raise the error
            _ = object_adapter.get_by_id(NON_EXISTENT_ID)


class TestIosObjectAdapterPsets:
    pass
