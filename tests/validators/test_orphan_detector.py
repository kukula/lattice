"""Tests for orphan entity detector."""

import pytest

from lattice.schema.loader import parse_model_from_string
from lattice.graph.builder import build_graph
from lattice.validators.orphan_detector import check_orphan_entities


class TestOrphanDetector:
    def test_no_orphans(self, minimal_graph):
        result = check_orphan_entities(minimal_graph)

        assert result.is_valid
        assert len(result.warnings) == 0

    def test_detects_orphan(self):
        yaml = """
entities:
  User:
    relationships:
      - has_many: Post

  Post:
    belongs_to: User

  Orphan:
    attributes:
      - name: data
        type: string
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_orphan_entities(graph)

        assert len(result.warnings) == 1
        assert result.warnings[0].code == "ORPHAN_ENTITY"
        assert result.warnings[0].entity == "Orphan"

    def test_multiple_orphans(self):
        yaml = """
entities:
  Orphan1:
    attributes:
      - name: a
        type: string

  Orphan2:
    attributes:
      - name: b
        type: string
"""
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_orphan_entities(graph)

        assert len(result.warnings) == 2
        orphan_names = {w.entity for w in result.warnings}
        assert orphan_names == {"Orphan1", "Orphan2"}

    def test_entity_with_only_incoming_relationship_not_orphan(self):
        yaml = """
entities:
  User:
    relationships:
      - has_many: Post

  Post:
    attributes:
      - name: title
        type: string
"""
        # Post doesn't declare belongs_to, but User has_many Post
        # So Post should have incoming relationship and not be orphan
        model = parse_model_from_string(yaml)
        graph = build_graph(model)

        result = check_orphan_entities(graph)

        # User has outgoing, Post has incoming - neither is orphan
        assert len(result.warnings) == 0
