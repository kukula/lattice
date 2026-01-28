"""YAML loading and parsing for Lattice models."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from .errors import SchemaLoadError, SchemaValidationError
from .models import LatticeModel


def load_yaml(path: str | Path) -> dict:
    """Load a YAML file and return the raw data.

    Args:
        path: Path to the YAML file.

    Returns:
        The parsed YAML data as a dictionary.

    Raises:
        SchemaLoadError: If the file cannot be read or parsed.
    """
    path = Path(path)

    if not path.exists():
        raise SchemaLoadError(f"File not found: {path}", str(path))

    if not path.is_file():
        raise SchemaLoadError(f"Not a file: {path}", str(path))

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SchemaLoadError(f"Invalid YAML: {e}", str(path)) from e
    except OSError as e:
        raise SchemaLoadError(f"Cannot read file: {e}", str(path)) from e

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise SchemaLoadError(
            f"Expected YAML mapping at root, got {type(data).__name__}", str(path)
        )

    return data


def parse_model(path: str | Path) -> LatticeModel:
    """Load and parse a YAML file into a LatticeModel.

    Args:
        path: Path to the YAML file.

    Returns:
        The parsed LatticeModel.

    Raises:
        SchemaLoadError: If the file cannot be read or parsed.
        SchemaValidationError: If the data fails validation.
    """
    data = load_yaml(path)
    return _parse_model_data(data)


def parse_model_from_string(yaml_string: str) -> LatticeModel:
    """Parse a YAML string into a LatticeModel.

    Args:
        yaml_string: The YAML content as a string.

    Returns:
        The parsed LatticeModel.

    Raises:
        SchemaLoadError: If the YAML cannot be parsed.
        SchemaValidationError: If the data fails validation.
    """
    try:
        data = yaml.safe_load(yaml_string)
    except yaml.YAMLError as e:
        raise SchemaLoadError(f"Invalid YAML: {e}") from e

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise SchemaLoadError(f"Expected YAML mapping at root, got {type(data).__name__}")

    return _parse_model_data(data)


def _parse_model_data(data: dict) -> LatticeModel:
    """Parse raw data into a LatticeModel.

    Args:
        data: The raw YAML data.

    Returns:
        The parsed LatticeModel.

    Raises:
        SchemaValidationError: If the data fails validation.
    """
    try:
        return LatticeModel.model_validate(data)
    except ValidationError as e:
        errors = [
            {
                "loc": ".".join(str(x) for x in err["loc"]),
                "msg": err["msg"],
                "type": err["type"],
            }
            for err in e.errors()
        ]
        raise SchemaValidationError(
            f"Schema validation failed with {len(errors)} error(s)", errors
        ) from e
