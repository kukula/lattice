"""Tests for test_generator.invariants."""

import pytest

from lattice.schema.loader import parse_model_from_string
from lattice.test_generator.invariants import (
    generate_entity_invariant_tests,
    generate_system_invariant_tests,
)
from lattice.test_generator.models import TestType


@pytest.fixture
def entity_with_invariants_yaml():
    """Entity with various invariants."""
    return """
entities:
  Order:
    attributes:
      - name: total
        type: decimal
    invariants:
      - description: "Order total equals sum of line items"
        formal: "total == line_items.sum(li => li.quantity * li.unit_price)"
      - description: "Cannot ship without payment"
        formal: "state == shipped => payment.recorded"
      - description: "Delivered orders cannot be cancelled"
"""


@pytest.fixture
def model_with_system_invariants_yaml():
    """Model with system-level invariants."""
    return """
entities:
  Order:
    attributes:
      - name: total
        type: decimal
  Product:
    attributes:
      - name: inventory_count
        type: integer

system_invariants:
  - description: "Total reserved inventory equals sum of reserved across orders"
  - description: "No overselling allowed"
    formal: "available_inventory >= 0"
"""


class TestGenerateEntityInvariantTests:
    """Tests for generate_entity_invariant_tests."""

    def test_generates_test_per_invariant(self, entity_with_invariants_yaml):
        """Should generate one test per entity invariant."""
        model = parse_model_from_string(entity_with_invariants_yaml)
        entity = model.entities["Order"]

        tests = generate_entity_invariant_tests(entity)

        assert len(tests) == 3
        assert all(t.test_type == TestType.ENTITY_INVARIANT for t in tests)

    def test_captures_description(self, entity_with_invariants_yaml):
        """Test should capture invariant description."""
        model = parse_model_from_string(entity_with_invariants_yaml)
        entity = model.entities["Order"]

        tests = generate_entity_invariant_tests(entity)

        descriptions = [t.description for t in tests]
        assert any("Order total equals" in d for d in descriptions)
        assert any("Cannot ship without payment" in d for d in descriptions)

    def test_captures_formal_expression(self, entity_with_invariants_yaml):
        """Test should capture formal expression when present."""
        model = parse_model_from_string(entity_with_invariants_yaml)
        entity = model.entities["Order"]

        tests = generate_entity_invariant_tests(entity)

        # Find test with formal expression
        total_test = next(t for t in tests if "total equals" in t.description)
        assert total_test.formal is not None
        assert "sum" in total_test.formal

    def test_handles_invariant_without_formal(self, entity_with_invariants_yaml):
        """Test should handle invariants without formal expression."""
        model = parse_model_from_string(entity_with_invariants_yaml)
        entity = model.entities["Order"]

        tests = generate_entity_invariant_tests(entity)

        # Find test without formal expression
        cancelled_test = next(t for t in tests if "cancelled" in t.description)
        assert cancelled_test.formal is None

    def test_unique_test_names(self, entity_with_invariants_yaml):
        """Test names should be unique."""
        model = parse_model_from_string(entity_with_invariants_yaml)
        entity = model.entities["Order"]

        tests = generate_entity_invariant_tests(entity)
        names = [t.name for t in tests]

        assert len(names) == len(set(names))

    def test_entity_without_invariants(self):
        """Entity without invariants should return empty list."""
        yaml = """
entities:
  User:
    attributes:
      - name: email
        type: string
"""
        model = parse_model_from_string(yaml)
        entity = model.entities["User"]

        tests = generate_entity_invariant_tests(entity)

        assert tests == []


class TestGenerateSystemInvariantTests:
    """Tests for generate_system_invariant_tests."""

    def test_generates_test_per_system_invariant(
        self, model_with_system_invariants_yaml
    ):
        """Should generate one test per system invariant."""
        model = parse_model_from_string(model_with_system_invariants_yaml)

        tests = generate_system_invariant_tests(model)

        assert len(tests) == 2
        assert all(t.test_type == TestType.SYSTEM_INVARIANT for t in tests)

    def test_entity_is_system(self, model_with_system_invariants_yaml):
        """System invariant tests should have entity='system'."""
        model = parse_model_from_string(model_with_system_invariants_yaml)

        tests = generate_system_invariant_tests(model)

        assert all(t.entity == "system" for t in tests)

    def test_captures_formal_expression(self, model_with_system_invariants_yaml):
        """Test should capture formal expression when present."""
        model = parse_model_from_string(model_with_system_invariants_yaml)

        tests = generate_system_invariant_tests(model)

        oversell_test = next(t for t in tests if "overselling" in t.description)
        assert oversell_test.formal is not None

    def test_model_without_system_invariants(self):
        """Model without system invariants should return empty list."""
        yaml = """
entities:
  User:
    attributes:
      - name: email
        type: string
"""
        model = parse_model_from_string(yaml)

        tests = generate_system_invariant_tests(model)

        assert tests == []
