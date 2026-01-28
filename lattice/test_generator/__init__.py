"""Test generation module for Lattice."""

from .generator import generate_tests, generate_tests_from_file
from .models import (
    CaseSpec,
    CaseType,
    FileSpec,
    GenerationResult,
    TestCase,
    TestFile,
    TestType,
)

__all__ = [
    "generate_tests",
    "generate_tests_from_file",
    "CaseSpec",
    "CaseType",
    "FileSpec",
    "GenerationResult",
    # Aliases for backwards compatibility
    "TestCase",
    "TestFile",
    "TestType",
]
