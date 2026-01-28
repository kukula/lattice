"""Integration tests for the generate-tests CLI command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from lattice.cli import main


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_model(tmp_path):
    """Create a sample model file for testing."""
    model_file = tmp_path / "order.yaml"
    model_file.write_text("""
entities:
  Order:
    attributes:
      - name: total
        type: decimal
    states:
      - name: draft
        initial: true
      - name: submitted
      - name: delivered
        terminal: true
      - name: cancelled
        terminal: true
    transitions:
      - from: draft
        to: submitted
        trigger: customer.submit
        requires:
          - line_items.count > 0
        effects:
          - reserve_inventory
      - from: submitted
        to: delivered
        trigger: deliver
      - from: [draft, submitted]
        to: cancelled
        trigger: cancel
    invariants:
      - description: "Order total must be positive"
        formal: "total > 0"

system_invariants:
  - description: "No overselling allowed"
""")
    return model_file


class TestGenerateTestsCommand:
    """Tests for the generate-tests command."""

    def test_text_output_default(self, runner, sample_model):
        """Default output should be text to stdout."""
        result = runner.invoke(main, ["generate-tests", str(sample_model)])

        assert result.exit_code == 0
        assert "Generated tests for Order entity" in result.output
        assert "import pytest" in result.output
        assert "class TestPositiveTransitions:" in result.output

    def test_text_output_explicit(self, runner, sample_model):
        """Explicit text format should work."""
        result = runner.invoke(
            main, ["generate-tests", str(sample_model), "--format", "text"]
        )

        assert result.exit_code == 0
        assert "import pytest" in result.output

    def test_files_output(self, runner, sample_model, tmp_path):
        """Files format should write to disk."""
        output_dir = tmp_path / "generated"

        result = runner.invoke(
            main,
            [
                "generate-tests",
                str(sample_model),
                "--format",
                "files",
                "--output-dir",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0
        assert output_dir.exists()
        assert (output_dir / "test_order.py").exists()
        assert (output_dir / "test_system_invariants.py").exists()

    def test_generated_file_is_valid_python(self, runner, sample_model, tmp_path):
        """Generated files should be valid Python."""
        output_dir = tmp_path / "generated"

        result = runner.invoke(
            main,
            [
                "generate-tests",
                str(sample_model),
                "--format",
                "files",
                "--output-dir",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0

        # Verify each generated file is valid Python
        for py_file in output_dir.glob("*.py"):
            content = py_file.read_text()
            compile(content, str(py_file), "exec")

    def test_includes_transition_tests(self, runner, sample_model):
        """Should include tests for state transitions."""
        result = runner.invoke(main, ["generate-tests", str(sample_model)])

        assert result.exit_code == 0
        assert "test_order_draft_to_submitted" in result.output
        assert "test_order_submitted_to_delivered" in result.output

    def test_includes_guards_and_effects(self, runner, sample_model):
        """Should include guards and effects in output."""
        result = runner.invoke(main, ["generate-tests", str(sample_model)])

        assert result.exit_code == 0
        assert "line_items.count > 0" in result.output
        assert "reserve_inventory" in result.output

    def test_includes_happy_path_tests(self, runner, sample_model):
        """Should include happy path tests."""
        result = runner.invoke(main, ["generate-tests", str(sample_model)])

        assert result.exit_code == 0
        assert "class TestHappyPaths:" in result.output
        assert "test_order_lifecycle_to" in result.output

    def test_includes_invariant_tests(self, runner, sample_model):
        """Should include invariant tests."""
        result = runner.invoke(main, ["generate-tests", str(sample_model)])

        assert result.exit_code == 0
        assert "class TestInvariants:" in result.output
        assert "total must be positive" in result.output

    def test_includes_system_invariant_tests(self, runner, sample_model):
        """Should include system invariant tests."""
        result = runner.invoke(main, ["generate-tests", str(sample_model)])

        assert result.exit_code == 0
        assert "test_system_invariants.py" in result.output
        assert "No overselling" in result.output

    def test_reports_test_count(self, runner, sample_model):
        """Should report total test count."""
        result = runner.invoke(main, ["generate-tests", str(sample_model)])

        assert result.exit_code == 0
        assert "Generated" in result.output
        assert "tests" in result.output

    def test_nonexistent_file(self, runner):
        """Should fail gracefully for nonexistent file."""
        result = runner.invoke(main, ["generate-tests", "nonexistent.yaml"])

        assert result.exit_code == 2

    def test_invalid_yaml(self, runner, tmp_path):
        """Should fail gracefully for invalid YAML."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("entities: [not: valid: yaml")

        result = runner.invoke(main, ["generate-tests", str(bad_file)])

        assert result.exit_code == 2

    def test_empty_model(self, runner, tmp_path):
        """Should handle model with no tests gracefully."""
        empty_model = tmp_path / "empty.yaml"
        empty_model.write_text("entities: {}")

        result = runner.invoke(main, ["generate-tests", str(empty_model)])

        assert result.exit_code == 0
        assert "No tests to generate" in result.output


class TestGenerateTestsWithRealFile:
    """Integration tests using the actual example file."""

    def test_order_lifecycle_example(self, runner, examples_dir):
        """Test with the actual order_lifecycle.yaml example."""
        model_path = examples_dir / "order_lifecycle.yaml"
        if not model_path.exists():
            pytest.skip("order_lifecycle.yaml not found")

        result = runner.invoke(main, ["generate-tests", str(model_path)])

        assert result.exit_code == 0
        assert "test_order.py" in result.output
        assert "test_shipment.py" in result.output
        assert "Generated" in result.output


@pytest.fixture
def examples_dir():
    """Return path to examples directory."""
    return Path(__file__).parent.parent.parent / "examples"
