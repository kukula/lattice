"""Validation runner that orchestrates all validators."""

from pathlib import Path

from ..graph.builder import build_graph
from ..graph.model_graph import ModelGraph
from ..schema.loader import parse_model
from ..schema.models import LatticeModel
from .base import ValidationResult
from .orphan_detector import check_orphan_entities
from .reachability import check_terminal_states, check_unreachable_states
from .reference_integrity import check_reference_integrity


def run_validators(model: LatticeModel, graph: ModelGraph) -> ValidationResult:
    """Run all validators on a model.

    Args:
        model: The parsed Lattice model.
        graph: The model graph.

    Returns:
        Combined ValidationResult from all validators.
    """
    result = ValidationResult()

    # Run reference integrity first (most fundamental)
    result.merge(check_reference_integrity(model, graph))

    # Run orphan detection
    result.merge(check_orphan_entities(graph))

    # Run state machine validators
    result.merge(check_unreachable_states(graph))
    result.merge(check_terminal_states(graph))

    return result


def validate_model_file(path: str | Path) -> ValidationResult:
    """Load and validate a model file.

    Args:
        path: Path to the YAML model file.

    Returns:
        ValidationResult from all validators.

    Raises:
        SchemaLoadError: If the file cannot be loaded.
        SchemaValidationError: If the model fails schema validation.
    """
    model = parse_model(path)
    graph = build_graph(model)
    return run_validators(model, graph)
