import logging

from pyfc.ios.context import IosModelContext


def debug_context_state(
    context: IosModelContext | None, label: str = "Context"
) -> None:
    """Print debug information about the context state."""
    if not context:
        logging.debug(f"{label}: Context is None")
        return

    if not context.ifc_model:
        logging.debug(f"{label}: IFC model is None")
        return

    try:
        entity_count = len(context.ifc_model.by_type("IfcProduct"))
        project_info = context.get_project()
        file_path = context.file_path

        logging.debug(f"{label}: Model loaded with {entity_count} entities")
        if project_info:
            logging.debug(f"{label}: Project: {project_info.get('name', 'Unknown')}")
        if file_path:
            logging.debug(f"{label}: File path: {file_path}")
    except Exception as e:
        logging.debug(f"{label}: Error getting context state: {e}")


# Optional: Define __all__ if you want to control imports with 'from tests.ios import *'
# __all__ = ["debug_context_state"]
