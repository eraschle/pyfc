class IfcModelContextError(Exception):
    """Exception raised for errors in the IfcProjectContext class."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class IfcAdapterError(Exception):
    """Custom exception for IFC adapter errors."""

    pass
