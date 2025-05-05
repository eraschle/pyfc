# pyfc/validation/properties.py
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyfc.models.properties import Property, PropertySet, QuantitySet, IPSetDefinition

from pyfc.models.value import IfcUnitType, IfcValueType

logger = logging.getLogger(__name__)

ALLOWED_QUANTITY_UNIT_TYPES: set["IfcUnitType"] = {
    IfcUnitType.AREA,
    IfcUnitType.COUNT,
    IfcUnitType.ENERGY,
    IfcUnitType.LENGTH,
    IfcUnitType.MASS,
    IfcUnitType.PLANEANGLE,
    IfcUnitType.POWER,
    IfcUnitType.TEMPERATURE,
    IfcUnitType.TIME,
    IfcUnitType.VOLUME,
    IfcUnitType.PRESSURE,
}


class ValidationError(Exception):
    pass


def validate_pset_definition(pset_def: "IPSetDefinition") -> None:
    """
    Validates a PropertySet or QuantitySet definition based on common rules.

    Raises
    ------
    ValidationError
        If validation fails.
    """
    logger.debug(f"Validating PSet definition: {pset_def.name}")

    # 1. Validate Name
    if not pset_def.name or not pset_def.name.strip():
        raise ValidationError(f"{type(pset_def).__name__} name cannot be empty or whitespace.")

    # 2. Validate Property Names for Duplicates
    prop_names = [prop.name for prop in pset_def.properties]
    if len(prop_names) != len(set(prop_names)):
        seen = set()
        # Correct way to find duplicates efficiently
        duplicates = {name for name in prop_names if name in seen or seen.add(name) is not None}
        raise ValidationError(
            f"Duplicate property names found in {type(pset_def).__name__} '{pset_def.name}': {duplicates}"
        )

    # 3. Validate Properties based on PSet Type
    from pyfc.models.properties import QuantitySet, PropertySet

    if isinstance(pset_def, QuantitySet):
        _validate_quantity_set_properties(pset_def)
    elif isinstance(pset_def, PropertySet):
        _validate_property_set_properties(pset_def)
    else:
        raise ValidationError(
            f"PSet Definition '{pset_def.name}' is not a QuantitySet or PropertySet."
        )


# --- Helper Validation Functions ---


def _validate_qset_property_unit_type(prop: "Property", qset_name: str) -> None:
    """Checks if the UnitType of a QuantitySet property is allowed."""
    # Quantities should generally have a defined physical unit type
    if prop.unit_type in ALLOWED_QUANTITY_UNIT_TYPES:
        return
    if prop.unit_type == IfcUnitType.UNKNOWN:
        raise ValidationError(
            f"Property '{prop.name}' in QuantitySet '{qset_name}' has no defined UnitType."
        )

    allowed_names = {ut.name for ut in ALLOWED_QUANTITY_UNIT_TYPES}
    raise ValidationError(
        f"Property '{prop.name}' in QuantitySet '{qset_name}' "
        f"has invalid UnitType: {prop.unit_type.name}. "
        f"Expected one of {allowed_names}"
    )


# Define value types generally expected for quantities with units
NUMERIC_VALUE_TYPES: set["IfcValueType"] = {
    IfcValueType.INTEGER,
    IfcValueType.REAL,
}


def _validate_qset_property_value_type(prop: "Property", qset_name: str) -> None:
    """Checks if the ValueType of a QuantitySet property is numeric when a physical unit is present."""
    # If a physical unit (from the allowed list) is specified, the value type should be numeric.
    if prop.unit_type not in ALLOWED_QUANTITY_UNIT_TYPES:
        raise RuntimeError("UnitType validation is not complete.")
    if prop.value_type is None:
        raise ValidationError(
            f"Property '{prop.name}' in QuantitySet '{qset_name}' has no ValueType (NONE)."
        )
    if prop.value_type not in NUMERIC_VALUE_TYPES:
        numeric_names = {vt.name for vt in NUMERIC_VALUE_TYPES}
        raise ValidationError(
            f"Property '{prop.name}' in QuantitySet '{qset_name}' has UnitType '{prop.unit_type.name}' "
            f"but non-numeric ValueType '{prop.value_type.value}'. Expected one of {numeric_names}."
        )


def _validate_quantity_set_properties(qset_def: "QuantitySet") -> None:
    """Validate properties within a QuantitySet using helper functions."""
    for prop in qset_def.properties:
        if not prop.ifc_value:
            logger.warning(
                f"Property '{prop.name}' in QuantitySet '{qset_def.name}' has no IfcValue. Skipping detailed validation."
            )
            raise ValidationError(
                f"Property '{prop.name}' in PropertySet '{qset_def.name}' has UnitType '{prop.unit_type}' "
                f"but non-numeric/non-measure ValueType '{prop.value_type}'. This combination is invalid."
            )
        # Validate Unit Type for the quantity property
        _validate_qset_property_unit_type(prop, qset_def.name)
        # Validate Value Type based on Unit Type for the quantity property
        _validate_qset_property_value_type(prop, qset_def.name)


def _validate_pset_property_unit_value_consistency(prop: "Property", pset_name: str) -> None:
    """Checks for potentially inconsistent UnitType/ValueType combinations in a PropertySet property."""
    # Check only if a specific unit (not UNKNOWN) is given.
    if prop.unit_type != IfcUnitType.UNKNOWN:
        # If a specific unit is given, the value type should ideally be numeric.
        if prop.value_type is None:
            raise ValidationError(
                f"Property '{prop.name}' in PropertySet '{pset_name}' has no ValueType (NONE)."
            )
        if prop.value_type not in NUMERIC_VALUE_TYPES:
            # Allow Count specifically (IfcUnitType.COUNT with INTEGER/REAL)
            # Note: COUNT is also in ALLOWED_QUANTITY_UNIT_TYPES, but this check is for general Psets
            if prop.unit_type == IfcUnitType.COUNT and prop.value_type in (
                IfcValueType.INTEGER,
                IfcValueType.REAL,
            ):
                # This is a valid combination (e.g., number of items)
                return

            # Log a warning for other non-numeric types with specific units in general Psets
            numeric_names = {vt.name for vt in NUMERIC_VALUE_TYPES}
            raise ValidationError(
                f"Property '{prop.name}' in PropertySet '{pset_name}' has UnitType '{prop.unit_type.name}' "
                f"but non-numeric ValueType '{prop.value_type.name}'. This combination might be invalid."
                f"Expected numeric ({numeric_names}) or specific allowed combinations (like COUNT). "
                "This combination might be unusual."
            )


def _validate_property_set_properties(pset_def: "PropertySet") -> None:
    """Validate properties within a PropertySet using helper functions."""
    for prop in pset_def.properties:
        if not prop.ifc_value:
            logger.warning(
                f"Property '{prop.name}' in PropertySet '{pset_def.name}' has no IfcValue. Skipping detailed validation."
            )
            continue

        _validate_pset_property_unit_value_consistency(prop, pset_def.name)
