"""Tests for test_generator.generator."""

import pytest

from lattice.graph.builder import build_graph
from lattice.schema.loader import parse_model_from_string
from lattice.test_generator import generate_tests, generate_tests_from_file
from lattice.test_generator.models import TestType


@pytest.fixture
def full_model_yaml():
    """A comprehensive model with states, transitions, and invariants."""
    return """
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
        trigger: submit
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
      - description: "Total must be positive"
        formal: "total > 0"

  User:
    attributes:
      - name: email
        type: string

system_invariants:
  - description: "No overselling"
"""


class TestGenerateTests:
    """Tests for generate_tests function."""

    def test_generates_files_for_stateful_entities(self, full_model_yaml):
        """Should generate test files for entities with state machines."""
        model = parse_model_from_string(full_model_yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)

        # Should have Order tests and system invariant tests
        filenames = [f.filename for f in result.files]
        assert "test_order.py" in filenames

    def test_skips_stateless_entities_without_invariants(self, full_model_yaml):
        """Should not generate file for User (no states, no invariants)."""
        model = parse_model_from_string(full_model_yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)

        filenames = [f.filename for f in result.files]
        assert "test_user.py" not in filenames

    def test_generates_system_invariant_file(self, full_model_yaml):
        """Should generate system invariants file."""
        model = parse_model_from_string(full_model_yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)

        filenames = [f.filename for f in result.files]
        assert "test_system_invariants.py" in filenames

    def test_includes_all_test_types(self, full_model_yaml):
        """Should include positive, negative, happy path, and invariant tests."""
        model = parse_model_from_string(full_model_yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)

        # Find Order file
        order_file = next(f for f in result.files if f.entity == "Order")

        test_types = {tc.test_type for tc in order_file.test_cases}

        assert TestType.POSITIVE_TRANSITION in test_types
        assert TestType.HAPPY_PATH in test_types
        assert TestType.ENTITY_INVARIANT in test_types

    def test_total_tests_counted(self, full_model_yaml):
        """Total tests should be properly counted."""
        model = parse_model_from_string(full_model_yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)

        assert result.total_tests > 0
        assert result.total_tests == sum(
            len(f.test_cases) for f in result.files
        )

    def test_empty_model(self):
        """Empty model should produce empty result."""
        yaml = """
entities: {}
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)

        assert result.files == []
        assert result.total_tests == 0


class TestGenerateTestsFromFile:
    """Tests for generate_tests_from_file function."""

    def test_loads_and_generates(self, tmp_path):
        """Should load YAML file and generate tests."""
        model_file = tmp_path / "model.yaml"
        model_file.write_text("""
entities:
  Task:
    states:
      - name: pending
        initial: true
      - name: done
        terminal: true
    transitions:
      - from: pending
        to: done
        trigger: complete
""")

        result = generate_tests_from_file(str(model_file))

        assert len(result.files) == 1
        assert result.files[0].entity == "Task"


class TestGenerateTestsEdgeCases:
    """Tests for edge cases in test generation."""

    def test_entity_with_only_invariants(self):
        """Entity with only invariants (no states) should still get tests."""
        yaml = """
entities:
  Product:
    attributes:
      - name: price
        type: decimal
    invariants:
      - description: "Price must be positive"
        formal: "price > 0"
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)

        assert len(result.files) == 1
        assert result.files[0].entity == "Product"
        assert all(
            tc.test_type == TestType.ENTITY_INVARIANT
            for tc in result.files[0].test_cases
        )

    def test_multiple_entities_with_states(self):
        """Should generate separate files for multiple stateful entities."""
        yaml = """
entities:
  Order:
    states:
      - name: draft
        initial: true
      - name: done
        terminal: true
    transitions:
      - from: draft
        to: done
  Shipment:
    states:
      - name: pending
        initial: true
      - name: delivered
        terminal: true
    transitions:
      - from: pending
        to: delivered
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)

        filenames = sorted([f.filename for f in result.files])
        assert filenames == ["test_order.py", "test_shipment.py"]

    def test_transition_from_multiple_states(self):
        """Transitions from multiple states should generate multiple tests."""
        yaml = """
entities:
  Order:
    states:
      - name: a
        initial: true
      - name: b
      - name: cancelled
        terminal: true
    transitions:
      - from: a
        to: b
      - from: [a, b]
        to: cancelled
        trigger: cancel
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = generate_tests(model, graph)
        order_file = result.files[0]

        # Should have: a->b, a->cancelled, b->cancelled
        positive_tests = [
            tc for tc in order_file.test_cases
            if tc.test_type == TestType.POSITIVE_TRANSITION
        ]
        assert len(positive_tests) == 3
