# Path: ifcproj/models/value.py
import logging
from dataclasses import dataclass, field

# Use standard Enum for IfcUnitType to allow tuple values
from enum import Enum, StrEnum
from typing import Any

from pyfc.utils import convert

logger = logging.getLogger(__name__)


class IfcPrefix(StrEnum):
    """Enum for SI prefixes used in IfcSIUnit. Values match IFC standard."""

    NONE = ""  # Use empty string for direct use, handle None via _missing_
    EXA = "EXA"
    PETA = "PETA"
    TERA = "TERA"
    GIGA = "GIGA"
    MEGA = "MEGA"
    KILO = "KILO"
    HECTO = "HECTO"
    DECA = "DECA"
    DECI = "DECI"
    CENTI = "CENTI"
    MILLI = "MILLI"
    MICRO = "MICRO"
    NANO = "NANO"
    PICO = "PICO"
    FEMTO = "FEMTO"
    ATTO = "ATTO"

    @classmethod
    def _missing_(cls, value):
        """Handle None or empty string as NONE."""
        if value is None or value == "":
            return cls.NONE
        try:
            # Attempt to find by value first (case-insensitive for robustness if needed)
            # For StrEnum, direct value lookup should work
            return super()._missing_(value)
        except ValueError:
            # Optional: Attempt case-insensitive lookup if direct match fails
            upper_value = str(value).upper()
            for member in cls:
                if member.value == upper_value:
                    return member
            # If still not found, return NONE or raise error depending on desired strictness
            logger.warning(f"Could not map value '{value}' to IfcPrefix, defaulting to NONE.")
            return cls.NONE


class IfcValueType(StrEnum):
    """Enum for IFC value types (semantic). Values match IFC standard type names."""

    REAL = "IfcReal"
    INTEGER = "IfcInteger"
    BOOLEAN = "IfcBoolean"
    TEXT = "IfcText"
    LABEL = "IfcLabel"
    LOGICAL = "IfcLogical"  # Added for boolean measures
    IDENTIFIER = "IfcIdentifier"  # Added for completeness
    # --- Keep commented types for potential future use ---
    # DATE_TIME = "IfcDateTime"
    # DATE = "IfcDate"
    # TIME = "IfcTime"
    # DURATION = "IfcDuration"
    # TIMESTAMP = "IfcTimeStamp"
    # POSITIVE_INTEGER = "IfcPositiveInteger"
    # BINARY = "IfcBinary"

    @classmethod
    def from_python_type(cls, value: Any) -> "IfcValueType":
        """Infers the IfcValueType from a Python value."""
        if isinstance(value, bool):
            # Map Python bool to IfcLogical according to IFC standard for IfcBooleanMeasure etc.
            # IfcBoolean type itself might be used differently, but Logical is common for measures.
            return cls.LOGICAL
        if convert.is_int(value):
            return cls.INTEGER
        if convert.is_float(value):
            return cls.REAL
        # Default to TEXT for strings or other types
        return cls.TEXT

    @classmethod
    def _missing_(cls, value):
        """Handle mapping from various IFC type names (e.g., measures) to semantic types."""
        if isinstance(value, str):
            upper_value = value.upper()
            # Direct match (already handled by StrEnum default)
            # if upper_value in cls._value2member_map_: return cls(upper_value)

            # Map Measures to base types
            if "MEASURE" in upper_value:
                if "COUNT" in upper_value:
                    return cls.INTEGER
                if "LOGICAL" in upper_value or "BOOLEAN" in upper_value:
                    return cls.LOGICAL
                # Most other measures map to REAL
                return cls.REAL
            # Map specific types not directly in enum (if needed)
            if upper_value == "IFCBOOLEAN":
                return cls.BOOLEAN  # Explicit IfcBoolean entity

            # Fallback or error
            logger.warning(
                f"Could not map IFC type name '{value}' to IfcValueType, defaulting to TEXT."
            )
            return cls.TEXT
        return super()._missing_(value)


