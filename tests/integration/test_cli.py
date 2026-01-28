"""Integration tests for CLI."""

import json

import pytest
from click.testing import CliRunner

from lattice.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestValidateCommand:
    def test_validate_valid_file(self, runner, examples_dir):
        result = runner.invoke(
            main, ["validate", str(examples_dir / "minimal_valid.yaml")]
        )

        assert result.exit_code == 0
        assert "Validation passed" in result.output

    def test_validate_with_errors(self, runner, examples_dir):
        result = runner.invoke(
            main, ["validate", str(examples_dir / "invalid" / "broken_reference.yaml")]
        )

        assert result.exit_code == 1
        assert "UNDEFINED" in result.output

    def test_validate_with_warnings(self, runner, examples_dir):
        result = runner.invoke(
            main, ["validate", str(examples_dir / "invalid" / "orphan_entity.yaml")]
        )

        # Warnings don't cause failure by default
        assert result.exit_code == 0
        assert "ORPHAN_ENTITY" in result.output

    def test_validate_strict_mode(self, runner, examples_dir):
        result = runner.invoke(
            main,
            [
                "validate",
                str(examples_dir / "invalid" / "orphan_entity.yaml"),
                "--strict",
            ],
        )

        # In strict mode, warnings cause failure
        assert result.exit_code == 1

    def test_validate_json_output(self, runner, examples_dir):
        result = runner.invoke(
            main,
            [
                "validate",
                str(examples_dir / "minimal_valid.yaml"),
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True
        assert "issues" in data

    def test_validate_nonexistent_file(self, runner):
        result = runner.invoke(main, ["validate", "/nonexistent/file.yaml"])

        assert result.exit_code == 2

    def test_validate_order_lifecycle(self, runner, examples_dir):
        result = runner.invoke(
            main, ["validate", str(examples_dir / "order_lifecycle.yaml")]
        )

        # Should pass (may have some warnings but no errors)
        assert result.exit_code == 0
