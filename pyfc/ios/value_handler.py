import logging
from typing import TYPE_CHECKING, Any

from pyfc.errors import IfcAdapterError

# Import value_factory from models
from pyfc.models import IfcPrefix, IfcUnitType, IfcValue, IfcValueType, value_factory

# Import IfcEntityType
from pyfc.models.ifc_types import IfcEntityType
from pyfc.utils import convert

if TYPE_CHECKING:
    from .context import IosModelContext  # Use type checking import

logger = logging.getLogger(__name__)


class IosValueUnitHandler:
    """Handles the creation, retrieval, and interpretation of IFC value and unit entities."""

    def __init__(self, context: "IosModelContext"):
        """
        Initializes the handler with the IFC model context.

        Parameters
        ----------
        context : IosModelContext
            The context for interacting with the IFC model.
        """
        self.context = context

    def create_ifc_value_entity(self, ifc_value: IfcValue) -> Any | None:
        """
        Create an IFC value entity (e.g., IfcReal, IfcText) based on the IfcValue object.

        Parameters
        ----------
        ifc_value : IfcValue
            The IfcValue object containing the value and type information.

        Returns
        -------
        Any | None
            The created ifcopenshell entity instance, or None if conversion fails.

        Raises
        ------
        IfcAdapterError
            If the value cannot be converted or the entity cannot be created.
        """
        value = ifc_value.value
        value_type = ifc_value.value_type
        # Use IfcValueType.value which is already the IFC type string (e.g., "IfcReal")
        ifc_type_str = value_type.value
        try:
            # Map IfcValueType enum to IFC entity type string and convert value
            converted_value: Any = None
            # Use IfcValueType enum members for comparison
            if value_type == IfcValueType.BOOLEAN or value_type == IfcValueType.LOGICAL:
                converted_value = convert.as_bool(value)
                if converted_value is None:
                    raise ValueError(f"Could not convert '{value}' to Boolean/Logical.")
                # Use IfcLogical as the target type for boolean-like values in properties/measures
                # Use IfcEntityType for the string value
                ifc_type_str = IfcEntityType.LOGICAL.value
            elif value_type == IfcValueType.INTEGER:
                converted_value = convert.as_int(value)
                if converted_value is None:
                    raise ValueError(f"Could not convert '{value}' to Integer.")
                # Use IfcEntityType for the string value
                ifc_type_str = IfcEntityType.INTEGER.value
            elif value_type == IfcValueType.REAL:
                converted_value = convert.as_float(value)
                if converted_value is None:
                    raise ValueError(f"Could not convert '{value}' to Float/Real.")
                # Use IfcEntityType for the string value
                ifc_type_str = IfcEntityType.REAL.value
            elif value_type == IfcValueType.TEXT:
                converted_value = str(value)
                # Use IfcEntityType for the string value
                ifc_type_str = IfcEntityType.TEXT.value
            elif value_type == IfcValueType.LABEL:
                converted_value = str(value)
                # Use IfcEntityType for the string value
                ifc_type_str = IfcEntityType.LABEL.value
            elif value_type == IfcValueType.IDENTIFIER:
                converted_value = str(value)
                # Use IfcEntityType for the string value
                ifc_type_str = IfcEntityType.IDENTIFIER.value
            # Add other type conversions if needed (e.g., dates, times)
            else:
                # This case should be less likely now with better mapping in IfcValueType
                logger.warning(
                    f"Unhandled IfcValueType '{value_type.name}' during IFC entity creation. Attempting str() and IfcText."
                )
                converted_value = str(value)
                # Use IfcEntityType for the string value
                ifc_type_str = IfcEntityType.TEXT.value  # Fallback to IfcText

            # Check if conversion was successful before creating entity
            if converted_value is None:
                logger.error(
                    f"Value conversion resulted in None for value '{value}' (Type: {value_type.name}). Cannot create IFC entity."
                )
                return None

            # Create the IFC entity using the context and the determined type string
            ifc_value_entity = self.context.create_entity(ifc_type_str, converted_value)
            logger.debug(
                f"Created IFC value entity: #{ifc_value_entity.id()} ({ifc_type_str}) with value: {converted_value}"
            )
            return ifc_value_entity

        except (ValueError, TypeError) as e:
            logger.error(
                f"Error converting value '{value}' to type required by {ifc_type_str}: {e}"
            )
            raise IfcAdapterError(
                f"Could not create IFC value entity for '{value}' as {value_type.name}: {e}"
            ) from e
        except Exception as e:
            # Catch potential errors during entity creation in ifcopenshell
            logger.error(
                f"Error creating IFC value entity of type {ifc_type_str} for value '{value}': {e}"
            )
            raise IfcAdapterError(
                f"Could not create IFC value entity for '{value}' as {value_type.name}: {e}"
            ) from e

    def get_or_create_unit(
        self, unit_type: IfcUnitType, prefix: IfcPrefix = IfcPrefix.NONE
    ) -> Any | None:
        """
        Get or create an IfcSIUnit or other relevant unit entity based on the unit type and prefix.
        Adds the created unit to the project's UnitsInContext if necessary.

        Parameters
        ----------
        unit_type : IfcUnitType
            The semantic type of the unit (e.g., LENGTH, AREA).
        prefix : IfcPrefix, optional
            The SI prefix (e.g., KILO, MILLI), by default IfcPrefix.NONE.

        Returns
        -------
        Any | None
            The ifcopenshell unit entity instance, or None if the unit type is
            UNKNOWN, COUNT, or cannot be mapped/created.
        """
        if unit_type in (IfcUnitType.UNKNOWN, IfcUnitType.COUNT):
            logger.debug(f"Unit creation skipped for unit type: {unit_type.name}")
            return None

        # Use properties from the updated IfcUnitType enum
        ifc_unit_enum = unit_type.ifc_unit_enum
        default_name = unit_type.default_si_name
        is_si = unit_type.is_si

        if not ifc_unit_enum:  # Should not happen if UNKNOWN/COUNT are handled, but good check
            logger.warning(
                f"No IFC UnitEnum defined for IfcUnitType '{unit_type.name}'. Cannot create unit."
            )
            return None

        # Use IfcPrefix.value which is now the IFC standard string (or "")
        ifc_prefix_enum_str = prefix.value if prefix != IfcPrefix.NONE else None

        # --- Search for existing unit in project context ---
        units_in_context = None
        project_units = []
        project = None
        try:
            # Use IfcEntityType
            project_list = self.context.ifc_by_type(IfcEntityType.PROJECT)
            if not project_list:
                logger.error("Could not find IfcProject to search for units.")
            else:
                project = project_list[0]
                if hasattr(project, "UnitsInContext") and project.UnitsInContext:
                    units_in_context = project.UnitsInContext
                    project_units = list(units_in_context.Units or [])  # Ensure list
                    for unit in project_units:
                        # Check IfcSIUnit using IfcEntityType
                        if (
                            is_si
                            and unit.is_a(IfcEntityType.SI_UNIT)
                            and hasattr(unit, "UnitType")
                            and unit.UnitType == ifc_unit_enum
                        ):
                            current_prefix_val = getattr(unit, "Prefix", None)
                            # Match prefix (handle None vs "")
                            if current_prefix_val == ifc_prefix_enum_str or (
                                current_prefix_val is None and ifc_prefix_enum_str is None
                            ):  # Match None with None
                                logger.debug(
                                    f"Found existing IfcSIUnit for {ifc_unit_enum} (Prefix: {ifc_prefix_enum_str or 'None'}): #{unit.id()}"
                                )
                                return unit
                        # TODO: Check for other unit types (IfcDerivedUnit, IfcConversionBasedUnit) using IfcEntityType

                else:
                    logger.warning(
                        "IfcProject found, but no UnitsInContext assigned. Cannot search for existing units."
                    )

        except Exception as e:
            logger.error(f"Error searching for existing units: {e}")
            # Fallback to creating a new unit

        # --- Create new unit if not found ---
        new_unit = None
        if is_si:
            logger.info(
                f"Creating new IfcSIUnit for {ifc_unit_enum} (Prefix: {ifc_prefix_enum_str or 'None'})"
            )
            create_args = {
                "UnitType": ifc_unit_enum,
                "Name": default_name,
            }
            if ifc_prefix_enum_str:
                # Handle KILO prefix for GRAM base unit -> KILOGRAM name convention
                if unit_type == IfcUnitType.MASS and prefix == IfcPrefix.KILO:
                    create_args["Name"] = "KILOGRAM"
                    # Prefix attribute is not set when Name is KILOGRAM for IfcSIUnit standard representation
                else:
                    create_args["Prefix"] = ifc_prefix_enum_str

            try:
                # Use IfcEntityType
                new_unit = self.context.create_entity(IfcEntityType.SI_UNIT, **create_args)
                logger.debug(f"Created new IfcSIUnit: #{new_unit.id()}")
            except Exception as e:
                logger.error(f"Failed to create IfcSIUnit: {e}")
                return None
        else:
            # TODO: Implement creation for IfcDerivedUnit, IfcConversionBasedUnit etc. using IfcEntityType
            logger.warning(
                f"Creation of non-SI unit type '{ifc_unit_enum}' for '{unit_type.name}' is not implemented."
            )
            return None

        # --- Add the new unit to the project's unit context ---
        if new_unit:
            if project and not units_in_context:
                logger.info("Creating new IfcUnitAssignment for project.")
                try:
                    # Use IfcEntityType
                    units_in_context = self.context.create_entity(
                        IfcEntityType.UNIT_ASSIGNMENT, Units=[]
                    )
                    project.UnitsInContext = units_in_context
                    project_units = []
                    self.context.mark_modified()
                except Exception as e:
                    logger.error(f"Failed to create IfcUnitAssignment: {e}")
                    units_in_context = None

            if units_in_context:
                project_units.append(new_unit)
                units_in_context.Units = tuple(project_units)
                logger.debug(f"Added new unit #{new_unit.id()} to project UnitsInContext")
                self.context.mark_modified()
            else:
                logger.warning(
                    f"Could not add new unit #{new_unit.id()} to project context (Project or UnitsInContext missing/creation failed)."
                )
                self.context.mark_modified()  # Still created the unit
            return new_unit
        else:
            return None

    def get_ifc_value_from_entity(self, entity: Any) -> IfcValue | None:
        """
        Get the value of a property or quantity entity as an IfcValue object.

        Parameters
        ----------
        entity : Any
            The ifcopenshell entity instance (IfcProperty or IfcPhysicalQuantity).

        Returns
        -------
        IfcValue | None
            The IfcValue object representing the entity's value, or None if extraction fails.
        """
        if not entity:
            logger.error("Cannot get value from None entity.")
            return None

        entity_id = entity.id()  # For logging

        try:
            raw_value: Any = None
            value_type: IfcValueType | None = None
            unit_type: IfcUnitType = IfcUnitType.UNKNOWN  # Default
            prefix: IfcPrefix = IfcPrefix.NONE  # Default
            unit_entity: Any = None

            # --- Extract Raw Value and Infer Value Type ---
            # Use IfcEntityType for checks
            if entity.is_a(IfcEntityType.PROPERTY_SINGLE_VALUE):
                if hasattr(entity, "NominalValue") and entity.NominalValue:
                    nominal_value = entity.NominalValue
                    raw_value = nominal_value.wrappedValue
                    ifc_type_name = nominal_value.is_a()
                    # Map IFC type string to IfcValueType enum using the updated _missing_ logic
                    value_type = IfcValueType(ifc_type_name)

                if hasattr(entity, "Unit"):
                    unit_entity = entity.Unit

            # --- Handle IfcQuantity subclasses using IfcEntityType ---
            elif entity.is_a(IfcEntityType.QUANTITY_LENGTH):
                if hasattr(entity, "LengthValue"):
                    raw_value = entity.LengthValue
                value_type = IfcValueType.REAL
                unit_type = IfcUnitType.LENGTH
                if hasattr(entity, "Unit"):
                    unit_entity = entity.Unit
            elif entity.is_a(IfcEntityType.QUANTITY_AREA):
                if hasattr(entity, "AreaValue"):
                    raw_value = entity.AreaValue
                value_type = IfcValueType.REAL
                unit_type = IfcUnitType.AREA
                if hasattr(entity, "Unit"):
                    unit_entity = entity.Unit
            elif entity.is_a(IfcEntityType.QUANTITY_VOLUME):
                if hasattr(entity, "VolumeValue"):
                    raw_value = entity.VolumeValue
                value_type = IfcValueType.REAL
                unit_type = IfcUnitType.VOLUME
                if hasattr(entity, "Unit"):
                    unit_entity = entity.Unit
            elif entity.is_a(IfcEntityType.QUANTITY_WEIGHT):  # Maps to MASS
                if hasattr(entity, "WeightValue"):
                    raw_value = entity.WeightValue
                value_type = IfcValueType.REAL
                unit_type = IfcUnitType.MASS
                if hasattr(entity, "Unit"):
                    unit_entity = entity.Unit
            elif entity.is_a(IfcEntityType.QUANTITY_COUNT):
                if hasattr(entity, "CountValue"):
                    raw_value = entity.CountValue
                # CountValue can be IfcInteger or IfcReal according to schema
                value_type = IfcValueType.from_python_type(raw_value)  # Infer from actual value
                unit_type = IfcUnitType.COUNT
            elif entity.is_a(IfcEntityType.QUANTITY_TIME):
                if hasattr(entity, "TimeValue"):
                    raw_value = entity.TimeValue
                value_type = IfcValueType.REAL  # IfcTimeMeasure is Real
                unit_type = IfcUnitType.TIME
                if hasattr(entity, "Unit"):
                    unit_entity = entity.Unit
            # Add other quantity types if needed

            else:
                # Handle other IfcProperty types if necessary
                logger.warning(
                    f"Cannot extract value from property/quantity {entity_id} of type {entity.is_a()}. "
                    "Not a SingleValue or known Quantity."
                )
                return None

            # --- Determine Unit Type and Prefix from Unit Entity ---
            if unit_entity:
                # Use IfcEntityType for checks
                if unit_entity.is_a(IfcEntityType.SI_UNIT):
                    si_unit_type_enum = getattr(unit_entity, "UnitType", None)
                    si_prefix_enum = getattr(unit_entity, "Prefix", None)
                    si_name = getattr(unit_entity, "Name", None)

                    # Map SI UnitType enum back to IfcUnitType enum using classmethod
                    inferred_unit_type = IfcUnitType.from_ifc_unit_enum(si_unit_type_enum)

                    if inferred_unit_type != IfcUnitType.UNKNOWN:
                        if unit_type == IfcUnitType.UNKNOWN:
                            unit_type = inferred_unit_type
                        elif unit_type != inferred_unit_type:
                            logger.warning(
                                f"Unit type mismatch for property {entity_id}: Entity implies {unit_type.name}, "
                                f"but IfcSIUnit specifies {inferred_unit_type.name}. Using entity type."
                            )
                    # No warning needed if mapping failed, already logged in from_ifc_unit_enum

                    # Map SI Prefix enum back to IfcPrefix enum using constructor/missing
                    # Handle KILOGRAM name convention for mass explicitly
                    if unit_type == IfcUnitType.MASS and si_name == "KILOGRAM":
                        prefix = IfcPrefix.KILO
                    else:
                        # Use constructor which handles None, "", or valid string via _missing_
                        prefix = IfcPrefix(si_prefix_enum)

                # Use IfcEntityType for checks
                elif unit_entity.is_a(IfcEntityType.CONVERSION_BASED_UNIT):
                    logger.debug(
                        f"Property {entity_id} uses IfcConversionBasedUnit #{unit_entity.id()}. "
                        "Unit/Prefix extraction not fully implemented."
                    )
                    measure = getattr(unit_entity, "Measure", None)
                    # Use classmethod for mapping
                    inferred_unit_type = IfcUnitType.from_measure_type(measure)
                    if (
                        inferred_unit_type != IfcUnitType.UNKNOWN
                        and unit_type == IfcUnitType.UNKNOWN
                    ):
                        unit_type = inferred_unit_type
                    # Prefix is generally NONE for these unless explicitly modeled differently.

                # Use IfcEntityType for checks
                elif unit_entity.is_a(IfcEntityType.DERIVED_UNIT):
                    logger.debug(
                        f"Property {entity_id} uses IfcDerivedUnit #{unit_entity.id()}. "
                        "Unit/Prefix extraction not fully implemented."
                    )
                elif unit_entity.is_a(IfcEntityType.CONTEXT_DEPENDENT_UNIT):
                    logger.debug(
                        f"Property {entity_id} uses IfcContextDependentUnit #{unit_entity.id()}. "
                        "Unit/Prefix extraction not implemented."
                    )
                else:
                    logger.warning(
                        f"Property {entity_id} has an unhandled unit type: {unit_entity.is_a()}. "
                        "Cannot determine prefix/unit type accurately."
                    )

            # --- Create and return IfcValue ---
            if raw_value is not None and value_type is not None:
                try:
                    # Use the factory to ensure consistency and validation
                    # Pass the resolved enums
                    return value_factory.create(
                        value=raw_value,
                        value_type=value_type,  # Pass the resolved IfcValueType enum
                        unit_type=unit_type,  # Pass the resolved IfcUnitType enum
                        prefix=prefix,  # Pass the resolved IfcPrefix enum
                    )
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Error creating IfcValue for property {entity_id} using factory: {e}"
                    )
                    return None
            else:
                logger.warning(
                    f"Could not determine raw value or value type for property/quantity {entity_id}."
                )
                return None

        except Exception as e:
            logger.error(f"Error getting value for property/quantity {entity_id}: {e}")
            return None
