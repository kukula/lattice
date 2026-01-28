"""Main test generation orchestrator."""

from ..graph.builder import build_graph
from ..graph.model_graph import ModelGraph
from ..schema.loader import parse_model
from ..schema.models import LatticeModel
from .invariants import generate_entity_invariant_tests, generate_system_invariant_tests
from .models import GenerationResult, TestFile, TestType
from .path_finder import generate_happy_path_tests
from .state_machine import generate_blocked_transition_tests, generate_transition_tests


def _snake_case(s: str) -> str:
    """Convert a string to snake_case."""
    return s.lower().replace(" ", "_").replace("-", "_")


def generate_tests(model: LatticeModel, graph: ModelGraph) -> GenerationResult:
    """Generate test cases from a Lattice model.

    For each entity with states, generates:
    - Positive transition tests
    - Negative transition tests (for adjacent skips)
    - Happy path tests (initial → terminal)
    - Entity invariant tests

    Also generates system invariant tests in a separate file.

    Args:
        model: The parsed Lattice model.
        graph: The model graph built from the model.

    Returns:
        GenerationResult containing all test files.
    """
    files: list[TestFile] = []

    # Process each entity
    for entity_name, entity in model.entities.items():
        test_cases = []

        # Only generate state machine tests for entities with states
        if entity.states:
            # Positive transitions
            test_cases.extend(generate_transition_tests(entity_name, graph))

            # Negative transitions (adjacent skips)
            test_cases.extend(generate_blocked_transition_tests(entity_name, graph))

            # Happy paths
            test_cases.extend(generate_happy_path_tests(entity_name, graph))

        # Entity invariants (even for stateless entities)
        if entity.invariants:
            test_cases.extend(generate_entity_invariant_tests(entity))

        # Only create a file if there are test cases
        if test_cases:
            files.append(
                TestFile(
                    entity=entity_name,
                    filename=f"test_{_snake_case(entity_name)}.py",
                    test_cases=test_cases,
                )
            )

    # System invariants
    if model.system_invariants:
        system_tests = generate_system_invariant_tests(model)
        if system_tests:
            files.append(
                TestFile(
                    entity="system",
                    filename="test_system_invariants.py",
                    test_cases=system_tests,
                )
            )

    return GenerationResult(files=files)


def generate_tests_from_file(path: str) -> GenerationResult:
    """Generate tests from a YAML model file.

    Convenience wrapper that loads the model and builds the graph.

    Args:
        path: Path to the YAML model file.

    Returns:
        GenerationResult containing all test files.
    """
    model = parse_model(path)
    graph = build_graph(model)
    return generate_tests(model, graph)
