import abc
import logging
from typing import TYPE_CHECKING, Any

from pyfc.adapters import IBaseAdapter
from pyfc.errors import IfcAdapterError
from pyfc.models import ABaseModel

if TYPE_CHECKING:
    from pyfc.ios.context import IosModelContext

logger = logging.getLogger(__name__)


class IosBaseAdapter[T: ABaseModel](IBaseAdapter[T]):
    """Base adapter implementation using ifcopenshell."""

    def __init__(self, context: "IosModelContext"):
        self.context = context

    @abc.abstractmethod
    def create_model(self, entity: Any) -> T:
        """Create a model instance from an entity. To be implemented by subclasses."""
        pass

    def get_by_id(self, ifc_id: int) -> T:
        """Get an entity by its ID."""
        try:
            entity = self.context.ifc_by_id(ifc_id)
            if not entity:
                raise IfcAdapterError(f"Entity with ID {ifc_id} not found")
            return self.create_model(entity)
        except Exception as e:
            logger.error(f"Error getting entity by ID {ifc_id}: {e}")
            raise IfcAdapterError(f"Error getting entity by ID {ifc_id}: {e}")

    def get_by_guid(self, guid: str) -> T:
        """Get an entity by its GUID."""
        try:
            entity = self.context.ifc_by_guid(guid)
            return self.create_model(entity)
        except Exception as e:
            logger.error(f"Error getting entity by GUID {guid}: {e}")
            raise IfcAdapterError(f"Error getting entity by GUID {guid}: {e}")

    def get_attribute(self, entity_id: int, name: str) -> Any | None:
        """Get an attribute value from an entity."""
        try:
            entity = self.context.ifc_by_id(entity_id)
            if not entity:
                raise IfcAdapterError(f"Entity with ID {entity_id} not found")

            if not hasattr(entity, name):
                return None
            return getattr(entity, name)
        except Exception as e:
            logger.error(f"Error getting attribute {name} from entity {entity_id}: {e}")
            raise IfcAdapterError(f"Error getting attribute {name} from entity {entity_id}: {e}")

    def set_attribute(self, entity_id: int, name: str, value: Any) -> bool:
        """Set an attribute value on an entity."""
        entity = self.context.ifc_by_id(entity_id)
        if not entity:
            raise IfcAdapterError(f"Entity with ID {entity_id} not found")
        try:
            if hasattr(entity, name):
                setattr(entity, name, value)
                return self.context.mark_modified()
            return False
        except Exception as e:
            logger.error(f"Error setting attribute {name} on entity {entity_id}: {e}")
            return False
