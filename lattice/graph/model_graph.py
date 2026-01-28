"""ModelGraph wrapper around networkx for Lattice models."""

from typing import Any, Iterator

import networkx as nx

from .node_types import NodeType, EdgeType


class ModelGraph:
    """A graph representation of a Lattice model.

    Wraps a networkx DiGraph with domain-specific methods for working
    with entities, states, transitions, and relationships.
    """

    def __init__(self):
        """Initialize an empty model graph."""
        self._graph = nx.DiGraph()

    @property
    def graph(self) -> nx.DiGraph:
        """Get the underlying networkx graph."""
        return self._graph

    # -------------------------------------------------------------------------
    # Node management
    # -------------------------------------------------------------------------

    def add_entity(self, name: str, **attrs: Any) -> str:
        """Add an entity node to the graph.

        Args:
            name: The entity name.
            **attrs: Additional attributes for the node.

        Returns:
            The node ID.
        """
        node_id = f"entity:{name}"
        self._graph.add_node(
            node_id,
            node_type=NodeType.ENTITY,
            name=name,
            **attrs,
        )
        return node_id

    def add_state(self, entity_name: str, state_name: str, **attrs: Any) -> str:
        """Add a state node to the graph.

        Args:
            entity_name: The owning entity name.
            state_name: The state name.
            **attrs: Additional attributes (initial, terminal).

        Returns:
            The node ID.
        """
        node_id = f"state:{entity_name}.{state_name}"
        self._graph.add_node(
            node_id,
            node_type=NodeType.STATE,
            entity=entity_name,
            name=state_name,
            **attrs,
        )

        # Add edge from entity to state
        entity_id = f"entity:{entity_name}"
        if self._graph.has_node(entity_id):
            self._graph.add_edge(
                entity_id, node_id, edge_type=EdgeType.HAS_STATE
            )

        return node_id

    def add_transition(
        self,
        entity_name: str,
        from_state: str,
        to_state: str,
        trigger: str | None = None,
        requires: list[str] | None = None,
        effects: list[str] | None = None,
    ) -> None:
        """Add a transition edge between states.

        Args:
            entity_name: The owning entity name.
            from_state: The source state name.
            to_state: The target state name.
            trigger: The event that triggers the transition.
            requires: Guard conditions.
            effects: Side effects.
        """
        from_id = f"state:{entity_name}.{from_state}"
        to_id = f"state:{entity_name}.{to_state}"

        self._graph.add_edge(
            from_id,
            to_id,
            edge_type=EdgeType.TRANSITION,
            trigger=trigger,
            requires=requires or [],
            effects=effects or [],
        )

    def add_relationship(
        self,
        from_entity: str,
        to_entity: str,
        rel_type: str,
        conditions: list[str] | None = None,
    ) -> None:
        """Add a relationship edge between entities.

        Args:
            from_entity: The source entity name.
            to_entity: The target entity name.
            rel_type: The relationship type (belongs_to, has_many, etc.).
            conditions: Optional conditions on the relationship.
        """
        from_id = f"entity:{from_entity}"
        to_id = f"entity:{to_entity}"

        try:
            edge_type = EdgeType(rel_type)
        except ValueError:
            edge_type = EdgeType.DEPENDS_ON

        self._graph.add_edge(
            from_id,
            to_id,
            edge_type=edge_type,
            conditions=conditions or [],
        )

    def add_attribute(
        self, entity_name: str, attr_name: str, **attrs: Any
    ) -> str:
        """Add an attribute node to the graph.

        Args:
            entity_name: The owning entity name.
            attr_name: The attribute name.
            **attrs: Additional attributes (type, unique, optional, etc.).

        Returns:
            The node ID.
        """
        node_id = f"attr:{entity_name}.{attr_name}"
        self._graph.add_node(
            node_id,
            node_type=NodeType.ATTRIBUTE,
            entity=entity_name,
            name=attr_name,
            **attrs,
        )

        # Add edge from entity to attribute
        entity_id = f"entity:{entity_name}"
        if self._graph.has_node(entity_id):
            self._graph.add_edge(
                entity_id, node_id, edge_type=EdgeType.HAS_ATTRIBUTE
            )

        return node_id

    def add_invariant(
        self, entity_name: str | None, description: str, formal: str | None = None
    ) -> str:
        """Add an invariant node to the graph.

        Args:
            entity_name: The owning entity name, or None for system invariants.
            description: The invariant description.
            formal: Optional formal expression.

        Returns:
            The node ID.
        """
        scope = "system" if entity_name is None else "entity"
        node_id = f"invariant:{entity_name or 'system'}:{hash(description)}"

        self._graph.add_node(
            node_id,
            node_type=NodeType.INVARIANT,
            entity=entity_name,
            description=description,
            formal=formal,
            scope=scope,
        )

        # Add edge from entity to invariant
        if entity_name:
            entity_id = f"entity:{entity_name}"
            if self._graph.has_node(entity_id):
                self._graph.add_edge(
                    entity_id, node_id, edge_type=EdgeType.HAS_INVARIANT
                )

        return node_id

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_entity_names(self) -> list[str]:
        """Get all entity names in the graph."""
        return [
            data["name"]
            for _, data in self._graph.nodes(data=True)
            if data.get("node_type") == NodeType.ENTITY
        ]

    def get_entity_node(self, name: str) -> dict[str, Any] | None:
        """Get an entity node by name."""
        node_id = f"entity:{name}"
        if self._graph.has_node(node_id):
            return dict(self._graph.nodes[node_id])
        return None

    def get_states_for_entity(self, entity_name: str) -> list[dict[str, Any]]:
        """Get all states for an entity."""
        states = []
        for node_id, data in self._graph.nodes(data=True):
            if (
                data.get("node_type") == NodeType.STATE
                and data.get("entity") == entity_name
            ):
                states.append(dict(data))
        return states

    def get_initial_state(self, entity_name: str) -> str | None:
        """Get the initial state name for an entity."""
        for state in self.get_states_for_entity(entity_name):
            if state.get("initial"):
                return state["name"]
        return None

    def get_terminal_states(self, entity_name: str) -> list[str]:
        """Get terminal state names for an entity."""
        return [
            state["name"]
            for state in self.get_states_for_entity(entity_name)
            if state.get("terminal")
        ]

    def get_transitions_from_state(
        self, entity_name: str, state_name: str
    ) -> list[dict[str, Any]]:
        """Get all transitions from a state."""
        state_id = f"state:{entity_name}.{state_name}"
        transitions = []

        for _, target, data in self._graph.out_edges(state_id, data=True):
            if data.get("edge_type") == EdgeType.TRANSITION:
                # Extract target state name
                target_state = target.split(".")[-1]
                transitions.append({
                    "from": state_name,
                    "to": target_state,
                    "trigger": data.get("trigger"),
                    "requires": data.get("requires", []),
                    "effects": data.get("effects", []),
                })

        return transitions

    def has_any_relationships(self, entity_name: str) -> bool:
        """Check if an entity has any relationships (in or out)."""
        entity_id = f"entity:{entity_name}"

        if not self._graph.has_node(entity_id):
            return False

        relationship_types = {
            EdgeType.BELONGS_TO,
            EdgeType.HAS_MANY,
            EdgeType.HAS_ONE,
            EdgeType.DEPENDS_ON,
        }

        # Check outgoing edges
        for _, _, data in self._graph.out_edges(entity_id, data=True):
            if data.get("edge_type") in relationship_types:
                return True

        # Check incoming edges
        for _, _, data in self._graph.in_edges(entity_id, data=True):
            if data.get("edge_type") in relationship_types:
                return True

        return False

    def get_relationships_for_entity(
        self, entity_name: str
    ) -> list[dict[str, Any]]:
        """Get all relationships for an entity (both directions)."""
        entity_id = f"entity:{entity_name}"
        relationships = []

        relationship_types = {
            EdgeType.BELONGS_TO,
            EdgeType.HAS_MANY,
            EdgeType.HAS_ONE,
            EdgeType.DEPENDS_ON,
        }

        # Outgoing relationships
        for _, target, data in self._graph.out_edges(entity_id, data=True):
            if data.get("edge_type") in relationship_types:
                target_name = target.replace("entity:", "")
                relationships.append({
                    "type": data["edge_type"].value,
                    "target": target_name,
                    "direction": "outgoing",
                })

        # Incoming relationships
        for source, _, data in self._graph.in_edges(entity_id, data=True):
            if data.get("edge_type") in relationship_types:
                source_name = source.replace("entity:", "")
                relationships.append({
                    "type": data["edge_type"].value,
                    "target": source_name,
                    "direction": "incoming",
                })

        return relationships

    def get_reachable_states(self, entity_name: str) -> set[str]:
        """Get all states reachable from the initial state.

        Args:
            entity_name: The entity name.

        Returns:
            Set of reachable state names.
        """
        initial = self.get_initial_state(entity_name)
        if not initial:
            return set()

        initial_id = f"state:{entity_name}.{initial}"
        reachable_ids = set()

        # BFS from initial state, following only transition edges
        queue = [initial_id]
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Only add if it's a state node
            if self._graph.has_node(current):
                node_data = self._graph.nodes[current]
                if node_data.get("node_type") == NodeType.STATE:
                    reachable_ids.add(current)

            # Follow transition edges
            for _, target, data in self._graph.out_edges(current, data=True):
                if data.get("edge_type") == EdgeType.TRANSITION:
                    if target not in visited:
                        queue.append(target)

        # Convert IDs to state names
        return {
            self._graph.nodes[sid]["name"]
            for sid in reachable_ids
            if self._graph.has_node(sid)
        }

    def get_states_with_no_outbound_transitions(
        self, entity_name: str
    ) -> list[str]:
        """Get states that have no outbound transitions.

        Args:
            entity_name: The entity name.

        Returns:
            List of state names with no outbound transitions.
        """
        states = []
        for state in self.get_states_for_entity(entity_name):
            state_name = state["name"]
            transitions = self.get_transitions_from_state(entity_name, state_name)
            if not transitions:
                states.append(state_name)
        return states

    def iter_entity_relationships(self) -> Iterator[tuple[str, str, str]]:
        """Iterate over all entity relationships.

        Yields:
            Tuples of (from_entity, to_entity, relationship_type).
        """
        relationship_types = {
            EdgeType.BELONGS_TO,
            EdgeType.HAS_MANY,
            EdgeType.HAS_ONE,
            EdgeType.DEPENDS_ON,
        }

        for source, target, data in self._graph.edges(data=True):
            edge_type = data.get("edge_type")
            if edge_type is not None and edge_type in relationship_types:
                from_entity = source.replace("entity:", "")
                to_entity = target.replace("entity:", "")
                yield from_entity, to_entity, edge_type.value
