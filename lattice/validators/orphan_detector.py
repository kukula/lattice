"""Orphan entity detection validator."""

from ..graph.model_graph import ModelGraph
from .base import ValidationResult


def check_orphan_entities(graph: ModelGraph) -> ValidationResult:
    """Check for entities with no relationships.

    An orphan entity is one that has no relationships to or from other entities.
    This may indicate a missing relationship or an entity that should be removed.

    Args:
        graph: The model graph to check.

    Returns:
        ValidationResult with warnings for orphan entities.
    """
    result = ValidationResult()

    for entity_name in graph.get_entity_names():
        if not graph.has_any_relationships(entity_name):
            result.add_warning(
                code="ORPHAN_ENTITY",
                message=f"Entity '{entity_name}' has no relationships to other entities",
                entity=entity_name,
            )

    return result
