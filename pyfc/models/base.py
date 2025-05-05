import abc
import logging
from typing import Any

from .attribute import IfcAttributeDescriptor

logger = logging.getLogger(__name__)


def get_ifc_model_id(entity: Any) -> int:
    """
    Returns the IFC ID of the given entity.

    Parameters
    ----------
    entity : Any
        The entity to get the IFC ID from.

    Returns
    -------
    int
        The IFC ID of the entity.
    """
    if isinstance(entity, dict):
        return entity.get("id", -1)
    if hasattr(entity, "id"):
        return entity.id()
    raise ValueError("Entity does not have an id attribute or is not a dictionary.")


class ABaseModel(abc.ABC):
    name: str = IfcAttributeDescriptor(ifc_attr="Name", read_only=False)  # pyright: ignore[reportAssignmentType]

    def __init__(self, entity: Any) -> None:
        super().__init__()
        self._entity_id: int = get_ifc_model_id(entity)

    @property
    def ifc_id(self) -> int:
        return self._entity_id

    def __str__(self) -> str:
        return f"{self.__class__.__name__} (id={self._entity_id}) Name: {self.name}"

    def __repr__(self) -> str:
        return self.__str__()
