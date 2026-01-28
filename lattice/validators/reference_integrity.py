"""Reference integrity validator."""

from ..graph.model_graph import ModelGraph
from ..schema.models import LatticeModel
from .base import ValidationResult


def check_reference_integrity(
    model: LatticeModel, graph: ModelGraph
) -> ValidationResult:
    """Check that all references resolve to defined entities/states.

    This validator checks:
    - Relationship targets reference defined entities
    - Transition from/to states reference defined states

    Args:
        model: The parsed Lattice model.
        graph: The model graph.

    Returns:
        ValidationResult with errors for broken references.
    """
    result = ValidationResult()

    all_entity_names = set(model.get_all_entity_names())

    for entity_name, entity in model.entities.items():
        # Check relationship targets
        for rel in entity.relationships:
            if rel.target not in all_entity_names:
                result.add_error(
                    code="UNDEFINED_ENTITY_REF",
                    message=f"Relationship references undefined entity '{rel.target}'",
                    entity=entity_name,
                    referenced_entity=rel.target,
                    relationship_type=rel.type,
                )

        # Check transition state references
        if entity.states:
            defined_states = {s.name for s in entity.states}

            for transition in entity.transitions:
                # Check from_states
                for from_state in transition.from_states:
                    if from_state not in defined_states:
                        result.add_error(
                            code="UNDEFINED_STATE_REF",
                            message=f"Transition references undefined source state '{from_state}'",
                            entity=entity_name,
                            state=from_state,
                        )

                # Check to state
                if transition.to not in defined_states:
                    result.add_error(
                        code="UNDEFINED_STATE_REF",
                        message=f"Transition references undefined target state '{transition.to}'",
                        entity=entity_name,
                        state=transition.to,
                    )

    return result