class IfcUnitType(Enum):
    """
    Enum for IFC unit types (semantic).
    Values are tuples: (IFC UnitEnum String | None, Default IFC SI Name | None, Is SI Unit?)
    """

    UNKNOWN = (None, None, False)
    COUNT = (None, None, False)  # Typically unitless but treated as a type
    LENGTH = ("LENGTHUNIT", "METRE", True)
    AREA = ("AREAUNIT", "SQUARE_METRE", True)
    VOLUME = ("VOLUMEUNIT", "CUBIC_METRE", True)
    MASS = ("MASSUNIT", "GRAM", True)  # Base is GRAM, KILOGRAM name handled separately
    TIME = ("TIMEUNIT", "SECOND", True)
    TEMPERATURE = (
        "THERMODYNAMICTEMPERATUREUNIT",
        "KELVIN",
        True,
    )  # Note: No space in IFC enum
    PRESSURE = ("PRESSUREUNIT", "PASCAL", True)
    ENERGY = ("ENERGYUNIT", "JOULE", True)
    POWER = ("POWERUNIT", "WATT", True)
    # Add more SI units as needed
    PLANEANGLE = ("PLANEANGLEUNIT", "RADIAN", True)
    # Add common derived units if needed for mapping back
    # VELOCITY = ("LINEARVELOCITYUNIT", "METRE PER SECOND", False) # Example

    @property
    def ifc_unit_enum(self) -> str | None:
        """The corresponding IFC UnitEnum string (e.g., 'LENGTHUNIT')."""
        return self.value[0]

    @property
    def default_si_name(self) -> str | None:
        """The default name for the corresponding IfcSIUnit (e.g., 'METRE')."""
        return self.value[1]

    @property
    def is_si(self) -> bool:
        """Indicates if this unit type corresponds to a base IfcSIUnit."""
        return self.value[2]

    @classmethod
    def from_ifc_unit_enum(cls, ifc_enum_str: str | None) -> "IfcUnitType":
        """Finds the IfcUnitType member corresponding to an IFC UnitEnum string."""
        if not ifc_enum_str:
            return cls.UNKNOWN
        upper_enum_str = ifc_enum_str.upper()
        for member in cls:
            if member.ifc_unit_enum == upper_enum_str:
                return member
        logger.warning(f"Could not map IFC UnitEnum '{ifc_enum_str}' to IfcUnitType.")
        return cls.UNKNOWN

    @classmethod
    def from_measure_type(cls, measure_type: str | None) -> "IfcUnitType":
        """Finds the IfcUnitType member corresponding to an IFC Measure type string."""
        if not measure_type:
            return cls.UNKNOWN
        upper_measure = measure_type.upper()
        # Simple mapping based on common measure names
        if "LENGTH" in upper_measure:
            return cls.LENGTH
        if "AREA" in upper_measure:
            return cls.AREA
        if "VOLUME" in upper_measure:
            return cls.VOLUME
        if "MASS" in upper_measure:
            return cls.MASS
        if "TIME" in upper_measure:
            return cls.TIME
        if "THERMODYNAMICTEMPERATURE" in upper_measure:
            return cls.TEMPERATURE
        if "PRESSURE" in upper_measure:
            return cls.PRESSURE
        if "ENERGY" in upper_measure:
            return cls.ENERGY
        if "POWER" in upper_measure:
            return cls.POWER
        if "COUNT" in upper_measure:
            return cls.COUNT
        if "PLANEANGLE" in upper_measure:
            return cls.PLANEANGLE
        # Add more mappings if needed
        logger.warning(f"Could not map IFC Measure type '{measure_type}' to IfcUnitType.")
        return cls.UNKNOWN


@dataclass(frozen=True)
class IfcValue:
    """
    Represents a value with its associated semantic type, unit, and prefix.
    Designed to be independent of the underlying IFC library implementation.
    """

    value: Any = field(compare=True)
    value_type: IfcValueType = field(compare=True)
    unit_type: IfcUnitType = field(default=IfcUnitType.UNKNOWN, compare=True)
    prefix: IfcPrefix = field(default=IfcPrefix.NONE, compare=True)
    # unit_symbol: str | None = None # Optional: For display purposes, could be added later

    def __post_init__(self):
        # --- Basic validation ---
        # Reset prefix if unit is UNKNOWN or COUNT
        if self.prefix != IfcPrefix.NONE and self.unit_type in (
            IfcUnitType.UNKNOWN,
            IfcUnitType.COUNT,
        ):
            object.__setattr__(self, "prefix", IfcPrefix.NONE)
            logger.warning(
                f"Prefix '{self.prefix.value}' ignored for unit type '{self.unit_type.name}'. Set to NONE."
            )

        # --- Check for value type mismatches for specific unit types ---
        mismatch = False
        expected_type_str = ""

        # Check physical units expecting REAL
        if self.unit_type in (
            IfcUnitType.LENGTH,
            IfcUnitType.AREA,
            IfcUnitType.VOLUME,
            IfcUnitType.MASS,
            IfcUnitType.TIME,
            IfcUnitType.TEMPERATURE,
            IfcUnitType.PRESSURE,
            IfcUnitType.ENERGY,
            IfcUnitType.POWER,
            IfcUnitType.PLANEANGLE,
        ):
            if self.value_type != IfcValueType.REAL:
                mismatch = True
                expected_type_str = IfcValueType.REAL.value

        # Check COUNT expecting INTEGER or REAL
        elif self.unit_type == IfcUnitType.COUNT:
            if self.value_type not in (IfcValueType.INTEGER, IfcValueType.REAL):
                mismatch = True
                # More precise expectation in the warning message
                expected_type_str = f"{IfcValueType.INTEGER.value} or {IfcValueType.REAL.value}"

        # Log warning only if a mismatch was detected for a relevant unit type
        if mismatch:
            logger.warning(
                f"Value type mismatch: Unit type '{self.unit_type.name}' typically expects {expected_type_str}, but got {self.value_type.value} for value '{self.value}'."
            )

    def __str__(self) -> str:
        unit_str = ""
        if self.unit_type != IfcUnitType.UNKNOWN:
            prefix_str = self.prefix.value if self.prefix != IfcPrefix.NONE else ""
            # Use the semantic name (e.g., LENGTH) for clarity in string representation
            unit_name = self.unit_type.name
            unit_str = f" ({prefix_str}{unit_name})"

        # Represent value type using its semantic name
        value_type_name = self.value_type.name  # Use name (e.g., REAL) instead of value ("IfcReal")
        return f"{self.value} [{value_type_name}{unit_str}]"


