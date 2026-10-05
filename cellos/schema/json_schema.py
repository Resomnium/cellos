"""Generate JSON Schema from CellOS models.

Produces a formal JSON Schema specification that can be used
to validate cell definitions independently of the Python library.
This is the "open specification" component of CellOS.
"""

from __future__ import annotations

import json
from pathlib import Path

from cellos.schema.models import Cell


def generate_cell_json_schema(indent: int = 2) -> str:
    """Generate the JSON Schema for a Cell definition.

    Returns the JSON Schema as a formatted string.
    """
    schema = Cell.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://resomnium.com/schemas/cellos/cell-v0.3.0.json"
    schema["title"] = "CellOS Cell Definition"
    schema["description"] = (
        "Schema for defining an organizational cell where humans and AI agents "
        "collaborate with explicit roles, accountability, and coordination protocols. "
        "Part of the CellOS open framework (https://github.com/resomnium/cellos)."
    )
    return json.dumps(schema, indent=indent, ensure_ascii=False)


def export_cell_json_schema(path: str | Path, indent: int = 2) -> None:
    """Export the Cell JSON Schema to a file."""
    path = Path(path)
    path.write_text(generate_cell_json_schema(indent))


if __name__ == "__main__":
    print(generate_cell_json_schema())
