"""Tests for test_generator.path_finder."""

import pytest

from lattice.graph.builder import build_graph
from lattice.schema.loader import parse_model_from_string
from lattice.test_generator.models import TestType
from lattice.test_generator.path_finder import (
    find_happy_paths,
    generate_happy_path_tests,
)


@pytest.fixture
def linear_state_machine_yaml():
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
      - from: in_progress
        to: completed
        trigger: complete
"""


@pytest.fixture
def multiple_terminals_yaml():
    """State machine with multiple terminal states."""
    return """
entities:
  Order:
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
      - from: submitted
        to: delivered
        trigger: deliver
      - from: draft
        to: cancelled
        trigger: cancel
      - from: submitted
        to: cancelled
        trigger: cancel
"""


@pytest.fixture
def diamond_state_machine_yaml():
    """State machine with diamond pattern (multiple paths to same terminal)."""
    return """
entities:
  Request:
    states:
      - name: new
        initial: true
      - name: path_a
      - name: path_b
      - name: done
        terminal: true
    transitions:
      - from: new
        to: path_a
        trigger: choose_a
      - from: new
        to: path_b
        trigger: choose_b
      - from: path_a
        to: done
        trigger: finish_a
      - from: path_b
        to: done
        trigger: finish_b
"""


class TestFindHappyPaths:
    """Tests for find_happy_paths."""

    def test_linear_path(self, linear_state_machine_yaml):
        """Should find path through linear state machine."""
        model = parse_model_from_string(linear_state_machine_yaml)
        graph = build_graph(model)

        paths = find_happy_paths("Task", graph)

        assert len(paths) == 1
        assert paths[0] == ["pending", "in_progress", "completed"]

    def test_multiple_terminals(self, multiple_terminals_yaml):
        """Should find path to each terminal state."""
        model = parse_model_from_string(multiple_terminals_yaml)
        graph = build_graph(model)

        paths = find_happy_paths("Order", graph)

        assert len(paths) == 2

        # Extract terminal states
        terminals = {path[-1] for path in paths}
        assert terminals == {"delivered", "cancelled"}

    def test_finds_shortest_path(self, multiple_terminals_yaml):
        """Should find shortest path to each terminal."""
        model = parse_model_from_string(multiple_terminals_yaml)
        graph = build_graph(model)

        paths = find_happy_paths("Order", graph)

        # Path to cancelled should be shorter (draft -> cancelled)
        # vs path to delivered (draft -> submitted -> delivered)
        cancelled_path = next(p for p in paths if p[-1] == "cancelled")
        delivered_path = next(p for p in paths if p[-1] == "delivered")

        assert len(cancelled_path) == 2  # draft -> cancelled
        assert len(delivered_path) == 3  # draft -> submitted -> delivered

    def test_diamond_pattern(self, diamond_state_machine_yaml):
        """Should find path through diamond pattern."""
        model = parse_model_from_string(diamond_state_machine_yaml)
        graph = build_graph(model)

        paths = find_happy_paths("Request", graph)

        # Should find one path to 'done', the shortest one
        assert len(paths) == 1
        assert paths[0][0] == "new"
        assert paths[0][-1] == "done"
        assert len(paths[0]) == 3  # Either through path_a or path_b

    def test_no_states_returns_empty(self):
        """Entity without states should return empty list."""
        yaml = """
entities:
  User:
    attributes:
      - name: email
        type: string
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        paths = find_happy_paths("User", graph)

        assert paths == []

    def test_no_terminal_states_returns_empty(self):
        """Entity without terminal states should return empty list."""
        yaml = """
entities:
  Infinite:
    states:
      - name: a
        initial: true
      - name: b
    transitions:
      - from: a
        to: b
      - from: b
        to: a
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        paths = find_happy_paths("Infinite", graph)

        assert paths == []


class TestGenerateHappyPathTests:
    """Tests for generate_happy_path_tests."""

    def test_generates_test_per_path(self, multiple_terminals_yaml):
        """Should generate one test per happy path."""
        model = parse_model_from_string(multiple_terminals_yaml)
        graph = build_graph(model)

        tests = generate_happy_path_tests("Order", graph)

        assert len(tests) == 2
        assert all(t.test_type == TestType.HAPPY_PATH for t in tests)

    def test_path_in_test_case(self, linear_state_machine_yaml):
        """Test case should include the full path."""
        model = parse_model_from_string(linear_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_happy_path_tests("Task", graph)

        assert len(tests) == 1
        assert tests[0].path == ["pending", "in_progress", "completed"]

    def test_names_include_terminal_state(self, multiple_terminals_yaml):
        """Test names should indicate the terminal state."""
        model = parse_model_from_string(multiple_terminals_yaml)
        graph = build_graph(model)

        tests = generate_happy_path_tests("Order", graph)

        names = [t.name for t in tests]
        assert any("delivered" in name for name in names)
        assert any("cancelled" in name for name in names)

    def test_description_contains_path(self, linear_state_machine_yaml):
        """Description should contain the path."""
        model = parse_model_from_string(linear_state_machine_yaml)
        graph = build_graph(model)

        tests = generate_happy_path_tests("Task", graph)

        assert "pending" in tests[0].description
        assert "completed" in tests[0].description
