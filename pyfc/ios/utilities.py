# pyfc/ios/utilities.py
import logging
from typing import Any, Iterable, List, Tuple, TypeVar  # Added List, Tuple, TypeVar

import ifcopenshell as ios

# Import IfcEntityType
from pyfc.models.ifc_types import IfcEntityType

logger = logging.getLogger(__name__)

IfcEntity = ios.entity_instance  # Alias for entity instance
T = TypeVar("T")  # Add TypeVar definition


def is_entity_type(entity: Any | None, expected_type: IfcEntityType) -> bool:
    """
    Checks safely if the entity is not None and is of the expected IFC type.

    Parameters
    ----------
    entity : Any | None
        The entity instance to check.
    expected_type : IfcEntityType
        The expected IFC type enum member.

    Returns
    -------
    bool
        True if the entity is not None and matches the expected type, False otherwise.
    """
    if entity is None:
        return False
    return entity.is_a(expected_type.value)


def has_attribute(entity: Any | None, attribute_name: str) -> bool:
    """
    Checks safely if the entity is not None and has the specified attribute.

    Parameters
    ----------
    entity : Any | None
        The entity instance to check.
    attribute_name : str
        The name of the attribute to check for.

    Returns
    -------
    bool
        True if the entity is not None and has the attribute, False otherwise.
    """
    if entity is None:
        return False
    return hasattr(entity, attribute_name)


def has_attribute_value(entity: Any | None, attribute_name: str) -> bool:
    """
    Checks safely if the entity is not None, has the specified attribute,
    and the attribute's value evaluates to True (is not None, empty, 0, False).

    Parameters
    ----------
    entity : Any | None
        The entity instance to check.
    attribute_name : str
        The name of the attribute to check.

    Returns
    -------
    bool
        True if the entity is not None, has the attribute, and its value is truthy, False otherwise.
    """
    return has_attribute(entity, attribute_name) and bool(getattr(entity, attribute_name))


def is_attribute_value(entity: Any | None, attribute_name: str, value: Any) -> bool:
    """
    Checks if the entity is not None, has the specified attribute,
    and the attribute's value matches the expected value.

    Parameters
    ----------
    entity : Any | None
        The entity instance to check.
    attribute_name : str
        The name of the attribute to check.
    value : Any
        The expected value to compare against.

    Returns
    -------
    bool
        True if the entity is not None, has the attribute, and its value matches the expected value, False otherwise.
    """
    if not has_attribute(entity, attribute_name):
        return False
    return getattr(entity, attribute_name) == value


def is_property_set(entity: Any | None) -> bool:
    """Checks if the entity is an IfcPropertySet."""
    return is_entity_type(entity, IfcEntityType.PROPERTY_SET)


def is_element_quantity(entity: Any | None) -> bool:
    """Checks if the entity is an IfcElementQuantity."""
    return is_entity_type(entity, IfcEntityType.ELEMENT_QUANTITY)


def is_pset_or_qto(entity: Any | None) -> bool:
    """Checks if the entity is either an IfcPropertySet or an IfcElementQuantity."""
    # Slightly more efficient than calling the other functions if entity is None
    if entity is None:
        return False
    return entity.is_a(IfcEntityType.PROPERTY_SET) or entity.is_a(IfcEntityType.ELEMENT_QUANTITY)


def is_single_value_property(entity: Any | None) -> bool:
    """Checks if the entity is an IfcPropertySingleValue."""
    return is_entity_type(entity, IfcEntityType.PROPERTY_SINGLE_VALUE)


def is_property_or_quantity(entity: Any | None) -> bool:
    """Checks if the entity is an IfcProperty or IfcPhysicalQuantity."""
    if entity is None:
        return False
    return entity.is_a(IfcEntityType.PROPERTY) or entity.is_a(IfcEntityType.PHYSICAL_QUANTITY)


def is_rel_defines_by_properties(entity: Any | None) -> bool:
    """Checks if the entity is an IfcRelDefinesByProperties."""
    return is_entity_type(entity, IfcEntityType.REL_DEFINES_BY_PROPERTIES)


def is_rel_defines_by_type(entity: Any | None) -> bool:
    """Checks if the entity is an IfcRelDefinesByType."""
    return is_entity_type(entity, IfcEntityType.REL_DEFINES_BY_TYPE)


def is_object(entity: Any | None) -> bool:
    """Checks if the entity is an IfcObject."""
    return is_entity_type(entity, IfcEntityType.OBJECT)


def is_type_object(entity: Any | None) -> bool:
    """Checks if the entity is an IfcTypeObject."""
    return is_entity_type(entity, IfcEntityType.TYPE_OBJECT)


def is_si_unit(entity: Any | None) -> bool:
    """Checks if the entity is an IfcSIUnit."""
    return is_entity_type(entity, IfcEntityType.SI_UNIT)


def is_list_or_tuple(value: Any) -> bool:
    """Checks if the value is a list or a tuple."""
    return isinstance(value, (list, tuple))


def ensure_list(value: Any | Iterable[T] | None) -> List[T]:
    """
    Ensures the returned value is a mutable list.

    - If the input is None, returns an empty list ([]).
    - If the input is already a list, returns a *copy* of it.
    - If the input is a tuple or other iterable (excluding str/bytes), converts it to a list.
    - If the input is a single item (not None, not iterable), wraps it in a list.

    Parameters
    ----------
    value : Any | Iterable[T] | None
        The value to process.

    Returns
    -------
    List[T]
        A mutable list (a copy if the input was a list).
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    # Check for common iterables, excluding strings/bytes which are usually treated as single items here
    if isinstance(value, Iterable):
        return list(value)
    # Assume it's a single item if not None and not a recognized iterable
    return [value]


def ensure_tuple(value: Any | Iterable[T] | None) -> Tuple[T, ...]:
    """
    Ensures the returned value is a tuple.

    - If the input is None, returns an empty tuple (()).
    - If the input is already a tuple, returns a *copy* of it (ensures it's a base tuple).
    - If the input is a list or other iterable (excluding str/bytes), converts it to a tuple.
    - If the input is a single item (not None, not iterable), wraps it in a single-element tuple.

    Parameters
    ----------
    value : Any | Iterable[T] | None
        The value to process.

    Returns
    -------
    Tuple[T, ...]
        A tuple.
    """
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    # Check for common iterables, excluding strings/bytes
    if isinstance(value, Iterable):
        return tuple(value)
    # Assume it's a single item if not None and not a recognized iterable
    return (value,)


def ensure_iterable(value: Any) -> Iterable[Any]:
    """
    Ensures the returned value is an iterable (list or tuple).
    If the input is None, returns an empty list.
    If the input is not a list or tuple, wraps it in a list.
    Otherwise, returns the input as is.

    Parameters
    ----------
    value : Any
        The value to process.

    Returns
    -------
    Iterable[Any]
        An iterable (list or tuple).
    """
    if value is None:
        return []
    if not is_list_or_tuple(value):
        return [value]
    return value
