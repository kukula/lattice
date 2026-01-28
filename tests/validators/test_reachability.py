"""Tests for state reachability validators."""

import pytest

from lattice.schema.loader import parse_model_from_string
from lattice.graph.builder import build_graph
from lattice.validators.reachability import (
    check_unreachable_states,
    check_terminal_states,
)


class TestUnreachableStates:
    def test_all_states_reachable(self, stateful_graph):
        result = check_unreachable_states(stateful_graph)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_detects_unreachable_state(self):
        yaml = """
entities:
  Task:
    states:
      - name: pending
        initial: true
      - name: done
        terminal: true
      - name: secret

    transitions:
      - from: pending
        to: done
      - from: secret
        to: done
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_unreachable_states(graph)

        assert len(result.errors) == 1
        assert result.errors[0].code == "UNREACHABLE_STATE"
        assert result.errors[0].state == "secret"

    def test_no_initial_state_error(self):
        yaml = """
entities:
  Task:
    states:
      - name: pending
      - name: done

    transitions:
      - from: pending
        to: done
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_unreachable_states(graph)

        assert len(result.errors) == 1
        assert result.errors[0].code == "NO_INITIAL_STATE"

    def test_entity_without_states_skipped(self, minimal_graph):
        # minimal_graph has entities without states
        result = check_unreachable_states(minimal_graph)

        assert result.is_valid


class TestTerminalStates:
    def test_all_terminals_marked(self, stateful_graph):
        result = check_terminal_states(stateful_graph)

        # All states with no outbound are marked terminal
        assert len(result.warnings) == 0

    def test_detects_implicit_terminal(self):
        yaml = """
entities:
  Task:
    states:
      - name: pending
        initial: true
      - name: stuck

    transitions:
      - from: pending
        to: stuck
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_terminal_states(graph)

        assert len(result.warnings) == 1
        assert result.warnings[0].code == "IMPLICIT_TERMINAL_STATE"
        assert result.warnings[0].state == "stuck"

    def test_marked_terminal_no_warning(self):
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
        to: done
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_terminal_states(graph)

        assert len(result.warnings) == 0
