"""Data models for test generation."""

from dataclasses import dataclass, field
from enum import Enum


class CaseType(Enum):
    """Type of generated test case."""

    POSITIVE_TRANSITION = "positive_transition"  # Valid state transition
    NEGATIVE_TRANSITION = "negative_transition"  # Blocked/invalid transition
    HAPPY_PATH = "happy_path"  # Full path initial → terminal
    ENTITY_INVARIANT = "entity_invariant"  # Entity-level invariant
    SYSTEM_INVARIANT = "system_invariant"  # System-level invariant


# Alias for backwards compatibility
TestType = CaseType


@dataclass
class CaseSpec:
    """A single test case to be generated."""

    name: str  # e.g., test_order_draft_to_submitted
    test_type: CaseType
    entity: str
    description: str
    from_state: str | None = None
    to_state: str | None = None
    trigger: str | None = None
    guards: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)
    path: list[str] = field(default_factory=list)  # For happy path tests
    formal: str | None = None  # For invariant tests


# Alias for backwards compatibility
TestCase = CaseSpec


@dataclass
class FileSpec:
    """A pytest file to be generated."""

    entity: str
    filename: str  # e.g., test_order.py
    test_cases: list[CaseSpec] = field(default_factory=list)


# Alias for backwards compatibility
TestFile = FileSpec


@dataclass
class GenerationResult:
    """Result of test generation."""

    files: list[FileSpec] = field(default_factory=list)

    @property
    def total_tests(self) -> int:
        """Total number of test cases across all files."""
        return sum(len(f.test_cases) for f in self.files)
