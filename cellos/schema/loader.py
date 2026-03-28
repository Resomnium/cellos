"""Load cell definitions from YAML files and validate them."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from cellos.schema.models import Cell


def load_cell_from_yaml(path: str | Path) -> Cell:
    """Load a cell definition from a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        A validated Cell instance.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the YAML is invalid or doesn't match the schema.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Cell definition not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping, got {type(data).__name__}")

    return Cell(**data)


def load_cell_from_json(path: str | Path) -> Cell:
    """Load a cell definition from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Cell definition not found: {path}")

    with open(path) as f:
        data = json.load(f)

    return Cell(**data)


def load_cell_from_dict(data: dict) -> Cell:
    """Load a cell definition from a dictionary."""
    return Cell(**data)


def save_cell_to_yaml(cell: Cell, path: str | Path) -> None:
    """Save a cell definition to a YAML file."""
    path = Path(path)
    data = cell.model_dump(mode="json", exclude_none=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def save_cell_to_json(cell: Cell, path: str | Path, indent: int = 2) -> None:
    """Save a cell definition to a JSON file."""
    path = Path(path)
    data = cell.model_dump(mode="json", exclude_none=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def validate_cell(cell: Cell) -> list[str]:
    """Validate a cell definition and return any issues found."""
    return cell.validate_completeness()
