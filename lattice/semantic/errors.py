"""Exception classes for semantic validation."""


class SemanticAnalysisError(Exception):
    """Base exception for semantic analysis errors."""

    pass


class APIKeyMissingError(SemanticAnalysisError):
    """Raised when no API key is configured."""

    def __init__(self, message: str = "No Anthropic API key configured"):
        super().__init__(message)


class APIError(SemanticAnalysisError):
    """Raised when the API call fails."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class ResponseParseError(SemanticAnalysisError):
    """Raised when the LLM response cannot be parsed."""

    def __init__(self, message: str, raw_response: str | None = None):
        self.raw_response = raw_response
        super().__init__(message)
