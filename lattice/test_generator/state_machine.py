"""Generate tests from state machine transitions."""

from ..graph.model_graph import ModelGraph
from .models import CaseSpec, CaseType


def _snake_case(s: str) -> str:
    """Convert a string to snake_case."""
    return s.lower().replace(" ", "_").replace("-", "_")


def generate_transition_tests(entity_name: str, graph: ModelGraph) -> list[CaseSpec]:
    """Generate positive transition tests for an entity.

    Creates one test per valid transition defined in the model.

    Args:
        entity_name: Name of the entity.
        graph: The model graph.

    Returns:
        List of TestCase objects for positive transitions.
    """
    test_cases = []
    states = graph.get_states_for_entity(entity_name)

    for state_data in states:
        state_name = state_data["name"]
        transitions = graph.get_transitions_from_state(entity_name, state_name)

        for transition in transitions:
            from_state = transition["from"]
            to_state = transition["to"]
            trigger = transition.get("trigger")
            guards = transition.get("requires", [])
            effects = transition.get("effects", [])

            test_name = f"test_{_snake_case(entity_name)}_{_snake_case(from_state)}_to_{_snake_case(to_state)}"

            # Build description
            desc_parts = [f"{entity_name} transitions from {from_state} to {to_state}"]
            if trigger:
                desc_parts.append(f" on {trigger}")

            test_cases.append(
                CaseSpec(
                    name=test_name,
                    test_type=CaseType.POSITIVE_TRANSITION,
                    entity=entity_name,
                    description="".join(desc_parts),
                    from_state=from_state,
                    to_state=to_state,
                    trigger=trigger,
                    guards=guards,
                    effects=effects,
                )
            )

    return test_cases


def generate_blocked_transition_tests(
    entity_name: str, graph: ModelGraph
) -> list[CaseSpec]:
    """Generate negative transition tests for invalid state jumps.

    Tests for adjacent state skips - e.g., if A->B->C, test that A->C directly is blocked.

    Args:
        entity_name: Name of the entity.
        graph: The model graph.

    Returns:
        List of TestCase objects for blocked transitions.
    """
    test_cases = []
    states = graph.get_states_for_entity(entity_name)

    # Build a set of valid transitions
    valid_transitions: set[tuple[str, str]] = set()
    for state_data in states:
        state_name = state_data["name"]
        transitions = graph.get_transitions_from_state(entity_name, state_name)
        for t in transitions:
            valid_transitions.add((t["from"], t["to"]))

    # Find the initial state
    initial_state = graph.get_initial_state(entity_name)
    if not initial_state:
        return test_cases

    # For each state, find states that are 2 hops away but not directly reachable
    state_names = [s["name"] for s in states]

    for state_name in state_names:
        # Get states reachable in one hop
        one_hop = {
            t["to"]
            for t in graph.get_transitions_from_state(entity_name, state_name)
        }

        # Get states reachable in two hops
        two_hop: set[str] = set()
        for next_state in one_hop:
            for t in graph.get_transitions_from_state(entity_name, next_state):
                two_hop.add(t["to"])

        # Find states that are 2 hops away but not directly reachable
        skip_states = two_hop - one_hop - {state_name}

        for skip_to in skip_states:
            # Only create test if this would be a meaningful skip
            # (i.e., there's no direct path from state_name to skip_to)
            if (state_name, skip_to) not in valid_transitions:
                test_name = f"test_{_snake_case(entity_name)}_cannot_skip_{_snake_case(state_name)}_to_{_snake_case(skip_to)}"
                test_cases.append(
                    CaseSpec(
                        name=test_name,
                        test_type=CaseType.NEGATIVE_TRANSITION,
                        entity=entity_name,
                        description=f"{entity_name} cannot skip from {state_name} directly to {skip_to}",
                        from_state=state_name,
                        to_state=skip_to,
                    )
                )

    return test_cases
