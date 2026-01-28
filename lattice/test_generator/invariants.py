"""Generate tests from invariants."""

import re

from ..schema.models import Entity, LatticeModel
from .models import CaseSpec, CaseType


def _snake_case(s: str) -> str:
    """Convert a string to snake_case."""
    # Remove non-alphanumeric chars except spaces/underscores
    s = re.sub(r"[^\w\s]", "", s)
    return s.lower().replace(" ", "_").replace("-", "_")


def _truncate(s: str, max_len: int = 50) -> str:
    """Truncate a string and add ellipsis if too long."""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def generate_entity_invariant_tests(entity: Entity) -> list[CaseSpec]:
    """Generate tests for entity-level invariants.

    Args:
        entity: The entity to generate tests for.

    Returns:
        List of TestCase objects for entity invariants.
    """
    test_cases = []

    for i, invariant in enumerate(entity.invariants):
        # Create a meaningful test name from description
        desc_slug = _snake_case(_truncate(invariant.description, 40))
        test_name = f"test_{_snake_case(entity.name)}_invariant_{desc_slug}"

        # Ensure unique names by adding index if needed
        if any(tc.name == test_name for tc in test_cases):
            test_name = f"{test_name}_{i}"

        test_cases.append(
            CaseSpec(
                name=test_name,
                test_type=CaseType.ENTITY_INVARIANT,
                entity=entity.name,
                description=invariant.description,
                formal=invariant.formal,
            )
        )

    return test_cases


def generate_system_invariant_tests(model: LatticeModel) -> list[CaseSpec]:
    """Generate tests for system-level invariants.

    Args:
        model: The full Lattice model.

    Returns:
        List of TestCase objects for system invariants.
    """
    test_cases = []

    for i, invariant in enumerate(model.system_invariants):
        # Create a meaningful test name from description
        desc_slug = _snake_case(_truncate(invariant.description, 40))
        test_name = f"test_system_invariant_{desc_slug}"

        # Ensure unique names by adding index if needed
        if any(tc.name == test_name for tc in test_cases):
            test_name = f"{test_name}_{i}"

        test_cases.append(
            CaseSpec(
                name=test_name,
                test_type=CaseType.SYSTEM_INVARIANT,
                entity="system",
                description=invariant.description,
                formal=invariant.formal,
            )
        )

    return test_cases
