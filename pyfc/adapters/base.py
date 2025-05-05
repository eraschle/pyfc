from typing import Any, Protocol

from pyfc.models import ABaseModel


class IBaseAdapter[TModel: "ABaseModel"](Protocol):
    def create_model(self, entity: Any) -> TModel:
        """
        Creates a model instance from the given entity.

        Parameters
        ----------
        entity : Any
            The entity to create the model from.

        Returns
        -------
        TModel
            The created model instance.
        """
        ...

    def get_by_id(self, ifc_id: int) -> TModel | None:
        """
        Returns the object with the given IFC ID.
        If the object is not found, None is returned.

        Parameters
        ----------
        ifc_id : int
            The IFC ID of the object to retrieve.

        Returns
        -------
        TModel | None
            The object if found, otherwise None.
        """
        ...

    def get_by_guid(self, guid: str) -> TModel | None:
        """
        Returns the object with the given GUID.

        If the object is not found, None is returned.

        Parameters
        ----------
        guid : str
            The GUID of the object to retrieve.
        Returns
        -------
        TModel | None
            The object if found, otherwise None.
        """
        ...

    def get_attribute(self, entity_id: int, name: str) -> Any | None:
        """
        Returns the value of the attribute with the given name of the entity with the given ID.

        Parameters
        ----------
        entity_id : int
            The ID of the entity to set the attribute on.
        name : str
            The name of the attribute to retrieve.

        Returns
        -------
        Any | None
            The value of the attribute, or None if not found.
        """
        ...

    def set_attribute(self, entity_id: int, name: str, value: Any) -> bool:
        """
        Sets the value of the attribute with the given name on the entity with the given ID.

        If the attribute does not exist or the value is None, it does not set the attribute.

        Parameters
        ----------
        entity_id : int
            The ID of the entity to set the attribute on.
        name : str
            The name of the attribute to set.
        value : Any
            The value to set for the attribute.

        Returns
        -------
        bool
            True if the attribute was set successfully, False otherwise.
        """
        ...
