"""Tests for semantic analyzer with mocked API."""

from unittest.mock import MagicMock, patch

import pytest

from lattice.semantic.analyzer import SemanticAnalyzer, analyze_model, DEFAULT_MODEL
from lattice.semantic.errors import APIKeyMissingError


class TestSemanticAnalyzerInit:
    def test_init_with_api_key_parameter(self):
        analyzer = SemanticAnalyzer(api_key="test-key")
        assert analyzer.api_key == "test-key"
        assert analyzer.model == DEFAULT_MODEL

    def test_init_with_env_var(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-test-key")
        analyzer = SemanticAnalyzer()
        assert analyzer.api_key == "env-test-key"

    def test_init_parameter_overrides_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        analyzer = SemanticAnalyzer(api_key="param-key")
        assert analyzer.api_key == "param-key"

    def test_init_without_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(APIKeyMissingError) as exc_info:
            SemanticAnalyzer()
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_init_with_custom_model(self):
        analyzer = SemanticAnalyzer(api_key="test-key", model="claude-3-opus-20240229")
        assert analyzer.model == "claude-3-opus-20240229"


class TestSemanticAnalyzerAnalyze:
    @pytest.fixture
    def mock_anthropic(self):
        """Create a mock anthropic client."""
        with patch("anthropic.Anthropic") as mock:
            yield mock

    @pytest.fixture
    def analyzer(self):
        """Create an analyzer with a test API key."""
        return SemanticAnalyzer(api_key="test-key")

    def test_analyze_returns_validation_result(self, mock_anthropic, analyzer, minimal_model):
        # Setup mock response
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "NO_ISSUES_FOUND"
        mock_response.content = [mock_text_block]
        mock_anthropic.return_value.messages.create.return_value = mock_response

        result = analyzer.analyze(minimal_model)

        assert result is not None
        assert len(result.issues) == 0

    def test_analyze_parses_issues(self, mock_anthropic, analyzer, minimal_model):
        # Setup mock response with issues
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = """---
ISSUE: MISSING
CONTEXT: [User]
DESCRIPTION: No password field defined
---"""
        mock_response.content = [mock_text_block]
        mock_anthropic.return_value.messages.create.return_value = mock_response

        result = analyzer.analyze(minimal_model)

        assert len(result.issues) == 1
        assert result.issues[0].code == "SEMANTIC_MISSING"
        assert result.issues[0].entity == "User"

    def test_analyze_calls_api_with_correct_params(self, mock_anthropic, analyzer, minimal_model):
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "NO_ISSUES_FOUND"
        mock_response.content = [mock_text_block]
        mock_client = mock_anthropic.return_value
        mock_client.messages.create.return_value = mock_response

        analyzer.analyze(minimal_model)

        # Verify the API was called
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == DEFAULT_MODEL
        assert call_kwargs["max_tokens"] == 4096
        assert "system" in call_kwargs
        assert "messages" in call_kwargs


class TestAnalyzeModelFunction:
    @pytest.fixture
    def mock_anthropic(self):
        """Create a mock anthropic client."""
        with patch("anthropic.Anthropic") as mock:
            yield mock

    def test_analyze_model_convenience_function(self, mock_anthropic, minimal_model):
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "NO_ISSUES_FOUND"
        mock_response.content = [mock_text_block]
        mock_anthropic.return_value.messages.create.return_value = mock_response

        result = analyze_model(minimal_model, api_key="test-key")

        assert result is not None
        assert len(result.issues) == 0

    def test_analyze_model_with_custom_model(self, mock_anthropic, minimal_model):
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "NO_ISSUES_FOUND"
        mock_response.content = [mock_text_block]
        mock_client = mock_anthropic.return_value
        mock_client.messages.create.return_value = mock_response

        analyze_model(minimal_model, api_key="test-key", model_name="claude-3-opus-20240229")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-opus-20240229"
