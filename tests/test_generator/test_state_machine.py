"""Tests for test_generator.state_machine."""

import pytest

from lattice.graph.builder import build_graph
from lattice.schema.loader import parse_model_from_string
from lattice.test_generator.models import TestType
from lattice.test_generator.state_machine import (
    generate_blocked_transition_tests,
    generate_transition_tests,
)


@pytest.fixture
def simple_state_machine_yaml():
    """A simple linear state machine."""
    return """
entities:
  Task:
    states:
      - name: pending
        initial: true
      - name: in_progress
      - name: completed
        terminal: true
    transitions:
      - from: pending
        to: in_progress
        trigger: start
        requires:
          - assigned_to.present
        effects:
          - notify_assignee
      - from: in_progress
        to: completed
        trigger: complete
"""


@pytest.fixture
def branching_state_machine_yaml():
    """A state machine with multiple paths."""
    return """
entities:
  Order:
    states:
      - name: draft
        initial: true
      - name: submitted
      - name: cancelled
        terminal: true
      - name: delivered
        terminal: true
    transitions:
      - from: draft
        to: submitted
        trigger: submit
      - from: submitted
        to: delivered
        trigger: deliver
      - from: [draft, submitted]
        to: cancelled
        trigger: cancel
"""


class TestGenerateTransitionTests:
    """Tests for generate_transition_tests."""

    def test_generates_test_per_transition(self, simple_state_machine_yaml):
        """Should generate one test per transition."""
        model = parse_model_from_string(simple_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_transition_tests("Task", graph)

        assert len(tests) == 2
        assert all(t.test_type == TestType.POSITIVE_TRANSITION for t in tests)

    def test_captures_transition_details(self, simple_state_machine_yaml):
        """Should capture trigger, guards, and effects."""
        model = parse_model_from_string(simple_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_transition_tests("Task", graph)

        # Find the pending -> in_progress test
        start_test = next(t for t in tests if t.from_state == "pending")

        assert start_test.to_state == "in_progress"
        assert start_test.trigger == "start"
        assert "assigned_to.present" in start_test.guards
        assert "notify_assignee" in start_test.effects

    def test_generates_snake_case_names(self, simple_state_machine_yaml):
        """Test names should be in snake_case."""
        model = parse_model_from_string(simple_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_transition_tests("Task", graph)

        assert tests[0].name == "test_task_pending_to_in_progress"
        assert tests[1].name == "test_task_in_progress_to_completed"

    def test_handles_multiple_from_states(self, branching_state_machine_yaml):
        """Should create separate tests for transitions with multiple from states."""
        model = parse_model_from_string(branching_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_transition_tests("Order", graph)

        # Should have: draft->submitted, submitted->delivered,
        # draft->cancelled, submitted->cancelled
        assert len(tests) == 4

        cancel_tests = [t for t in tests if t.to_state == "cancelled"]
        assert len(cancel_tests) == 2

    def test_entity_without_states_returns_empty(self):
        """Entities without states should return empty list."""
        yaml = """
entities:
  User:
    attributes:
      - name: email
        type: string
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        tests = generate_transition_tests("User", graph)

        assert tests == []


class TestGenerateBlockedTransitionTests:
    """Tests for generate_blocked_transition_tests."""

    def test_detects_skipped_states(self, simple_state_machine_yaml):
        """Should detect when states can be skipped."""
        model = parse_model_from_string(simple_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_blocked_transition_tests("Task", graph)

        # pending -> completed would skip in_progress
        assert len(tests) == 1
        assert tests[0].from_state == "pending"
        assert tests[0].to_state == "completed"
        assert tests[0].test_type == TestType.NEGATIVE_TRANSITION

    def test_no_blocked_for_valid_paths(self, branching_state_machine_yaml):
        """Should not flag transitions that are actually valid."""
        model = parse_model_from_string(branching_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_blocked_transition_tests("Order", graph)

        # draft -> cancelled is valid, so shouldn't be flagged
        blocked_pairs = [(t.from_state, t.to_state) for t in tests]
        assert ("draft", "cancelled") not in blocked_pairs

    def test_detects_adjacent_skip(self, branching_state_machine_yaml):
        """Should detect skipping adjacent states."""
        model = parse_model_from_string(branching_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_blocked_transition_tests("Order", graph)

        # draft -> delivered would skip submitted
        blocked_pairs = [(t.from_state, t.to_state) for t in tests]
        assert ("draft", "delivered") in blocked_pairs
