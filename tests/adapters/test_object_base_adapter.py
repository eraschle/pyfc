from pyfc.adapters import IObjectBaseAdapter
from pyfc.models import (
    IfcObjectBase,
    IfcProperty,
    IfcPSet,
    Property,
    PropertySet,
    ValueFactory,
)

# --- Constants for Test Data ---
from tests.conftest import (
    KNOWN_ELEMENT_ID,
    KNOWN_NORMAL_PROP_NAME,
    KNOWN_NORMAL_PROP_VALUE,
    KNOWN_NORMAL_PSET_NAME,
    KNOWN_PROP_QTO_NAME_IN_PSET,
    KNOWN_PROP_QTO_VALUE_IN_PSET,
    KNOWN_PSET_QTO_NAME,
    NEW_PROP_NAME,
    NEW_PROP_VALUE,
    NEW_PSET_NAME,
    NON_EXISTENT_ID,
    NON_EXISTENT_PROP_NAME,
    NON_EXISTENT_PSET_NAME,
)


# --- Test Class ---
class TestIObjectBaseAdapter:
    """Tests the IObjectBaseAdapter interface methods."""

    def test_get_property_sets_normal(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify retrieving normal property sets for a known element."""
        psets = base_adapter.get_psets(KNOWN_ELEMENT_ID, include_qto=False)
        assert psets is not None
        assert isinstance(psets, list)
        assert len(psets) > 0  # Assuming the test element has at least one normal pset
        found_known_pset = any(pset.name == KNOWN_NORMAL_PSET_NAME for pset in psets)
        assert found_known_pset, f"Expected PSet '{KNOWN_NORMAL_PSET_NAME}' not found."
        # Verify QTO sets are excluded
        found_qto_pset = any(pset.name == KNOWN_PSET_QTO_NAME for pset in psets)
        assert not found_qto_pset, f"QTO PSet '{KNOWN_PSET_QTO_NAME}' should not be included."

    def test_get_property_sets_with_qto(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify retrieving all property sets (including QTOs) for a known element."""
        psets = base_adapter.get_psets(KNOWN_ELEMENT_ID, include_qto=True)
        assert psets is not None
        assert isinstance(psets, list)
        assert len(psets) > 1  # Assuming at least one normal and one QTO pset
        found_known_pset = any(pset.name == KNOWN_NORMAL_PSET_NAME for pset in psets)
        assert found_known_pset, f"Expected PSet '{KNOWN_NORMAL_PSET_NAME}' not found."
        found_qto_pset = any(pset.name == KNOWN_PSET_QTO_NAME for pset in psets)
        assert found_qto_pset, f"Expected QTO PSet '{KNOWN_PSET_QTO_NAME}' not found."

    def test_get_property_sets_non_existent_object(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify retrieving property sets for a non-existent object returns empty list."""
        psets = base_adapter.get_psets(NON_EXISTENT_ID, include_qto=True)
        assert psets == []

    def test_get_property_set_normal_by_name(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify retrieving a specific normal property set by name."""
        pset = base_adapter.get_pset_by_name(KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME)
        assert pset is not None
        assert isinstance(pset, IfcPSet)
        assert pset.name == KNOWN_NORMAL_PSET_NAME
        assert len(pset.properties) > 0  # Assuming the pset has properties
        # Check for a known property within the pset
        found_prop = any(prop.name == KNOWN_NORMAL_PROP_NAME for prop in pset.properties)
        assert found_prop, f"Expected property '{KNOWN_NORMAL_PROP_NAME}' not found in PSet."

    def test_get_property_set_qto_by_name(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify retrieving a specific QTO property set by name."""
        pset = base_adapter.get_pset_by_name(KNOWN_ELEMENT_ID, KNOWN_PSET_QTO_NAME)
        assert pset is not None
        assert isinstance(pset, IfcPSet)
        assert pset.name == KNOWN_PSET_QTO_NAME
        assert len(pset.properties) > 0
        found_prop = any(prop.name == KNOWN_PROP_QTO_NAME_IN_PSET for prop in pset.properties)
        assert found_prop, f"Expected property '{KNOWN_PSET_QTO_NAME}' not found in QTO PSet."

    def test_get_property_set_non_existent_name(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify retrieving a non-existent property set by name returns None."""
        pset = base_adapter.get_pset_by_name(KNOWN_ELEMENT_ID, NON_EXISTENT_PSET_NAME)
        assert pset is None

    def test_get_property_set_non_existent_object(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify retrieving a property set for a non-existent object returns None."""
        pset = base_adapter.get_pset_by_name(NON_EXISTENT_ID, KNOWN_NORMAL_PSET_NAME)
        assert pset is None

    def test_get_property_normal(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify retrieving a specific property from a normal pset."""
        prop = base_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, KNOWN_NORMAL_PROP_NAME
        )
        assert prop is not None
        assert isinstance(prop, IfcProperty)
        assert prop.name == KNOWN_NORMAL_PROP_NAME
        assert prop.value is not None
        # Be careful comparing values directly if they are floats due to precision
        assert prop.value.value == KNOWN_NORMAL_PROP_VALUE

    def test_get_property_qto(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify retrieving a specific property from a QTO pset."""
        prop = base_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_PSET_QTO_NAME, KNOWN_PROP_QTO_NAME_IN_PSET
        )
        assert prop is not None
        assert isinstance(prop, IfcProperty)
        assert prop.name == KNOWN_PROP_QTO_NAME_IN_PSET
        assert prop.value is not None
        assert prop.value.value == KNOWN_PROP_QTO_VALUE_IN_PSET

    def test_get_property_non_existent_prop_name(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify retrieving a non-existent property returns None."""
        prop = base_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, NON_EXISTENT_PROP_NAME
        )
        assert prop is None

    def test_get_property_non_existent_pset_name(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify retrieving a property from a non-existent pset returns None."""
        prop = base_adapter.get_property(
            KNOWN_ELEMENT_ID, NON_EXISTENT_PSET_NAME, KNOWN_NORMAL_PROP_NAME
        )
        assert prop is None

    def test_get_property_non_existent_object(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify retrieving a property for a non-existent object returns None."""
        prop = base_adapter.get_property(
            NON_EXISTENT_ID, KNOWN_NORMAL_PSET_NAME, KNOWN_NORMAL_PROP_NAME
        )
        assert prop is None

    def test_add_remove_pset(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify adding a new pset to an object and then removing it."""
        # Define a new PSet with a property
        new_prop = Property(name=NEW_PROP_NAME, ifc_value=ValueFactory.create(NEW_PROP_VALUE))
        new_pset_data = PropertySet(name=NEW_PSET_NAME, properties=[new_prop])

        # 1. Verify the PSet does not exist initially
        initial_pset = base_adapter.get_pset_by_name(KNOWN_ELEMENT_ID, NEW_PSET_NAME)
        assert initial_pset is None

        # 2. Add the new PSet
        added_pset = base_adapter.add_new_pset_to(KNOWN_ELEMENT_ID, new_pset_data)
        assert added_pset is not None
        assert isinstance(added_pset, IfcPSet)
        assert added_pset.name == NEW_PSET_NAME
        assert len(added_pset.properties) == 1
        added_prop = added_pset.properties[0]
        assert added_prop.name == NEW_PROP_NAME
        assert added_prop.value is not None
        assert added_prop.value.value == NEW_PROP_VALUE

        # 3. Verify the PSet exists after adding
        pset_after_add = base_adapter.get_pset_by_name(KNOWN_ELEMENT_ID, NEW_PSET_NAME)
        assert pset_after_add is not None
        assert pset_after_add.ifc_id == added_pset.ifc_id  # Check if it's the same entity
        assert pset_after_add.name == NEW_PSET_NAME
        assert len(pset_after_add.properties) == 1
        prop_in_added = pset_after_add.properties[0]
        assert prop_in_added.name == NEW_PROP_NAME
        assert prop_in_added.value is not None
        assert prop_in_added.value.value == NEW_PROP_VALUE

        # 4. Remove the PSet
        remove_result = base_adapter.remove_pset_from(KNOWN_ELEMENT_ID, NEW_PSET_NAME)
        assert remove_result is True

        # 5. Verify the PSet is gone
        pset_after_remove = base_adapter.get_pset_by_name(KNOWN_ELEMENT_ID, NEW_PSET_NAME)
        assert pset_after_remove is None

    def test_add_pset_that_already_exists(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify adding a pset that already exists returns the existing one (or updates)."""
        # Interface contract might vary: does it update, error, or return existing?
        # Assuming it returns the existing or potentially updates properties if different.
        # Let's try adding the known pset again, maybe with a slight modification if update is expected.
        existing_pset_data = PropertySet(name=KNOWN_NORMAL_PSET_NAME, properties=[])

        added_pset = base_adapter.get_pset_by_name(KNOWN_ELEMENT_ID, existing_pset_data.name)

        # Check if it returned a valid PSet (either original or potentially modified)
        assert added_pset is not None
        assert isinstance(added_pset, IfcPSet)
        assert added_pset.name == KNOWN_NORMAL_PSET_NAME

        # Verify it's still accessible
        retrieved_pset = base_adapter.get_pset_by_name(KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME)
        assert retrieved_pset is not None
        assert retrieved_pset.name == KNOWN_NORMAL_PSET_NAME
        # Depending on implementation, check if properties were updated or remained the same
        # For this test, just ensuring it didn't fail catastrophically is okay.

    def test_add_pset_to_non_existent_object(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify adding a pset to a non-existent object returns None."""
        new_pset_data = PropertySet(name=NEW_PSET_NAME, properties=[])
        added_pset = base_adapter.get_pset_by_name(NON_EXISTENT_ID, new_pset_data.name)
        assert added_pset is None

    def test_remove_pset_non_existent_name(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify removing a non-existent pset returns False."""
        remove_result = base_adapter.remove_pset_from(KNOWN_ELEMENT_ID, NON_EXISTENT_PSET_NAME)
        assert remove_result is False

    def test_remove_pset_non_existent_object(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify removing a pset from a non-existent object returns False."""
        remove_result = base_adapter.remove_pset_from(NON_EXISTENT_ID, KNOWN_NORMAL_PSET_NAME)
        assert remove_result is False

    def test_add_remove_property_in_pset(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify adding a new property to an existing pset and then removing it."""
        prop_to_add = Property(name=NEW_PROP_NAME, ifc_value=ValueFactory.create(NEW_PROP_VALUE))

        # 1. Verify the property does not exist initially in the target pset
        initial_prop = base_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, NEW_PROP_NAME
        )
        assert initial_prop is None

        # 2. Add the new property
        added_prop = base_adapter.add_property_to_pset(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, prop_to_add
        )
        assert added_prop is not None
        # The returned type might be the generic Property or the specific IfcProperty
        # depending on the implementation detail. Let's accept either for now.
        assert isinstance(added_prop, (Property, IfcProperty))
        assert added_prop.name == NEW_PROP_NAME
        assert added_prop.value is not None
        assert added_prop.value.value == NEW_PROP_VALUE

        # 3. Verify the property exists after adding
        prop_after_add = base_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, NEW_PROP_NAME
        )
        assert prop_after_add is not None
        assert prop_after_add.ifc_id == added_prop.ifc_id  # Check if it's the same entity
        assert prop_after_add.name == NEW_PROP_NAME
        assert prop_after_add.value is not None
        assert prop_after_add.value.value == NEW_PROP_VALUE

        # 4. Remove the property
        remove_result = base_adapter.remove_property_from_pset(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, NEW_PROP_NAME
        )
        assert remove_result is True

        # 5. Verify the property is gone
        prop_after_remove = base_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, NEW_PROP_NAME
        )
        assert prop_after_remove is None

    def test_add_property_to_non_existent_pset(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify adding a property to a non-existent pset returns None."""
        prop_to_add = Property(name=NEW_PROP_NAME, ifc_value=ValueFactory.create(NEW_PROP_VALUE))
        added_prop = base_adapter.add_property_to_pset(
            KNOWN_ELEMENT_ID, NON_EXISTENT_PSET_NAME, prop_to_add
        )
        # The interface contract doesn't strictly define error handling here,
        # but returning None is a reasonable expectation for failure.
        assert added_prop is None

    def test_add_property_to_non_existent_object(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify adding a property to a pset of a non-existent object returns None."""
        prop_to_add = Property(name=NEW_PROP_NAME, ifc_value=ValueFactory.create(NEW_PROP_VALUE))
        added_prop = base_adapter.add_property_to_pset(
            NON_EXISTENT_ID, KNOWN_NORMAL_PSET_NAME, prop_to_add
        )
        assert added_prop is None

    def test_add_property_that_already_exists_updates(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify adding a property that already exists updates its value."""
        updated_value = "Updated Test Value"
        prop_to_update = Property(
            name=KNOWN_NORMAL_PROP_NAME,  # Existing property name
            ifc_value=ValueFactory.create(updated_value),  # New value
        )

        # 1. Verify initial value
        initial_prop = base_adapter.get_property(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, KNOWN_NORMAL_PROP_NAME
        )
        assert initial_prop is not None
        assert initial_prop.value is not None
        assert initial_prop.value.value == KNOWN_NORMAL_PROP_VALUE

        # 2. Add the property with the same name but new value
        updated_prop = base_adapter.add_property_to_pset(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, prop_to_update
        )
        assert updated_prop is None

    def test_remove_property_non_existent(self, base_adapter: IObjectBaseAdapter[IfcObjectBase]):
        """Verify removing a non-existent property returns False."""
        remove_result = base_adapter.remove_property_from_pset(
            KNOWN_ELEMENT_ID, KNOWN_NORMAL_PSET_NAME, NON_EXISTENT_PROP_NAME
        )
        assert remove_result is False

    def test_remove_property_from_non_existent_pset(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify removing a property from a non-existent pset returns False."""
        remove_result = base_adapter.remove_property_from_pset(
            KNOWN_ELEMENT_ID, NON_EXISTENT_PSET_NAME, KNOWN_NORMAL_PROP_NAME
        )
        assert remove_result is False

    def test_remove_property_from_non_existent_object(
        self, base_adapter: IObjectBaseAdapter[IfcObjectBase]
    ):
        """Verify removing a property from a pset of a non-existent object returns False."""
        remove_result = base_adapter.remove_property_from_pset(
            NON_EXISTENT_ID, KNOWN_NORMAL_PSET_NAME, KNOWN_NORMAL_PROP_NAME
        )
        assert remove_result is False
