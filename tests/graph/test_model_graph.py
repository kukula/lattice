"""Tests for ModelGraph."""

import pytest

from lattice.graph.model_graph import ModelGraph
from lattice.graph.node_types import NodeType, EdgeType


class TestModelGraphBasics:
    def test_add_entity(self):
        graph = ModelGraph()
        node_id = graph.add_entity("User", custom_attr="value")

        assert node_id == "entity:User"
        assert "User" in graph.get_entity_names()

        node = graph.get_entity_node("User")
        assert node is not None
        assert node["name"] == "User"
        assert node["custom_attr"] == "value"

    def test_add_state(self):
        graph = ModelGraph()
        graph.add_entity("Task")
        graph.add_state("Task", "pending", initial=True)
        graph.add_state("Task", "done", terminal=True)

        states = graph.get_states_for_entity("Task")
        assert len(states) == 2

        state_names = {s["name"] for s in states}
        assert state_names == {"pending", "done"}

    def test_add_transition(self):
        graph = ModelGraph()
        graph.add_entity("Task")
        graph.add_state("Task", "pending", initial=True)
        graph.add_state("Task", "done", terminal=True)
        graph.add_transition("Task", "pending", "done", trigger="complete")

        transitions = graph.get_transitions_from_state("Task", "pending")
        assert len(transitions) == 1
        assert transitions[0]["to"] == "done"
        assert transitions[0]["trigger"] == "complete"

    def test_add_relationship(self):
        graph = ModelGraph()
        graph.add_entity("User")
        graph.add_entity("Post")
        graph.add_relationship("Post", "User", "belongs_to")

        assert graph.has_any_relationships("Post")
        assert graph.has_any_relationships("User")


class TestModelGraphQueries:
    def test_get_initial_state(self):
        graph = ModelGraph()
        graph.add_entity("Task")
        graph.add_state("Task", "draft")
        graph.add_state("Task", "active", initial=True)
        graph.add_state("Task", "done", terminal=True)

        initial = graph.get_initial_state("Task")
        assert initial == "active"

    def test_get_terminal_states(self):
        graph = ModelGraph()
        graph.add_entity("Order")
        graph.add_state("Order", "pending", initial=True)
        graph.add_state("Order", "completed", terminal=True)
        graph.add_state("Order", "cancelled", terminal=True)

        terminals = graph.get_terminal_states("Order")
        assert set(terminals) == {"completed", "cancelled"}

    def test_get_reachable_states(self):
        graph = ModelGraph()
        graph.add_entity("Task")
        graph.add_state("Task", "pending", initial=True)
        graph.add_state("Task", "active")
        graph.add_state("Task", "done", terminal=True)
        graph.add_state("Task", "unreachable")  # No incoming transitions

        graph.add_transition("Task", "pending", "active")
        graph.add_transition("Task", "active", "done")

        reachable = graph.get_reachable_states("Task")
        assert reachable == {"pending", "active", "done"}
        assert "unreachable" not in reachable

    def test_get_states_with_no_outbound(self):
        graph = ModelGraph()
        graph.add_entity("Task")
        graph.add_state("Task", "pending", initial=True)
        graph.add_state("Task", "done", terminal=True)
        graph.add_state("Task", "stuck")  # No outbound

        graph.add_transition("Task", "pending", "done")
        graph.add_transition("Task", "pending", "stuck")

        no_outbound = graph.get_states_with_no_outbound_transitions("Task")
        assert set(no_outbound) == {"done", "stuck"}

    def test_has_any_relationships_false(self):
        graph = ModelGraph()
        graph.add_entity("Orphan")

        assert not graph.has_any_relationships("Orphan")

    def test_get_relationships_for_entity(self):
        graph = ModelGraph()
        graph.add_entity("User")
        graph.add_entity("Post")
        graph.add_entity("Comment")

        graph.add_relationship("User", "Post", "has_many")
        graph.add_relationship("Comment", "User", "belongs_to")

        user_rels = graph.get_relationships_for_entity("User")
        assert len(user_rels) == 2  # outgoing has_many and incoming belongs_to

    def test_iter_entity_relationships(self):
        graph = ModelGraph()
        graph.add_entity("User")
        graph.add_entity("Post")
        graph.add_relationship("Post", "User", "belongs_to")
        graph.add_relationship("User", "Post", "has_many")

        rels = list(graph.iter_entity_relationships())
        assert len(rels) == 2
