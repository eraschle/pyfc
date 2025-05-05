# Path: ifcproj/models/ifc_types.py
from enum import StrEnum


class IfcEntityType(StrEnum):
    """Enum for common IFC entity type names (class names)."""

    # General
    PROJECT = "IfcProject"
    OWNER_HISTORY = "IfcOwnerHistory"
    APPLICATION = "IfcApplication"
    PERSON = "IfcPerson"
    ORGANIZATION = "IfcOrganization"
    PERSON_AND_ORGANIZATION = "IfcPersonAndOrganization"
    SI_UNIT = "IfcSIUnit"
    CONVERSION_BASED_UNIT = "IfcConversionBasedUnit"
    DERIVED_UNIT = "IfcDerivedUnit"
    CONTEXT_DEPENDENT_UNIT = "IfcContextDependentUnit"
    UNIT_ASSIGNMENT = "IfcUnitAssignment"
    GEOMETRIC_REPRESENTATION_CONTEXT = "IfcGeometricRepresentationContext"
    CARTESIAN_POINT = "IfcCartesianPoint"
    AXIS2_PLACEMENT_3D = "IfcAxis2Placement3D"
    SITE = "IfcSite"
    BUILDING = "IfcBuilding"

    # Objects & Types
    OBJECT = "IfcObject"
    OBJECT_TYPE = "IfcObjectType"
    TYPE_OBJECT = "IfcTypeObject"
    WALL = "IfcWall"
    WALL_TYPE = "IfcWallType"

    # Properties & Quantities
    PROPERTY = "IfcProperty"
    PROPERTY_SET = "IfcPropertySet"
    PROPERTY_SINGLE_VALUE = "IfcPropertySingleValue"
    PHYSICAL_QUANTITY = "IfcPhysicalQuantity"
    ELEMENT_QUANTITY = "IfcElementQuantity"
    QUANTITY_LENGTH = "IfcQuantityLength"
    QUANTITY_AREA = "IfcQuantityArea"
    QUANTITY_VOLUME = "IfcQuantityVolume"
    QUANTITY_WEIGHT = "IfcQuantityWeight"
    QUANTITY_COUNT = "IfcQuantityCount"
    QUANTITY_TIME = "IfcQuantityTime"

    # Value Types (also covered by IfcValueType, but useful here for is_a checks)
    BOOLEAN = "IfcBoolean"
    INTEGER = "IfcInteger"
    REAL = "IfcReal"
    TEXT = "IfcText"
    LABEL = "IfcLabel"
    IDENTIFIER = "IfcIdentifier"
    LOGICAL = "IfcLogical"

    # Add specific Measure types if needed for is_a checks
    LENGTH_MEASURE = "IfcLengthMeasure"
    AREA_MEASURE = "IfcAreaMeasure"
    VOLUME_MEASURE = "IfcVolumeMeasure"
    MASS_MEASURE = "IfcMassMeasure"
    TIME_MEASURE = "IfcTimeMeasure"
    COUNT_MEASURE = "IfcCountMeasure"
    # ... other measures

    # Relationships
    REL_DEFINES_BY_PROPERTIES = "IfcRelDefinesByProperties"
    REL_DEFINES_BY_TYPE = "IfcRelDefinesByType"
    REL_CONTAINED_IN_SPATIAL_STRUCTURE = "IfcRelContainedInSpatialStructure"
    REL_AGGREGATES = "IfcRelAggregates"

    # Add other frequently used types as needed...
