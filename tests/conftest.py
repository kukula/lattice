"""Shared fixtures for tests."""

from pathlib import Path

import pytest

from lattice.schema.loader import parse_model_from_string
from lattice.graph.builder import build_graph


@pytest.fixture
def examples_dir() -> Path:
    """Return the path to the examples directory."""
    return Path(__file__).parent.parent / "examples"


@pytest.fixture
def minimal_model_yaml() -> str:
    """Return a minimal valid model YAML string."""
    return """
entities:
  User:
    attributes:
      - name: email
        type: string
    relationships:
      - has_many: Post

  Post:
    belongs_to: User
    attributes:
      - name: title
        type: string
"""


@pytest.fixture
def stateful_model_yaml() -> str:
    """Return a model with states and transitions."""
    return """
entities:
  Task:
    attributes:
      - name: title
        type: string

    states:
      - name: pending
        initial: true
      - name: in_progress
      - name: completed
        terminal: true

    transitions:
      - from: pending
        to: in_progress
        trigger: start
      - from: in_progress
        to: completed
        trigger: complete
"""


@pytest.fixture
def minimal_model(minimal_model_yaml):
    """Return a parsed minimal model."""
    return parse_model_from_string(minimal_model_yaml)


@pytest.fixture
def minimal_graph(minimal_model):
    """Return a graph built from the minimal model."""
    return build_graph(minimal_model)


@pytest.fixture
def stateful_model(stateful_model_yaml):
    """Return a parsed stateful model."""
    return parse_model_from_string(stateful_model_yaml)


@pytest.fixture
def stateful_graph(stateful_model):
    """Return a graph built from the stateful model."""
    return build_graph(stateful_model)
