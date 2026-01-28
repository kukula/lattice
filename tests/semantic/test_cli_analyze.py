"""Integration tests for CLI analyze command."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from lattice.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_anthropic():
    """Create a mock anthropic client."""
    with patch("anthropic.Anthropic") as mock:
        yield mock


def _create_mock_response(text: str):
    """Create a mock API response with the given text."""
    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.text = text
    mock_response.content = [mock_text_block]
    return mock_response


class TestAnalyzeCommand:
    def test_analyze_valid_file_no_issues(self, runner, examples_dir, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = _create_mock_response(
            "NO_ISSUES_FOUND"
        )

        result = runner.invoke(
            main,
            ["analyze", str(examples_dir / "minimal_valid.yaml"), "--api-key", "test-key"],
        )

        assert result.exit_code == 0
        assert "Validation passed" in result.output

    def test_analyze_finds_semantic_issues(self, runner, examples_dir, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = _create_mock_response(
            """---
ISSUE: MISSING
CONTEXT: [User]
DESCRIPTION: No password validation rules defined
---"""
        )

        result = runner.invoke(
            main,
            ["analyze", str(examples_dir / "minimal_valid.yaml"), "--api-key", "test-key"],
        )

        # Exit code 0 because semantic issues are warnings
        assert result.exit_code == 0
        assert "SEMANTIC_MISSING" in result.output
        assert "password" in result.output

    def test_analyze_json_output(self, runner, examples_dir, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = _create_mock_response(
            """---
ISSUE: EDGE_CASE
CONTEXT: [Post]
DESCRIPTION: What if title is empty?
---"""
        )

        result = runner.invoke(
            main,
            [
                "analyze",
                str(examples_dir / "minimal_valid.yaml"),
                "--api-key",
                "test-key",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True
        assert data["warning_count"] == 1
        assert any(i["code"] == "SEMANTIC_EDGE_CASE" for i in data["issues"])

    def test_analyze_missing_api_key(self, runner, examples_dir, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = runner.invoke(
            main,
            ["analyze", str(examples_dir / "minimal_valid.yaml")],
        )

        assert result.exit_code == 2
        assert "API key" in result.output or "ANTHROPIC_API_KEY" in result.output

    def test_analyze_with_custom_model(self, runner, examples_dir, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = _create_mock_response(
            "NO_ISSUES_FOUND"
        )

        result = runner.invoke(
            main,
            [
                "analyze",
                str(examples_dir / "minimal_valid.yaml"),
                "--api-key",
                "test-key",
                "--model",
                "claude-3-opus-20240229",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_anthropic.return_value.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-opus-20240229"

    def test_analyze_with_structural_validation(self, runner, examples_dir, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = _create_mock_response(
            "NO_ISSUES_FOUND"
        )

        result = runner.invoke(
            main,
            [
                "analyze",
                str(examples_dir / "invalid" / "orphan_entity.yaml"),
                "--api-key",
                "test-key",
                "--include-structural",
            ],
        )

        # Should include structural warnings
        assert "ORPHAN_ENTITY" in result.output

    def test_analyze_without_structural_validation(self, runner, examples_dir, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = _create_mock_response(
            "NO_ISSUES_FOUND"
        )

        result = runner.invoke(
            main,
            [
                "analyze",
                str(examples_dir / "invalid" / "orphan_entity.yaml"),
                "--api-key",
                "test-key",
                "--no-include-structural",
            ],
        )

        # Should NOT include structural warnings
        assert "ORPHAN_ENTITY" not in result.output
        assert "Validation passed" in result.output

    def test_analyze_nonexistent_file(self, runner):
        result = runner.invoke(
            main, ["analyze", "/nonexistent/file.yaml", "--api-key", "test-key"]
        )

        assert result.exit_code == 2

    def test_analyze_order_lifecycle(self, runner, examples_dir, mock_anthropic):
        mock_anthropic.return_value.messages.create.return_value = _create_mock_response(
            """---
ISSUE: MISSING
CONTEXT: [Order.payment_pending]
DESCRIPTION: No transition handles payment timeout
---

---
ISSUE: EDGE_CASE
CONTEXT: [Order.cancelled]
DESCRIPTION: What if refund fails after order is cancelled?
---

---
ISSUE: AMBIGUOUS
CONTEXT: [Shipment]
DESCRIPTION: States defined but no clear link to Order state transitions
---"""
        )

        result = runner.invoke(
            main,
            ["analyze", str(examples_dir / "order_lifecycle.yaml"), "--api-key", "test-key"],
        )

        assert result.exit_code == 0
        assert "SEMANTIC_MISSING" in result.output
        assert "SEMANTIC_EDGE_CASE" in result.output
        assert "SEMANTIC_AMBIGUOUS" in result.output
        assert "3 warning(s)" in result.output
