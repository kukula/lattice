"""Semantic analyzer using Claude API."""

import os
from typing import TYPE_CHECKING

from ..schema.models import LatticeModel
from ..validators.base import ValidationResult
from .errors import APIError, APIKeyMissingError
from .parser import parse_semantic_response
from .prompts import SYSTEM_PROMPT, build_analysis_prompt

if TYPE_CHECKING:
    from anthropic import Anthropic

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class SemanticAnalyzer:
    """Semantic analyzer using Claude API for LLM-based validation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ):
        """Initialize the semantic analyzer.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use for analysis.

        Raises:
            APIKeyMissingError: If no API key is configured.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise APIKeyMissingError(
                "No Anthropic API key configured. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )
        self.model = model
        self._client: "Anthropic | None" = None

    @property
    def client(self) -> "Anthropic":
        """Lazy-load the Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError:
                raise APIKeyMissingError(
                    "The anthropic package is not installed. "
                    "Install it with: pip install lattice[semantic]"
                )
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def analyze(self, model: LatticeModel) -> ValidationResult:
        """Analyze a model for semantic issues.

        Args:
            model: The LatticeModel to analyze.

        Returns:
            ValidationResult containing semantic issues as warnings.

        Raises:
            APIError: If the API call fails.
        """
        prompt = build_analysis_prompt(model)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            return parse_semantic_response(response_text)

        except Exception as e:
            # Check for specific anthropic errors
            error_type = type(e).__name__
            if "APIError" in error_type or "APIStatusError" in error_type:
                status_code = getattr(e, "status_code", None)
                raise APIError(str(e), status_code=status_code) from e
            elif "AuthenticationError" in error_type:
                raise APIKeyMissingError(
                    "Invalid Anthropic API key. Please check your API key."
                ) from e
            else:
                raise APIError(f"Unexpected error during analysis: {e}") from e


def analyze_model(
    model: LatticeModel,
    api_key: str | None = None,
    model_name: str = DEFAULT_MODEL,
) -> ValidationResult:
    """Convenience function to analyze a model.

    Args:
        model: The LatticeModel to analyze.
        api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        model_name: Claude model to use for analysis.

    Returns:
        ValidationResult containing semantic issues as warnings.
    """
    analyzer = SemanticAnalyzer(api_key=api_key, model=model_name)
    return analyzer.analyze(model)
