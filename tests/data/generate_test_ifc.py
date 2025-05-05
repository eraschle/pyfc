from pathlib import Path

import ifcopenshell

# Pfad für die neue Datei
OUTPUT_IFC = Path(__file__).parent / "test_ifc4x3.ifc"

# Konstanten aus den Tests
KNOWN_ELEMENT_ID = 68
KNOWN_ELEMENT_GUID = "0DyViLJJ175RvWQi1rE7a6"
KNOWN_ELEMENT_NAME = "Test Wall Element"

KNOWN_TYPE_ID = 66
KNOWN_TYPE_GUID = "0_8SeeJGr948J4bU1RPXce"
KNOWN_TYPE_NAME = "Test Wall Type"

KNOWN_PSET_ID_ON_ELEMENT = 77
KNOWN_PSET_NAME_ON_ELEMENT = "Qto_WallBaseQuantities"

KNOWN_PROP_ID_IN_PSET = 74
KNOWN_PROP_NAME_IN_PSET = "Width"
KNOWN_PROP_VALUE_IN_PSET = 200.0000000000794

# Erstellen einer neuen Datei mit IFC4X3_ADD2 Schema
ifc = ifcopenshell.file(schema="IFC4X3")

# Erstellen der grundlegenden Projektstruktur
project = ifc.create_entity(
    "IfcProject", GlobalId=ifcopenshell.guid.new(), Name="Test Project"
)
context = ifc.create_entity("IfcGeometricRepresentationContext", ContextType="Model")
units = ifc.create_entity("IfcUnitAssignment")

# Hinzufügen von Längeneinheit
length_unit = ifc.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE")
units.Units = [length_unit]

project.RepresentationContexts = [context]
project.UnitsInContext = units

# Erstellen von Standort und Gebäude
site = ifc.create_entity("IfcSite", GlobalId=ifcopenshell.guid.new(), Name="Test Site")
building = ifc.create_entity(
    "IfcBuilding", GlobalId=ifcopenshell.guid.new(), Name="Test Building"
)

# Erstellen der Containment-Beziehungen
rel_contained_in_spatial_structure1 = ifc.create_entity(
    "IfcRelContainedInSpatialStructure",
    GlobalId=ifcopenshell.guid.new(),
    Name="Site Container",
    RelatingStructure=site,
    RelatedElements=[building],
)

rel_aggregates = ifc.create_entity(
    "IfcRelAggregates",
    GlobalId=ifcopenshell.guid.new(),
    Name="Project Container",
    RelatingObject=project,
    RelatedObjects=[site],
)

# Erstellen des Wandtyps mit spezifischer ID und GUID
wall_type = ifc.create_entity(
    "IfcWallType",
    id=KNOWN_TYPE_ID,
    GlobalId=KNOWN_TYPE_GUID,
    Name=KNOWN_TYPE_NAME,
    PredefinedType="STANDARD",
)

# Erstellen der Wand mit spezifischer ID und GUID
wall = ifc.create_entity(
    "IfcWall",
    id=KNOWN_ELEMENT_ID,
    GlobalId=KNOWN_ELEMENT_GUID,
    Name=KNOWN_ELEMENT_NAME,
    PredefinedType="STANDARD",
)

# Verknüpfen der Wand mit dem Wandtyp
rel_defines_by_type = ifc.create_entity(
    "IfcRelDefinesByType",
    GlobalId=ifcopenshell.guid.new(),
    RelatingType=wall_type,
    RelatedObjects=[wall],
)

# Verknüpfen der Wand mit dem Gebäude
rel_contained_in_spatial_structure2 = ifc.create_entity(
    "IfcRelContainedInSpatialStructure",
    GlobalId=ifcopenshell.guid.new(),
    RelatingStructure=building,
    RelatedElements=[wall],
)

# Erstellen des Property Sets für die Wand
quantity_set = ifc.create_entity(
    "IfcElementQuantity",
    id=KNOWN_PSET_ID_ON_ELEMENT,
    GlobalId=ifcopenshell.guid.new(),
    Name=KNOWN_PSET_NAME_ON_ELEMENT,
    MethodOfMeasurement="Test Method",
)

# Erstellen der Quantity (Property) im Property Set
width_quantity = ifc.create_entity(
    "IfcQuantityLength",
    id=KNOWN_PROP_ID_IN_PSET,
    Name=KNOWN_PROP_NAME_IN_PSET,
    LengthValue=KNOWN_PROP_VALUE_IN_PSET,
)

quantity_set.Quantities = [width_quantity]

# Verknüpfen des Property Sets mit der Wand
rel_defines_by_properties = ifc.create_entity(
    "IfcRelDefinesByProperties",
    GlobalId=ifcopenshell.guid.new(),
    RelatingPropertyDefinition=quantity_set,
    RelatedObjects=[wall],
)

# Erstellen eines zusätzlichen Property Sets für Tests
test_pset = ifc.create_entity(
    "IfcPropertySet",
    GlobalId=ifcopenshell.guid.new(),
    Name="Test_PropertySet",
    HasProperties=[
        ifc.create_entity(
            "IfcPropertySingleValue",
            Name="TestProperty",
            NominalValue=ifc.create_entity("IfcText", wrappedValue="Test Value"),
        )
    ],
)

rel_defines_by_properties2 = ifc.create_entity(
    "IfcRelDefinesByProperties",
    GlobalId=ifcopenshell.guid.new(),
    RelatingPropertyDefinition=test_pset,
    RelatedObjects=[wall],
)

# Speichern der Datei
ifc.write(OUTPUT_IFC)
print(f"Neue IFC-Datei erstellt: {OUTPUT_IFC}")
