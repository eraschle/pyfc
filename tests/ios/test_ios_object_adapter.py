import pytest

from pyfc.errors import IfcAdapterError
from pyfc.ios import IosObjectAdapter, IosPSetAdapter
from pyfc.ios.context import IosModelContext
from pyfc.models import (
    IfcObject,
    IfcObjectType,
    IfcProperty,
    IfcPSet,
    Property,
    PropertySet,
)
from pyfc.models.value import (
    IfcPrefix,
    IfcUnitType,
    IfcValue,
    IfcValueType,
    value_factory,
)

from .conftest import (
    BUILDING_ID_NO_TYPE,
    KNOWN_ELEMENT_ID,
    KNOWN_ELEMENT_NAME,
    KNOWN_NORMAL_PROP_NAME,
    KNOWN_NORMAL_PROP_VALUE,
    KNOWN_NORMAL_PSET_ID,
    KNOWN_NORMAL_PSET_NAME,
    KNOWN_PROP_NAME_IN_PSET,
    KNOWN_QTO_ID,
    KNOWN_QTO_NAME,
    NEW_NORMAL_PROP_NAME,
    NEW_NORMAL_PROP_VALUE,
    NEW_NORMAL_PSET_NAME,
    NEW_PROP_NAME,
    NEW_PROP_NAME_2,
    NEW_PROP_VALUE,
    NEW_PROP_VALUE_2,
    NEW_PSET_NAME,
    NON_EXISTENT_ID,
    NON_EXISTENT_PSET_NAME,
    UPDATED_PROP_VALUE,
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

    def test_add_normal_pset_to_object(
        self, object_adapter: IosObjectAdapter, ifc_context: IosModelContext
    ):
        """Test adding a new standard PropertySet to an existing object."""
        # Create a normal PropertySet with a text property
        prop = Property(
            name=NEW_NORMAL_PROP_NAME,
            # Use value_factory to create IfcValue
            ifc_value=value_factory.create(
                NEW_NORMAL_PROP_VALUE, value_type=IfcValueType.TEXT
            ),
        )
        pset_to_add = PropertySet(name=NEW_NORMAL_PSET_NAME, properties=[prop])

        # Add the PSet using the object adapter
        added_pset = object_adapter.add_pset(KNOWN_ELEMENT_ID, pset_to_add)

        # --- Verification ---
        assert added_pset is not None
        assert isinstance(added_pset, IfcPSet)
        assert added_pset.name == NEW_NORMAL_PSET_NAME
        assert added_pset.ifc_id > 0  # Should have a valid ID

        props = added_pset.properties
        assert len(props) == 1
        assert props[0].name == NEW_NORMAL_PROP_NAME
        # Check the raw value within the IfcValue object
        assert props[0].value is not None  # Check IfcValue exists
        assert isinstance(props[0].value, IfcValue)  # Verify it's IfcValue
        assert props[0].value.value == NEW_NORMAL_PROP_VALUE  # Check raw value

        # --- Verification ---
        # Save and reload to ensure persistence
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)
        new_context = IosModelContext.open(file_path)
        new_adapter = IosObjectAdapter(new_context)

        # Verify PSet exists on the object using the model
        reloaded_obj = new_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert reloaded_obj is not None
        new_pset = reloaded_obj.pset_by_name(NEW_NORMAL_PSET_NAME)  # Use model method
        assert new_pset is not None
        # Verify property
        prop_found = new_pset.prop_by_name(NEW_NORMAL_PROP_NAME)
        assert prop_found is not None
        assert prop_found.value is not None  # Check IfcValue exists
        assert isinstance(prop_found.value, IfcValue)
        assert prop_found.value.value == NEW_NORMAL_PROP_VALUE  # Check raw value
        assert prop_found.value.value_type == IfcValueType.TEXT

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
        with pytest.raises(IfcAdapterError):
            # get_property should raise error if object_id doesn't exist
            _ = object_adapter.get_property(
                NON_EXISTENT_ID, KNOWN_NORMAL_PSET_NAME, KNOWN_NORMAL_PROP_NAME
            )

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
        # Check if properties are loaded
        props = pset.properties
        assert len(props) > 0
        prop = pset.prop_by_name(KNOWN_NORMAL_PROP_NAME)
        assert prop is not None
        assert prop.value is not None
        assert isinstance(prop.value, IfcValue)
        assert prop.value.value == KNOWN_NORMAL_PROP_VALUE  # Check raw value

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
    # Test adding, removing, updating PSets

    def test_add_pset_success(
        self, object_adapter: IosObjectAdapter, ifc_context: IosModelContext
    ):
        # Use value_factory
        prop1 = Property(
            name=NEW_PROP_NAME,
            ifc_value=value_factory.create(
                NEW_PROP_VALUE, value_type=IfcValueType.TEXT
            ),
        )
        prop2 = Property(
            name=NEW_PROP_NAME_2,
            ifc_value=value_factory.create(
                NEW_PROP_VALUE_2, value_type=IfcValueType.REAL
            ),
        )
        pset_to_add = PropertySet(name=NEW_PSET_NAME, properties=[prop1, prop2])

        added_pset = object_adapter.add_pset(KNOWN_ELEMENT_ID, pset_to_add)

        assert added_pset is not None
        assert isinstance(added_pset, IfcPSet)
        assert added_pset.name == NEW_PSET_NAME
        assert len(added_pset.properties) == 2

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)
        new_context = IosModelContext.open(file_path)
        new_adapter = IosObjectAdapter(new_context)
        # Verify using model methods
        reloaded_obj = new_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert reloaded_obj is not None
        new_pset_wrapper = reloaded_obj.pset_by_name(NEW_PSET_NAME)
        assert new_pset_wrapper is not None
        assert len(new_pset_wrapper.properties) == 2
        prop1_found = new_pset_wrapper.prop_by_name(NEW_PROP_NAME)
        prop2_found = new_pset_wrapper.prop_by_name(NEW_PROP_NAME_2)
        assert prop1_found is not None
        assert prop1_found.value is not None
        assert isinstance(prop1_found.value, IfcValue)
        assert prop1_found.value.value == NEW_PROP_VALUE  # Check raw value
        assert prop2_found is not None
        assert prop2_found.value is not None
        assert isinstance(prop2_found.value, IfcValue)
        assert prop2_found.value.value == pytest.approx(
            NEW_PROP_VALUE_2
        )  # Check float value

    def test_add_pset_duplicate_name(self, object_adapter: IosObjectAdapter):
        # Attempt to add a PSet with the same name as an existing one
        prop = Property(
            name="AnyProp",
            ifc_value=value_factory.create("AnyValue", value_type=IfcValueType.TEXT),
        )
        pset_to_add = PropertySet(name=KNOWN_NORMAL_PSET_NAME, properties=[prop])

        with pytest.raises(IfcAdapterError):
            _ = object_adapter.add_pset(KNOWN_ELEMENT_ID, pset_to_add)

    def test_update_properties_quantity_success(
        self, object_adapter: IosObjectAdapter, ifc_context: IosModelContext
    ):
        """Test updating a quantity property via the object adapter."""
        # Get the object model first
        obj_model = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert obj_model is not None

        # Get the QTO set using model method
        pset = obj_model.pset_by_name(KNOWN_QTO_NAME)
        assert pset is not None
        assert pset.ifc_id == KNOWN_QTO_ID  # Verify we got the right PSet ID
        prop = pset.prop_by_name(KNOWN_PROP_NAME_IN_PSET)
        assert prop is not None

        original_ifc_value = prop.value  # Get the IfcValue object
        assert original_ifc_value is not None
        assert isinstance(original_ifc_value, IfcValue)
        original_value = original_ifc_value.value  # Extract raw value

        # Create a new value different from the original
        new_width_value = original_value + 10.0
        assert new_width_value != original_value

        # Update the property (Quantity)
        props_to_update = [
            Property(
                name=KNOWN_PROP_NAME_IN_PSET,
                # Use value_factory
                ifc_value=value_factory.create(
                    new_width_value,
                    value_type=IfcValueType.REAL,
                    unit_type=IfcUnitType.LENGTH,
                ),
            )
        ]

        assert object_adapter.update_properties(KNOWN_QTO_ID, props_to_update)
        pset_adapter = IosPSetAdapter(ifc_context)
        updated_pset = pset_adapter.get_by_id(KNOWN_QTO_ID)

        assert updated_pset is not None
        assert updated_pset.ifc_id == KNOWN_QTO_ID
        updated_prop = updated_pset.prop_by_name(KNOWN_PROP_NAME_IN_PSET)
        assert updated_prop is not None
        assert updated_prop.value is not None
        assert isinstance(updated_prop.value, IfcValue)
        assert updated_prop.value.value == pytest.approx(new_width_value)
        assert updated_prop.value.unit_type == IfcUnitType.LENGTH  # Verify unit type

        # Save and reload to verify persistence
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)
        new_context = IosModelContext.open(file_path)
        new_adapter = IosObjectAdapter(new_context)

        # Verify using model methods
        reloaded_obj = new_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert reloaded_obj is not None
        reloaded_pset = reloaded_obj.pset_by_name(KNOWN_QTO_NAME)
        assert reloaded_pset is not None
        reloaded_prop = reloaded_pset.prop_by_name(KNOWN_PROP_NAME_IN_PSET)
        assert reloaded_prop is not None
        assert reloaded_prop.value is not None
        assert isinstance(reloaded_prop.value, IfcValue)
        assert reloaded_prop.value.value == pytest.approx(new_width_value)
        assert reloaded_prop.value.unit_type == IfcUnitType.LENGTH

    def test_update_properties_normal_success(
        self, object_adapter: IosObjectAdapter, ifc_context: IosModelContext
    ):
        """Test updating a normal property via the object adapter."""
        # Get the object model first
        obj_model = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert obj_model is not None

        # Get the PSet using model method
        pset = obj_model.pset_by_name(KNOWN_NORMAL_PSET_NAME)
        assert pset is not None
        assert pset.ifc_id == KNOWN_NORMAL_PSET_ID  # Verify PSet ID
        prop = pset.prop_by_name(KNOWN_NORMAL_PROP_NAME)
        assert prop is not None
        assert prop.value is not None
        assert isinstance(prop.value, IfcValue)
        assert prop.value.value == KNOWN_NORMAL_PROP_VALUE

        # Update the normal property
        ifc_value = value_factory.create(
            UPDATED_PROP_VALUE, value_type=IfcValueType.TEXT
        )
        props_to_update = [Property(name=KNOWN_NORMAL_PROP_NAME, ifc_value=ifc_value)]
        assert object_adapter.update_properties(KNOWN_NORMAL_PSET_ID, props_to_update)

        pset_adapter = IosPSetAdapter(ifc_context)
        updated_pset = pset_adapter.get_by_id(KNOWN_NORMAL_PSET_ID)
        assert updated_pset is not None
        assert updated_pset.ifc_id == KNOWN_NORMAL_PSET_ID
        updated_prop = updated_pset.prop_by_name(KNOWN_NORMAL_PROP_NAME)
        assert updated_prop is not None
        assert updated_prop.value is not None
        assert isinstance(updated_prop.value, IfcValue)
        assert updated_prop.value.value == UPDATED_PROP_VALUE
        assert updated_prop.value.value_type == IfcValueType.TEXT

        # Save and reload to verify persistence
        file_path = ifc_context.file_path
        assert file_path is not None

        ifc_context.save(file_path)
        new_context = IosModelContext.open(file_path)
        new_adapter = IosObjectAdapter(new_context)

        # Verify using model methods
        reloaded_obj = new_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert reloaded_obj is not None
        reloaded_pset = reloaded_obj.pset_by_name(KNOWN_NORMAL_PSET_NAME)
        assert reloaded_pset is not None
        reloaded_prop = reloaded_pset.prop_by_name(KNOWN_NORMAL_PROP_NAME)
        assert reloaded_prop is not None
        assert reloaded_prop.value is not None
        assert isinstance(reloaded_prop.value, IfcValue)
        assert reloaded_prop.value.value == UPDATED_PROP_VALUE

    def test_update_properties_non_existent_prop(
        self, object_adapter: IosObjectAdapter
    ):
        props_to_update = [
            Property(
                name="NonExistentProp",
                ifc_value=value_factory.create(
                    "AnyValue", value_type=IfcValueType.TEXT
                ),
            ),
        ]
        # update_properties requires the property to exist within the PSet
        assert not object_adapter.update_properties(
            KNOWN_NORMAL_PSET_ID, props_to_update
        )

    def test_update_properties_non_existent_pset(
        self, object_adapter: IosObjectAdapter
    ):
        props_to_update = [
            # Use value_factory
            Property(
                name="AnyProp",
                ifc_value=value_factory.create(
                    "AnyValue", value_type=IfcValueType.TEXT
                ),
            ),
        ]
        # update_properties requires the PSet ID to exist
        with pytest.raises(IfcAdapterError):
            _ = object_adapter.update_properties(NON_EXISTENT_ID, props_to_update)

    def test_remove_pset_success(
        self, object_adapter: IosObjectAdapter, ifc_context: IosModelContext
    ):
        """Test removing an existing PSet from an object."""
        # Verify PSet exists initially using model method
        obj_model = object_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert obj_model is not None
        initial_pset = obj_model.pset_by_name(KNOWN_NORMAL_PSET_NAME)
        assert initial_pset is not None
        assert initial_pset.ifc_id == KNOWN_NORMAL_PSET_ID

        # Remove the PSet using the adapter method with element ID and NOT existing name
        success = object_adapter.remove_pset(KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME)
        assert success

        # --- Verification ---
        file_path = ifc_context.file_path
        assert file_path is not None
        ifc_context.save(file_path)
        new_context = IosModelContext.open(file_path)
        new_adapter = IosObjectAdapter(new_context)

        # Verify using model method after reload
        reloaded_obj = new_adapter.get_by_id(KNOWN_ELEMENT_ID)
        assert reloaded_obj is not None
        reloaded_pset = reloaded_obj.pset_by_name(KNOWN_NORMAL_PSET_NAME)
        assert reloaded_pset is None, "PSet should be removed after save/reload"

        # Verify the PSet entity itself is removed from the file
        pset_entity = new_context.ifc_by_id(KNOWN_NORMAL_PSET_ID)
        assert pset_entity is None, "PSet entity should be deleted from the file"

    def test_remove_pset_not_found_on_object(self, object_adapter: IosObjectAdapter):
        """Test removing a PSet that exists but is not attached to the object."""
        # Assuming BUILDING_ID_NO_TYPE doesn't have KNOWN_QTO_ID attached
        # Not raise an error but return False
        success = object_adapter.remove_pset(BUILDING_ID_NO_TYPE, KNOWN_QTO_NAME)
        assert not success

    def test_remove_pset_non_existent_pset_name(self, object_adapter: IosObjectAdapter):
        """Test removing a PSet using a non-existent PSet Name."""
        success = object_adapter.remove_pset(KNOWN_ELEMENT_ID, NON_EXISTENT_PSET_NAME)
        assert not success

    def test_remove_pset_non_existent_object_id(self, object_adapter: IosObjectAdapter):
        """Test removing a PSet from a non-existent object ID."""
        with pytest.raises(IfcAdapterError) as excinfo:
            object_adapter.remove_pset(NON_EXISTENT_ID, NON_EXISTENT_PSET_NAME)
            assert excinfo.match("ID") and excinfo.match("not found")
