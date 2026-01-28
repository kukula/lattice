"""Tests for validation runner."""

import pytest

from lattice.validators.runner import run_validators, validate_model_file


class TestRunValidators:
    def test_combines_all_validators(self, minimal_model, minimal_graph):
        result = run_validators(minimal_model, minimal_graph)

        # minimal model should be valid
        assert result.is_valid

    def test_collects_errors_from_multiple_validators(self):
        from lattice.schema.loader import parse_model_from_string
        from lattice.graph.builder import build_graph

        yaml = """
entities:
  Orphan:
    attributes:
      - name: data
        type: string

  Task:
    states:
      - name: pending
        initial: true
      - name: secret

    transitions:
      - from: pending
        to: nonexistent
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = run_validators(model, graph)

        # Should have:
        # - ORPHAN_ENTITY for Orphan
        # - UNDEFINED_STATE_REF for nonexistent
        # - UNREACHABLE_STATE for secret
        assert len(result.errors) >= 2
        assert len(result.warnings) >= 1


class TestValidateModelFile:
    def test_validate_valid_file(self, examples_dir):
        result = validate_model_file(examples_dir / "minimal_valid.yaml")

        assert result.is_valid

    def test_validate_orphan_entity_file(self, examples_dir):
        result = validate_model_file(examples_dir / "invalid" / "orphan_entity.yaml")

        warnings = [w for w in result.warnings if w.code == "ORPHAN_ENTITY"]
        assert len(warnings) == 1
        assert warnings[0].entity == "OrphanWidget"

    def test_validate_unreachable_state_file(self, examples_dir):
        result = validate_model_file(
            examples_dir / "invalid" / "unreachable_state.yaml"
        )

        errors = [e for e in result.errors if e.code == "UNREACHABLE_STATE"]
        assert len(errors) == 1
        assert errors[0].state == "secret"

    def test_validate_broken_reference_file(self, examples_dir):
        result = validate_model_file(
            examples_dir / "invalid" / "broken_reference.yaml"
        )

        # Should have multiple reference errors
        ref_errors = [
            e
            for e in result.errors
            if e.code in ("UNDEFINED_ENTITY_REF", "UNDEFINED_STATE_REF")
        ]
        assert len(ref_errors) >= 3
