"""Builder for converting LatticeModel to ModelGraph."""

from ..schema.models import LatticeModel
from .model_graph import ModelGraph


def build_graph(model: LatticeModel) -> ModelGraph:
    """Build a ModelGraph from a LatticeModel.

    Args:
        model: The parsed Lattice model.

    Returns:
        A ModelGraph representing the model.
    """
    graph = ModelGraph()

    # Add all entities first
    for entity_name, entity in model.entities.items():
        graph.add_entity(
            entity_name,
            has_states=bool(entity.states),
            has_transitions=bool(entity.transitions),
        )

        # Add attributes
        for attr in entity.attributes:
            graph.add_attribute(
                entity_name,
                attr.name,
                attr_type=attr.type,
                unique=attr.unique,
                optional=attr.optional,
            )

        # Add states
        for state in entity.states:
            graph.add_state(
                entity_name,
                state.name,
                initial=state.initial,
                terminal=state.terminal,
            )

        # Add transitions
        for transition in entity.transitions:
            for from_state in transition.from_states:
                graph.add_transition(
                    entity_name,
                    from_state,
                    transition.to,
                    trigger=transition.trigger,
                    requires=transition.requires,
                    effects=transition.effects,
                )

        # Add entity-level invariants
        for invariant in entity.invariants:
            graph.add_invariant(
                entity_name,
                invariant.description,
                invariant.formal,
            )

    # Add relationships (after all entities exist)
    for entity_name, entity in model.entities.items():
        for rel in entity.relationships:
            graph.add_relationship(
                entity_name,
                rel.target,
                rel.type,
                rel.conditions,
            )

    # Add system-level invariants
    for invariant in model.system_invariants:
        graph.add_invariant(
            None,
            invariant.description,
            invariant.formal,
        )

    return graph
