"""Schema-related exceptions."""


class SchemaLoadError(Exception):
    """Raised when a YAML file cannot be loaded."""

    def __init__(self, message: str, path: str | None = None):
        self.path = path
        super().__init__(message)


class SchemaValidationError(Exception):
    """Raised when a model fails schema validation."""

    def __init__(self, message: str, errors: list[dict] | None = None):
        self.errors = errors or []
        super().__init__(message)
