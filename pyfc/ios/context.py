# -*- coding: utf-8 -*-
import logging
import time
from pathlib import Path
from typing import Any

import ifcopenshell as ios

from pyfc.errors import IfcModelContextError

# Import the new Enum
from pyfc.models.ifc_types import IfcEntityType
from pyfc.repository import IModelContext

# Import utilities
from . import utilities as ifc_utils

logger = logging.getLogger(__name__)

IfcEntity = ios.entity_instance  # Alias for entity instance


class IosModelContext(IModelContext):
    """
    Context manager for handling IFC files using ifcopenshell.

    This class provides a context for working with IFC files, including opening,
    saving, and closing the files. It also provides access to the various adapters
    for working with IFC entities.

    Example:
    --------
    ```python
    from pyfc.ios import IosModelContext # Assuming adapters are accessed differently now

    # Open an existing file
    with IosModelContext.open("path/to/your/file.ifc") as context:
        # Access adapters via context properties if implemented that way
        # element = context.objects.get_by_id(123)
        # Or instantiate adapters directly:
        # from pyfc.ios import IosObjectAdapter
        # adapter = IosObjectAdapter(context)
        # element = adapter.get_by_id(123)
        # if element:
        #     print(element.name)
        context.save() # Save changes back to the original file

    # Create a new file
    with IosModelContext.create(schema="IFC4") as context:
        # ... add entities ...
        context.save("path/to/new/file.ifc")
    ```
    """

    def __init__(self, ifc_file: Any, filepath: Path | None = None):
        """
        Initialize the context with an opened ifcopenshell file object.

        Prefer using the classmethods `open()` or `create()` instead of direct instantiation.

        Parameters
        ----------
        ifc_file : ifcopenshell.file
            An opened ifcopenshell file instance.
        filepath : Path | None, optional
            The original file path, if opened from a file. Defaults to None.
        """
        if not isinstance(ifc_file, ios.file):
            raise TypeError("ifc_file must be an instance of ifcopenshell.file")

        self.ifc_model: ios.file = ifc_file
        self._file_path: Path | None = filepath
        self._is_modified: bool = False
        self._owner_history: IfcEntity | None = None  # Cache for owner history
        logger.info(
            f"IosModelContext initialized. Schema: {self.ifc_model.schema}. Path: {self._file_path}"
        )

    @classmethod
    def open(cls, filepath: str | Path) -> "IosModelContext":
        """
        Open an IFC file and create a context.

        Parameters
        ----------
        filepath : str | Path
            The path to the IFC file to open.

        Returns
        -------
        IosModelContext
            An instance of the context manager.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        IfcModelContextError
            If there is an error opening the file with ifcopenshell.
        """
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"IFC file not found at: {path}")
        try:
            ifc_file = ios.open(str(path))
            logger.info(f"Successfully opened IFC file: {path}")
            return cls(ifc_file, path)
        except Exception as e:
            logger.error(f"Error opening IFC file {path}: {e}")
            raise IfcModelContextError(f"Failed to open IFC file {path}: {e}")

    @classmethod
    def create(cls, schema: str = "IFC4X3") -> "IosModelContext":
        """
        Create a new, empty IFC model context in memory.

        Parameters
        ----------
        schema : str, optional
            The IFC schema version to use (e.g., "IFC2X3", "IFC4"). Defaults to "IFC4X3".

        Returns
        -------
        IosModelContext
            An instance of the context manager for the new model.

        Raises
        ------
        IfcModelContextError
            If there is an error creating the file with ifcopenshell.
        """
        try:
            # Use IfcEntityType for schema string? No, schema is specific to ios.file
            ifc_file = ios.file(schema=schema)  # pyright: ignore[reportArgumentType]
            logger.info(f"Successfully created new in-memory IFC model (Schema: {schema})")
            context = cls(ifc_file, None)
            context._setup_basic_project()  # Add basic project structure
            return context
        except Exception as e:
            logger.error(f"Error creating new IFC model (Schema: {schema}): {e}")
            raise IfcModelContextError(f"Failed to create new IFC model: {e}")

    def _setup_basic_project(self):
        """Sets up a minimal IfcProject structure for a new file."""
        # Use IfcEntityType for type checks and creation
        if not self.ifc_by_type(IfcEntityType.PROJECT):
            logger.debug("Setting up basic IfcProject structure...")
            # Ensure owner history exists (getter will create if needed)
            owner_history = self.owner_history

            # Create geometry context (example: 3D)
            # Use IfcEntityType for these types as well
            cartesian_point = self.create_entity(
                IfcEntityType.CARTESIAN_POINT, Coordinates=(0.0, 0.0, 0.0)
            )
            axis_placement = self.create_entity(
                IfcEntityType.AXIS2_PLACEMENT_3D, Location=cartesian_point
            )
            # Create geometric representation context
            context_type = "Model"  # Or 'Plan', 'Section', etc.
            geom_context = self.create_entity(
                IfcEntityType.GEOMETRIC_REPRESENTATION_CONTEXT,
                ContextIdentifier="3D",
                ContextType=context_type,
                CoordinateSpaceDimension=3,
                Precision=1e-5,
                WorldCoordinateSystem=axis_placement,
            )
            # Create units (example: SI units)
            # Use IfcEntityType for unit creation
            units = [
                self.create_entity(IfcEntityType.SI_UNIT, UnitType="LENGTHUNIT", Name="METRE"),
                self.create_entity(IfcEntityType.SI_UNIT, UnitType="AREAUNIT", Name="SQUARE_METRE"),
                self.create_entity(
                    IfcEntityType.SI_UNIT, UnitType="VOLUMEUNIT", Name="CUBIC_METRE"
                ),
                self.create_entity(IfcEntityType.SI_UNIT, UnitType="PLANEANGLEUNIT", Name="RADIAN"),
            ]
            unit_assignment = self.create_entity(
                IfcEntityType.UNIT_ASSIGNMENT, Units=ifc_utils.ensure_tuple(units)
            )

            # Create IfcProject using IfcEntityType
            self.create_entity(
                IfcEntityType.PROJECT,
                GlobalId=ios.guid.new(),
                OwnerHistory=owner_history,
                Name="Default Project",
                UnitsInContext=unit_assignment,
                RepresentationContexts=ifc_utils.ensure_tuple([geom_context]),
            )
            # No need to mark modified here, create_entity does it
            logger.info("Basic IfcProject structure created.")

    def save(self, filepath: str | Path | None = None) -> None:
        """
        Save the IFC model to a file.

        If filepath is provided, saves to that path and updates the context's file path.
        If filepath is None, saves back to the original file path (if available).

        Parameters
        ----------
        filepath : str | Path | None, optional
            The path to save the IFC file to. Defaults to None.

        Raises
        ------
        IfcModelContextError
            If the file cannot be saved (e.g., no path specified for a new model, write errors).
        """
        target_path: Path | None = None
        if filepath:
            target_path = Path(filepath)
        elif self._file_path:
            target_path = self._file_path
        else:
            raise IfcModelContextError(
                "Cannot save: No filepath provided and context was not opened from a file."
            )

        try:
            self.ifc_model.write(str(target_path))
            self._file_path = target_path
            self._is_modified = False
            logger.info(f"Successfully saved IFC model to: {target_path}")
        except Exception as e:
            logger.error(f"Error saving IFC model to {target_path}: {e}")
            raise IfcModelContextError(f"Failed to save IFC model to {target_path}: {e}")

    def ifc_by_id(self, ifc_id: int) -> IfcEntity | None:
        """Get an IFC entity by its ID."""
        try:
            return self.ifc_model.by_id(ifc_id)
        except Exception:
            # ifcopenshell raises a generic exception if ID not found
            return None

    def ifc_by_guid(self, guid: str) -> IfcEntity | None:
        """Get an IFC entity by its GlobalId (GUID)."""
        try:
            # Ensure GUID is in the correct format if needed (ifcopenshell usually handles it)
            # guid = ios.guid.compress(guid) # Example if needed
            return self.ifc_model.by_guid(guid)
        except Exception:
            return None

    def ifc_by_type(self, ifc_type: str | IfcEntityType) -> list[IfcEntity]:
        """Get all IFC entities of a specific type."""
        type_str = ifc_type.value if isinstance(ifc_type, IfcEntityType) else ifc_type
        try:
            return self.ifc_model.by_type(type_str)
        except Exception as e:
            logger.error(f"Error retrieving entities by type '{type_str}': {e}")
            return []

    def create_entity(self, type: str | IfcEntityType, *args, **kwargs) -> IfcEntity:
        """
        Create a new IFC entity.

        Parameters
        ----------
        type : str | IfcEntityType
            The IFC type name (e.g., "IfcWall", IfcEntityType.WALL).
        *args :
            Positional arguments for the entity constructor (use sparingly, prefer kwargs).
        **kwargs :
            Keyword arguments for the entity constructor (e.g., Name="MyWall").
            GlobalId and OwnerHistory are often handled automatically if not provided,
            but explicit provision is safer for relationships.

        Returns
        -------
        IfcEntity
            The newly created entity instance.

        Raises
        ------
        IfcModelContextError
            If the entity creation fails.
        """
        type_str = type.value if isinstance(type, IfcEntityType) else type
        try:
            # Ensure GlobalId is present if required (most IfcRoot subtypes)
            # ifcopenshell often adds it automatically if missing, but check schema if needed.
            # if "GlobalId" not in kwargs and issubclass(self.ifc_model.schema.declaration_by_name(type_str), self.ifc_model.schema.declaration_by_name("IfcRoot")):
            #     kwargs["GlobalId"] = ios.guid.new()

            # Ensure OwnerHistory is present if required
            # This check might be too broad; apply only where necessary (e.g., IfcRoot subtypes)
            # is_root_subtype = False # Determine this based on schema inspection if needed
            # if "OwnerHistory" not in kwargs and is_root_subtype:
            #     kwargs["OwnerHistory"] = self.owner_history # Use the property

            entity = self.ifc_model.create_entity(type_str, *args, **kwargs)
            if entity is None:
                raise IfcModelContextError(
                    f"Failed to create entity of type {type_str} (returned None)"
                )
            logger.debug(f"Created entity: #{entity.id()} - {entity.is_a()}")
            self.mark_modified()
            return entity
        except Exception as e:
            # Log the arguments that failed
            log_args = args if args else ""
            log_kwargs = kwargs if kwargs else ""
            logger.error(
                f"Error creating entity of type {type_str} with args {log_args} and kwargs {log_kwargs}: {e}"
            )
            raise IfcModelContextError(f"Failed to create entity of type {type_str}: {e}")

    def remove_entity(self, entity: IfcEntity) -> bool:
        """
        Remove an IFC entity from the model.

        Parameters
        ----------
        entity : IfcEntity
            The entity instance to remove.

        Returns
        -------
        bool
            True if the entity was removed successfully, False otherwise.
        """
        try:
            entity_id = entity.id()
            entity_type = entity.is_a()
            self.ifc_model.remove(entity)
            logger.info(f"Removed entity: #{entity_id} - {entity_type}")
            self.mark_modified()
            return True
        except Exception as e:
            logger.error(f"Error removing entity #{entity.id()} ({entity.is_a()}): {e}")
            return False

    def close(self) -> None:
        """Closes the context. For ifcopenshell, this mainly clears the reference."""
        # ifcopenshell file objects don't have an explicit close method
        # Just log and clear reference
        logger.info(f"Closing IosModelContext. Path: {self._file_path}")
        self._ifc_model = None
        self._is_modified = False

    def mark_modified(self) -> bool:
        """Marks the context as modified."""
        if not self._is_modified:
            logger.debug(f"Context marked as modified. Path: {self._file_path}")
            self._is_modified = True
        return True

    @property
    def is_modified(self) -> bool:
        """Check if the model has been modified since the last save."""
        return self._is_modified

    @property
    def file_path(self) -> Path | None:
        """Get the file path associated with the context, if any."""
        return self._file_path

    @property
    def owner_history(self) -> IfcEntity:
        """
        Gets or creates the IfcOwnerHistory for the model.

        Searches for an existing IfcOwnerHistory. If none is found,
        creates a default one with placeholder information.

        Returns
        -------
        IfcEntity
            The found or newly created IfcOwnerHistory entity.

        Raises
        ------
        IfcModelContextError
            If the owner history cannot be found or created.
        """
        if self._owner_history is not None:
            # Verify it hasn't been deleted from the model somehow
            try:
                if self.ifc_model.by_id(self._owner_history.id()):
                    return self._owner_history
                else:
                    logger.warning(
                        "Cached OwnerHistory entity no longer exists in model. Re-fetching."
                    )
                    self._owner_history = None
            except Exception:
                logger.warning("Error verifying cached OwnerHistory. Re-fetching.")
                self._owner_history = None

        # Try to find existing owner history using IfcEntityType
        histories = self.ifc_by_type(IfcEntityType.OWNER_HISTORY)

        if histories:
            # Select the first one found. Could add logic to select a specific one if needed.
            self._owner_history = histories[0]
            logger.debug(f"Found existing IfcOwnerHistory: #{self._owner_history.id()}")
            return self._owner_history

        # If not found, create a default one
        logger.info("No IfcOwnerHistory found, creating a default one.")
        try:
            # Create minimal required nested entities with placeholders
            # Use existing entities if they happen to exist to avoid duplicates
            # Use IfcEntityType for creation
            persons = self.ifc_by_type(IfcEntityType.PERSON)
            person = (
                persons[0]
                if persons
                else self.create_entity(
                    IfcEntityType.PERSON, GivenName="Not", FamilyName="Specified"
                )
            )

            orgs = self.ifc_by_type(IfcEntityType.ORGANIZATION)
            organization = (
                orgs[0]
                if orgs
                else self.create_entity(IfcEntityType.ORGANIZATION, Name="Not Specified")
            )

            persons_orgs = self.ifc_by_type(IfcEntityType.PERSON_AND_ORGANIZATION)
            # Find existing matching PersonAndOrg if possible
            person_org = None
            for po in persons_orgs:
                if po.ThePerson == person and po.TheOrganization == organization:
                    person_org = po
                    break
            if not person_org:
                person_org = self.create_entity(
                    IfcEntityType.PERSON_AND_ORGANIZATION,
                    ThePerson=person,
                    TheOrganization=organization,
                )

            apps = self.ifc_by_type(IfcEntityType.APPLICATION)
            # Find existing matching Application if possible
            owning_application = None
            app_id = "ifcproj_default_app"
            app_name = "ifcproj Default Application"
            app_version = "1.0"
            for app in apps:
                if (
                    app.ApplicationDeveloper == organization
                    and app.Version == app_version
                    and app.ApplicationFullName == app_name
                    and app.ApplicationIdentifier == app_id
                ):
                    owning_application = app
                    break
            if not owning_application:
                owning_application = self.create_entity(
                    IfcEntityType.APPLICATION,
                    ApplicationDeveloper=organization,  # Re-use organization
                    Version=app_version,
                    ApplicationFullName=app_name,
                    ApplicationIdentifier=app_id,
                )

            # Create the IfcOwnerHistory using IfcEntityType
            # Timestamp needs to be an integer for IfcTimeStamp
            creation_timestamp = int(time.time())
            self._owner_history = self.create_entity(
                IfcEntityType.OWNER_HISTORY,
                OwningUser=person_org,
                OwningApplication=owning_application,
                State="READWRITE",  # Or other IfcStateEnum
                ChangeAction="ADDED",  # Or other IfcChangeActionEnum
                CreationDate=creation_timestamp,
            )
            logger.debug(f"Created default IfcOwnerHistory: #{self._owner_history.id()}")
            # No need to call self.mark_modified() here as create_entity already does
            return self._owner_history

        except Exception as e:
            logger.error(f"Failed to create default IfcOwnerHistory: {e}")
            raise IfcModelContextError(f"Failed to get or create IfcOwnerHistory: {e}")

    def __enter__(self) -> "IosModelContext":
        """Enter the runtime context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the runtime context, ensuring cleanup."""
        # In the future, could handle transactions (commit/rollback) here
        if exc_type:
            logger.warning(
                f"Exiting context due to exception: {exc_type.__name__}. Changes might not be saved."
                f"Exception: {exc_val} at {exc_tb}"
            )
        elif self.is_modified:
            logger.warning(f"Exiting context with unsaved modifications. Path: {self._file_path}")
            # Decide if auto-save on successful exit is desired
            # self.save() # Example: uncomment to auto-save

        self.close()

    def get_project(self) -> dict[str, Any] | None:
        """
        Retrieves basic project information from the IfcProject entity.

        Returns
        -------
        dict[str, Any] | None
            A dictionary containing project details like Name, Description,
            LongName, Phase, GUID, or None if IfcProject is not found.
        """
        try:
            # Use IfcEntityType
            project_entities = self.ifc_by_type(IfcEntityType.PROJECT)
            if project_entities:
                # Assuming get_project_info exists and works correctly
                # return get_project_info(project_entities[0])
                # Basic implementation if get_project_info is not available:
                proj = project_entities[0]
                return {
                    "id": proj.id(),
                    "guid": proj.GlobalId,
                    "name": getattr(proj, "Name", None),
                    "description": getattr(proj, "Description", None),
                    "long_name": getattr(proj, "LongName", None),
                    "phase": getattr(proj, "Phase", None),
                }

            else:
                logger.warning("IfcProject entity not found in the model.")
                return None
        except Exception as e:
            logger.error(f"Error retrieving project information: {e}")
            return None
