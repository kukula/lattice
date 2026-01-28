"""Find happy paths through state machines."""

from collections import deque

from ..graph.model_graph import ModelGraph
from .models import CaseSpec, CaseType


def find_happy_paths(entity_name: str, graph: ModelGraph) -> list[list[str]]:
    """Find shortest paths from initial state to each terminal state.

    Uses BFS to find the shortest path to each terminal state.

    Args:
        entity_name: Name of the entity.
        graph: The model graph.

    Returns:
        List of paths, where each path is a list of state names.
    """
    initial_state = graph.get_initial_state(entity_name)
    terminal_states = set(graph.get_terminal_states(entity_name))

    if not initial_state or not terminal_states:
        return []

    paths = []

    # BFS to find shortest path to each terminal state
    for terminal in terminal_states:
        path = _bfs_path(entity_name, graph, initial_state, terminal)
        if path:
            paths.append(path)

    # Sort paths by length (shortest first), then by terminal state name
    paths.sort(key=lambda p: (len(p), p[-1] if p else ""))

    return paths


def _bfs_path(
    entity_name: str, graph: ModelGraph, start: str, end: str
) -> list[str] | None:
    """Find shortest path between two states using BFS.

    Args:
        entity_name: Name of the entity.
        graph: The model graph.
        start: Starting state name.
        end: Target state name.

    Returns:
        List of state names forming the path, or None if no path exists.
    """
    if start == end:
        return [start]

    queue: deque[tuple[str, list[str]]] = deque()
    queue.append((start, [start]))
    visited: set[str] = {start}

    while queue:
        current, path = queue.popleft()

        for transition in graph.get_transitions_from_state(entity_name, current):
            next_state = transition["to"]

            if next_state == end:
                return path + [next_state]

            if next_state not in visited:
                visited.add(next_state)
                queue.append((next_state, path + [next_state]))

    return None


def _snake_case(s: str) -> str:
    """Convert a string to snake_case."""
    return s.lower().replace(" ", "_").replace("-", "_")


def generate_happy_path_tests(entity_name: str, graph: ModelGraph) -> list[CaseSpec]:
    """Generate happy path tests for an entity.

    Creates one test per path from initial to terminal state.

    Args:
        entity_name: Name of the entity.
        graph: The model graph.

    Returns:
        List of TestCase objects for happy paths.
    """
    test_cases = []
    paths = find_happy_paths(entity_name, graph)

    for path in paths:
        if len(path) < 2:
            continue

        terminal_state = path[-1]
        test_name = f"test_{_snake_case(entity_name)}_lifecycle_to_{_snake_case(terminal_state)}"

        # Build path description
        path_str = " → ".join(path)

        test_cases.append(
            CaseSpec(
                name=test_name,
                test_type=CaseType.HAPPY_PATH,
                entity=entity_name,
                description=f"Test path: {path_str}",
                from_state=path[0],
                to_state=terminal_state,
                path=path,
            )
        )

    return test_cases
