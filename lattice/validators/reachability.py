"""State reachability validators."""

from ..graph.model_graph import ModelGraph
from .base import ValidationResult


def check_unreachable_states(graph: ModelGraph) -> ValidationResult:
    """Check for states that cannot be reached from the initial state.

    An unreachable state indicates either:
    - A missing transition to that state
    - A state that should be removed
    - A missing initial state marker

    Args:
        graph: The model graph to check.

    Returns:
        ValidationResult with errors for unreachable states.
    """
    result = ValidationResult()

    for entity_name in graph.get_entity_names():
        states = graph.get_states_for_entity(entity_name)
        if not states:
            continue  # Entity has no states

        initial = graph.get_initial_state(entity_name)
        if not initial:
            # Check if there are states but no initial
            result.add_error(
                code="NO_INITIAL_STATE",
                message=f"Entity '{entity_name}' has states but no initial state defined",
                entity=entity_name,
            )
            continue

        reachable = graph.get_reachable_states(entity_name)
        all_states = {s["name"] for s in states}

        unreachable = all_states - reachable
        for state_name in unreachable:
            result.add_error(
                code="UNREACHABLE_STATE",
                message=f"State '{state_name}' cannot be reached from initial state '{initial}'",
                entity=entity_name,
                state=state_name,
            )

    return result


def check_terminal_states(graph: ModelGraph) -> ValidationResult:
    """Check for states with no outbound transitions that aren't marked terminal.

    A state with no outbound transitions that isn't marked as terminal
    may be an implicit terminal state, which should be explicitly marked.

    Args:
        graph: The model graph to check.

    Returns:
        ValidationResult with warnings for implicit terminal states.
    """
    result = ValidationResult()

    for entity_name in graph.get_entity_names():
        states = graph.get_states_for_entity(entity_name)
        if not states:
            continue

        terminal_states = set(graph.get_terminal_states(entity_name))
        no_outbound = set(graph.get_states_with_no_outbound_transitions(entity_name))

        # States with no outbound that aren't marked terminal
        implicit_terminals = no_outbound - terminal_states
        for state_name in implicit_terminals:
            result.add_warning(
                code="IMPLICIT_TERMINAL_STATE",
                message=f"State '{state_name}' has no outbound transitions but is not marked as terminal",
                entity=entity_name,
                state=state_name,
            )

    return result
