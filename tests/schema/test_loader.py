"""Tests for schema loader."""

import pytest
from pathlib import Path

from lattice.schema.loader import (
    load_yaml,
    parse_model,
    parse_model_from_string,
)
from lattice.schema.errors import SchemaLoadError, SchemaValidationError


class TestLoadYaml:
    def test_load_valid_yaml(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\nlist:\n  - item1\n  - item2")

        data = load_yaml(yaml_file)
        assert data["key"] == "value"
        assert data["list"] == ["item1", "item2"]

    def test_file_not_found(self):
        with pytest.raises(SchemaLoadError) as exc_info:
            load_yaml("/nonexistent/path.yaml")
        assert "not found" in str(exc_info.value).lower()

    def test_invalid_yaml(self, tmp_path):
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("key: [unclosed bracket")

        with pytest.raises(SchemaLoadError) as exc_info:
            load_yaml(yaml_file)
        assert "Invalid YAML" in str(exc_info.value)

    def test_empty_file_returns_empty_dict(self, tmp_path):
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        data = load_yaml(yaml_file)
        assert data == {}

    def test_non_mapping_at_root(self, tmp_path):
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text("- item1\n- item2")

        with pytest.raises(SchemaLoadError) as exc_info:
            load_yaml(yaml_file)
        assert "mapping" in str(exc_info.value).lower()


class TestParseModelFromString:
    def test_parse_minimal_model(self):
        yaml_str = """
entities:
  User:
    attributes:
      - name: email
        type: string
"""
        model = parse_model_from_string(yaml_str)
        assert "User" in model.entities
        assert model.entities["User"].attributes[0].name == "email"

    def test_parse_empty_model(self):
        model = parse_model_from_string("")
        assert len(model.entities) == 0

    def test_parse_model_with_states(self):
        yaml_str = """
entities:
  Task:
    states:
      - name: pending
        initial: true
      - name: done
        terminal: true
    transitions:
      - from: pending
        to: done
"""
        model = parse_model_from_string(yaml_str)
        task = model.entities["Task"]
        assert len(task.states) == 2
        assert len(task.transitions) == 1

    def test_invalid_yaml_string(self):
        with pytest.raises(SchemaLoadError):
            parse_model_from_string("invalid: [yaml")


class TestParseModel:
    def test_parse_example_file(self, examples_dir):
        model = parse_model(examples_dir / "minimal_valid.yaml")
        assert "User" in model.entities
        assert "Post" in model.entities

    def test_parse_order_lifecycle(self, examples_dir):
        model = parse_model(examples_dir / "order_lifecycle.yaml")
        assert "Order" in model.entities
        assert "Customer" in model.entities

        order = model.entities["Order"]
        assert len(order.states) > 0
        assert len(order.transitions) > 0
