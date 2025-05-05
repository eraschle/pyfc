import pytest

# --- Importiere die Interfaces ---
from pyfc.adapters.objects import IObjectBaseAdapter

# --- Importiere die Modelle (für Typ-Hinweise) ---
# Importiere das spezifische Modell, das von der Basisimplementierung erwartet wird.
# Wenn andere Implementierungen andere Basismodelle verwenden, muss dies angepasst
# oder generischer gestaltet werden (z.B. mit TypeVar).
from pyfc.models.objects import IfcObjectBase


# --- Fixture für IObjectBaseAdapter ---
@pytest.fixture
def base_adapter(object_adapter) -> IObjectBaseAdapter[IfcObjectBase]:
    """
    Provides an IObjectBaseAdapter instance (using the object_adapter fixture)
    for the current implementation. Tests should only use methods defined
    in the IObjectBaseAdapter protocol.

    Relies on the 'object_adapter' fixture provided by the parent conftest.py,
    which is already parametrized based on the implementation context.
    """
    # Der object_adapter wird bereits parametrisiert von tests/conftest.py geliefert.
    # Wir prüfen nur, ob er das benötigte Interface implementiert.
    if not isinstance(object_adapter, IObjectBaseAdapter):
        raise TypeError(
            f"Fixture 'object_adapter' (type: {type(object_adapter)}) does not implement IObjectBaseAdapter"
        )

    # TODO: Add code here if necessary to ensure the adapter is initialized
    #       or contains known test data. Currently, it's assumed the IFC file
    #       loaded via the context contains the necessary entities.
    return object_adapter