# --- Factory ---


class ValueFactory:
    """Factory class for creating IfcValue instances."""

    @staticmethod
    def create(
        value: Any,
        value_type: IfcValueType | str | None = None,
        unit_type: IfcUnitType | str | None = None,
        prefix: IfcPrefix | str | None = None,
    ) -> IfcValue:
        """
        Creates an IfcValue instance, inferring missing types if possible.
        Accepts Enum members or their string representations for type inputs.

        Parameters
        ----------
        value : Any
            The raw Python value.
        value_type : IfcValueType | str | None, optional
            The semantic type of the value. Inferred if None. Can be Enum member or IFC type string (e.g., "IfcReal").
        unit_type : IfcUnitType | str | None, optional
            The semantic unit type. Defaults to UNKNOWN if None. Can be Enum member or IFC UnitEnum string (e.g., "LENGTHUNIT") or semantic name ("LENGTH").
        prefix : IfcPrefix | str | None, optional
            The SI prefix. Defaults to NONE if None. Can be Enum member or IFC Prefix string (e.g., "KILO").

        Returns
        -------
        IfcValue
            An immutable IfcValue instance.

        Raises
        ------
        ValueError
            If value is None or required conversions fail.
        """
        if value is None:
            raise ValueError("Cannot create IfcValue for None.")

        # --- Resolve Enums from strings if necessary ---
        resolved_value_type: IfcValueType | None = None
        resolved_unit_type: IfcUnitType | None = None
        resolved_prefix: IfcPrefix | None = None
        try:
            # Resolve Value Type (accepts enum, IFC type string, or None)
            if isinstance(value_type, IfcValueType):
                resolved_value_type = value_type
            elif isinstance(value_type, str):
                # Uses _missing_ for mapping
                resolved_value_type = IfcValueType(value_type)
            # elif value_type is not None:
            #     raise ValueError(f"Invalid value_type input: {value_type}")

            # Resolve Unit Type (accepts enum, semantic name string, IFC UnitEnum string, or None)
            if isinstance(unit_type, IfcUnitType):
                resolved_unit_type = unit_type
            elif isinstance(unit_type, str):
                try:
                    # Try mapping by semantic name first (case-insensitive)
                    resolved_unit_type = IfcUnitType[unit_type.upper()]
                except KeyError:
                    # If not found by name, try mapping by IFC UnitEnum value
                    resolved_unit_type = IfcUnitType.from_ifc_unit_enum(unit_type)
            # elif unit_type is not None:
            #     raise ValueError(f"Invalid unit_type input: {unit_type}")
            resolved_unit_type = resolved_unit_type or IfcUnitType.UNKNOWN  # Default to UNKNOWN

            # Resolve Prefix (accepts enum, IFC prefix string, None, or "")
            if isinstance(prefix, IfcPrefix):
                resolved_prefix = prefix
            elif prefix is not None:  # Handles string or ""
                resolved_prefix = IfcPrefix(prefix)  # Uses _missing_ for None/""/string
            else:  # prefix is None
                resolved_prefix = IfcPrefix.NONE
            resolved_prefix = resolved_prefix or IfcPrefix.NONE  # Ensure not None

        except (ValueError, KeyError) as e:
            logger.error(f"Invalid type string provided to ValueFactory: {e}")
            raise ValueError(f"Invalid type string provided: {e}") from e

        # --- Infer value type if not provided ---
        inferred_value_type = resolved_value_type or IfcValueType.from_python_type(value)

        # --- Type Conversion & Validation ---
        original_value = value  # Keep original for logging if conversion fails
        try:
            if inferred_value_type == IfcValueType.INTEGER:
                value = int(value)
            elif inferred_value_type == IfcValueType.REAL:
                value = float(value)
            elif (
                inferred_value_type == IfcValueType.BOOLEAN
                or inferred_value_type == IfcValueType.LOGICAL
            ):
                # Allow flexible boolean conversion
                bool_val = convert.as_bool(value)
                if bool_val is None:
                    raise ValueError("Not a valid boolean representation")
                value = bool_val
                # Standardize on LOGICAL if boolean-like? Or keep BOOLEAN if explicitly requested?
                # Let's keep the inferred/requested type for now.
            elif inferred_value_type in (
                IfcValueType.TEXT,
                IfcValueType.LABEL,
                IfcValueType.IDENTIFIER,
            ):
                value = str(value)
            # Add other conversions if needed (e.g., date/time)

        except (ValueError, TypeError) as e:
            logger.error(
                f"Cannot convert value '{original_value}' to required type {inferred_value_type.value}: {e}"
            )
            raise ValueError(
                f"Value '{original_value}' cannot be converted to {inferred_value_type.value}."
            ) from e

        logger.debug(
            f"Creating IfcValue: v='{value}', vt={inferred_value_type.value}, ut={resolved_unit_type.name}, pfx={resolved_prefix.value}"
        )
        # Use the validated/converted value and resolved types
        return IfcValue(
            value=value,
            value_type=inferred_value_type,
            unit_type=resolved_unit_type,
            prefix=resolved_prefix,
        )

    # --- Convenience Methods ---
    # (These remain largely the same, just call the updated create method)

    @staticmethod
    def create_length(value: float, prefix: IfcPrefix | str = IfcPrefix.NONE) -> IfcValue:
        return ValueFactory.create(value, IfcValueType.REAL, IfcUnitType.LENGTH, prefix)

    @staticmethod
    def create_meter(value: float) -> IfcValue:
        return ValueFactory.create_length(value, IfcPrefix.NONE)

    @staticmethod
    def create_centimeter(value: float) -> IfcValue:
        return ValueFactory.create_length(value, IfcPrefix.CENTI)

    @staticmethod
    def create_millimeter(value: float) -> IfcValue:
        return ValueFactory.create_length(value, IfcPrefix.MILLI)

    @staticmethod
    def create_area(value: float, prefix: IfcPrefix | str = IfcPrefix.NONE) -> IfcValue:
        return ValueFactory.create(value, IfcValueType.REAL, IfcUnitType.AREA, prefix)

    @staticmethod
    def create_volume(value: float, prefix: IfcPrefix | str = IfcPrefix.NONE) -> IfcValue:
        return ValueFactory.create(value, IfcValueType.REAL, IfcUnitType.VOLUME, prefix)

    @staticmethod
    def create_mass(value: float, prefix: IfcPrefix | str = IfcPrefix.NONE) -> IfcValue:
        return ValueFactory.create(value, IfcValueType.REAL, IfcUnitType.MASS, prefix)

    @staticmethod
    def create_kilogram(value: float) -> IfcValue:
        return ValueFactory.create_mass(value, IfcPrefix.KILO)

    @staticmethod
    def create_count(
        value: int | float,
    ) -> IfcValue:  # Allow float input, will be converted
        return ValueFactory.create(value, IfcValueType.INTEGER, IfcUnitType.COUNT, IfcPrefix.NONE)

    @staticmethod
    def create_text(value: str) -> IfcValue:
        return ValueFactory.create(value, IfcValueType.TEXT, IfcUnitType.UNKNOWN, IfcPrefix.NONE)

    @staticmethod
    def create_label(value: str) -> IfcValue:
        return ValueFactory.create(value, IfcValueType.LABEL, IfcUnitType.UNKNOWN, IfcPrefix.NONE)

    @staticmethod
    def create_identifier(value: str) -> IfcValue:
        return ValueFactory.create(
            value, IfcValueType.IDENTIFIER, IfcUnitType.UNKNOWN, IfcPrefix.NONE
        )

    @staticmethod
    def create_bool(value: bool | str | int) -> IfcValue:  # Allow flexible input
        # Use LOGICAL as the standard boolean type from factory perspective
        return ValueFactory.create(value, IfcValueType.LOGICAL, IfcUnitType.UNKNOWN, IfcPrefix.NONE)


value_factory = ValueFactory()
