"""Tests for graph builder."""

import pytest

from lattice.schema.loader import parse_model_from_string
from lattice.graph.builder import build_graph
from lattice.graph.node_types import NodeType


class TestBuildGraph:
    def test_build_entities(self, minimal_model):
        graph = build_graph(minimal_model)

        entity_names = graph.get_entity_names()
        assert "User" in entity_names
        assert "Post" in entity_names

    def test_build_relationships(self, minimal_model):
        graph = build_graph(minimal_model)

        # Post belongs_to User
        assert graph.has_any_relationships("Post")
        assert graph.has_any_relationships("User")

    def test_build_states(self, stateful_model):
        graph = build_graph(stateful_model)

        states = graph.get_states_for_entity("Task")
        state_names = {s["name"] for s in states}
        assert state_names == {"pending", "in_progress", "completed"}

    def test_build_transitions(self, stateful_model):
        graph = build_graph(stateful_model)

        transitions = graph.get_transitions_from_state("Task", "pending")
        assert len(transitions) == 1
        assert transitions[0]["to"] == "in_progress"

    def test_build_initial_state(self, stateful_model):
        graph = build_graph(stateful_model)

        initial = graph.get_initial_state("Task")
        assert initial == "pending"

    def test_build_terminal_state(self, stateful_model):
        graph = build_graph(stateful_model)

        terminals = graph.get_terminal_states("Task")
        assert terminals == ["completed"]

    def test_build_multi_from_transition(self):
        yaml = """
entities:
  Order:
    states:
      - name: draft
        initial: true
      - name: submitted
      - name: cancelled
        terminal: true
    transitions:
      - from: [draft, submitted]
        to: cancelled
        trigger: cancel
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        # Both draft and submitted should have transitions to cancelled
        draft_trans = graph.get_transitions_from_state("Order", "draft")
        submitted_trans = graph.get_transitions_from_state("Order", "submitted")

        assert any(t["to"] == "cancelled" for t in draft_trans)
        assert any(t["to"] == "cancelled" for t in submitted_trans)
