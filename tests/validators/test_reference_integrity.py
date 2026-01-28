"""Tests for reference integrity validator."""

import pytest

from lattice.schema.loader import parse_model_from_string
from lattice.graph.builder import build_graph
from lattice.validators.reference_integrity import check_reference_integrity


class TestReferenceIntegrity:
    def test_valid_references(self, minimal_model, minimal_graph):
        result = check_reference_integrity(minimal_model, minimal_graph)

        assert result.is_valid

    def test_undefined_entity_reference(self):
        yaml = """
entities:
  Post:
    belongs_to: NonExistentUser
    attributes:
      - name: title
        type: string
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_reference_integrity(model, graph)

        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].code == "UNDEFINED_ENTITY_REF"
        assert "NonExistentUser" in result.errors[0].message

    def test_undefined_state_in_transition_from(self):
        yaml = """
entities:
  Task:
    states:
      - name: pending
        initial: true
      - name: done
        terminal: true

    transitions:
      - from: nonexistent
        to: done
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_reference_integrity(model, graph)

        assert not result.is_valid
        errors = [e for e in result.errors if e.code == "UNDEFINED_STATE_REF"]
        assert len(errors) == 1
        assert "nonexistent" in errors[0].message

    def test_undefined_state_in_transition_to(self):
        yaml = """
entities:
  Task:
    states:
      - name: pending
        initial: true
      - name: done
        terminal: true

    transitions:
      - from: pending
        to: nonexistent
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_reference_integrity(model, graph)

        assert not result.is_valid
        errors = [e for e in result.errors if e.code == "UNDEFINED_STATE_REF"]
        assert len(errors) == 1

    def test_multiple_broken_references(self):
        yaml = """
entities:
  Post:
    belongs_to: Author
    has_many: Comment

    states:
      - name: draft
        initial: true

    transitions:
      - from: review
        to: published
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_reference_integrity(model, graph)

        assert not result.is_valid
        # Should have errors for: Author, Comment, review, published
        assert len(result.errors) >= 2
