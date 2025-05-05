import logging
from typing import TYPE_CHECKING, Any

from pyfc.models.value import IfcValue

if TYPE_CHECKING:
    from .base import ABaseModel
    from .objects import IfcObjectBase


logger = logging.getLogger(__name__)


class IfcAttributeDescriptor:
    def __init__(self, ifc_attr: str, read_only: bool):
        self.ifc_attr = ifc_attr
        self._py_attr = None
        self.read_only = read_only

    def __set_name__(self, _: type["ABaseModel"], name: str):
        self._py_attr = name

    def __get__(self, instance: "ABaseModel | None", owner: type["ABaseModel"]) -> Any | None:
        if instance is None:
            # Return the descriptor itself when accessed on the class
            return self
        adapter = getattr(instance, "_adapter", None)
        if adapter is None:
            logger.error(f"Descriptor owner {owner.__name__} needs an attribute '_adapter'")
            return None

        try:
            return adapter.get_attribute(instance.ifc_id, self.ifc_attr)
        except Exception as exp:
            logger.debug(f"Descriptor failed to get '{self.ifc_attr}' for {instance}: {exp}")
            return None

    def __set__(self, instance: "ABaseModel", value: Any):
        if self.read_only:
            logger.error(f"Attribute '{self.ifc_attr}' on {type(instance).__name__} is read-only.")
            raise AttributeError(
                f"Attribute '{self.ifc_attr}' on {type(instance).__name__} is read-only."
            )
        # Allow setting None to potentially clear an attribute if the adapter supports it
        # if value is None:
        #     logger.warning(
        #         f"Descriptor owner {type(instance).__name__} cannot set None value for '{self.ifc_attr}'"
        #     )
        #     return
        adapter = getattr(instance, "_adapter", None)
        if adapter is None:
            logger.error(
                f"Descriptor owner {type(instance).__name__} needs an attribute '_adapter' to set '{self.ifc_attr}'",
            )
            raise AttributeError(
                f"Adapter not found on {type(instance).__name__} to set attribute."
            )

        try:
            result = adapter.set_attribute(instance.ifc_id, self.ifc_attr, value)
            if result:
                logger.debug(f"Descriptor set '{self.ifc_attr}' to '{value}' for {instance}")
            else:
                # This might happen if the value didn't actually change or adapter prevented it
                logger.warning(
                    f"Descriptor failed to set '{self.ifc_attr}' for {instance} via adapter (returned False)."
                )
        except Exception as e:
            logger.error(
                f"Descriptor failed to set '{self.ifc_attr}' for {instance}: {e}",
            )
            # Re-raise as AttributeError or a custom exception if needed
            raise AttributeError(f"Failed to set attribute '{self.ifc_attr}': {e}") from e


class IfcSingleValuePropertyDescriptor:
    """
    Descriptor to get/set an IfcPropertySingleValue within a specific PSet via the adapter.
    Assumes the owner instance is a IfcObjectBase (or subtype).
    """

    def __init__(self, pset_name: str, prop_name: str, read_only: bool = False):
        self._python_attr_name = None
        self.pset_name = pset_name
        self.prop_name = prop_name
        self.read_only = read_only

    def __set_name__(self, _: type["IfcObjectBase"], name: str):
        self._python_attr_name = name

    def __get__(self, instance: "IfcObjectBase | None", owner: type["IfcObjectBase"]) -> Any | None:
        if instance is None:
            # Return the descriptor itself when accessed on the class
            return self
        # Ensure instance is of the correct type
        # This check might be too strict if used on subclasses not directly inheriting IfcObjectBase
        # Consider removing if causing issues with inheritance.
        # from .objects import IfcObjectBase # Import locally for isinstance check if needed
        # if not isinstance(instance, IfcObjectBase):
        #     logger.error(f"Descriptor owner must be an instance of IfcObjectBase, not {type(instance).__name__}")
        #     raise TypeError(f"Descriptor owner must be an instance of IfcObjectBase")

        # Check for adapter existence
        adapter = getattr(instance, "_adapter", None)
        if adapter is None:
            logger.error(f"Descriptor owner {owner.__name__} needs an attribute '_adapter'")
            return None

        try:
            # get_property returns an IfcProperty model or None
            prop = adapter.get_property(instance.ifc_id, self.pset_name, self.prop_name)
            if prop:
                # prop.value returns an IfcValue object or None
                ifc_value_obj: IfcValue | None = prop.value
                # Return the raw value from the IfcValue object
                return ifc_value_obj.value if ifc_value_obj else None
            else:
                # Property or PSet not found
                return None
        except Exception as e:
            prop_full_name = f"{self.pset_name}.{self.prop_name}"
            logger.debug(
                f"Descriptor failed to get property '{prop_full_name}' from '{instance}' via adapter: {e}"
            )
            return None

    def __set__(self, instance: "IfcObjectBase", value: Any):
        if self.read_only:
            prop_full_name = f"{self.pset_name}.{self.prop_name}"
            logger.error(f"Property '{prop_full_name}' on {type(instance).__name__} is read-only.")
            raise AttributeError(
                f"Property '{prop_full_name}' on {type(instance).__name__} is read-only."
            )

        # Check for adapter existence
        adapter = getattr(instance, "_adapter", None)
        if adapter is None:
            logger.error(
                f"Descriptor owner {type(instance).__name__} needs an attribute '_adapter'"
            )
            raise AttributeError(f"Adapter not found on {type(instance).__name__} to set property.")

        try:
            # Get the IfcProperty model first
            prop = adapter.get_property(instance.ifc_id, self.pset_name, self.prop_name)

            if prop:
                # Assign the raw value to the property model's value setter
                # The setter within IfcProperty handles creating/updating the IfcValue
                # and calling the adapter's set_value method.
                prop.value = value
                logger.debug(
                    f"Descriptor requested set property '{self.pset_name}.{self.prop_name}' to '{value}' for {instance}",
                )
            else:
                # Property or PSet doesn't exist. Should we create it?
                # Current behavior: Log a warning.
                # Alternative: Could try to create PSet/Property if value is not None.
                logger.warning(
                    f"Descriptor could not find property '{self.pset_name}.{self.prop_name}' on {instance} to set value. "
                    f"PSet/Property might need to be created first using add_pset/add_property."
                )
                # Optionally raise an error here if setting non-existent properties is disallowed.
                # raise AttributeError(f"Property '{self.pset_name}.{self.prop_name}' not found on {instance}.")

        except Exception as e:
            prop_full_name = f"{self.pset_name}.{self.prop_name}"
            logger.error(
                f"Descriptor failed to set property '{prop_full_name}' for {instance}: {e}",
            )
            # Re-raise as AttributeError or IfcAdapterError
            raise AttributeError(f"Failed to set property '{prop_full_name}': {e}") from e
