from pathlib import Path
from typing import Protocol


class IModelContext(Protocol):
    @classmethod
    def open(cls, filepath: str | Path) -> "IModelContext":
        """
        Open an IFC file.

        Parameters
        ----------
        filepath : str | Path
            The path to the IFC file to open.

        Returns
        -------
        IModelContext
            The IFC model context.

        Raises
        ------
        IfcModelContextError
            If the file cannot be opened.
        """
        ...

    @classmethod
    def create(cls, schema: str = "IFC4") -> "IModelContext":
        """
        Create a new IFC file.

        Parameters
        ----------
        schema : str
            The IFC schema to use (default: "IFC4").

        Returns
        -------
        IfcModelContext
            The IFC model context.

        Raises
        ------
        IfcModelContextError
            If the file cannot be created.
        """
        ...

    def save(self, filepath: str | Path | None = None) -> None:
        """
        Save the IFC file.

        Parameters
        ----------
        filepath : Optional[str | Path]
            The path to save the IFC file to. If None, the original filepath is used.

        Raises
        ------
        IfcModelContextError
            If the file cannot be saved.
        """

    def __enter__(self) -> "IModelContext":
        """Enter the context."""
        ...

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the context."""
        ...
