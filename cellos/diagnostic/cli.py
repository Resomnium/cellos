"""CLI for the CellOS diagnostic toolkit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cellos.schema.loader import load_cell_from_yaml, load_cell_from_json
from cellos.diagnostic.analyzer import DiagnosticAnalyzer


def main(argv: list[str] | None = None) -> None:
    """Run the CellOS diagnostic CLI."""
    parser = argparse.ArgumentParser(
        prog="cellos-diagnostic",
        description="Analyze organizational cells for AI-readiness",
    )
    parser.add_argument(
        "cell_file",
        help="Path to a cell definition file (YAML or JSON)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args(argv)
    path = Path(args.cell_file)

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    # Load cell
    if path.suffix in (".yml", ".yaml"):
        cell = load_cell_from_yaml(path)
    elif path.suffix == ".json":
        cell = load_cell_from_json(path)
    else:
        print(f"Error: Unsupported file format: {path.suffix}", file=sys.stderr)
        sys.exit(1)

    # Run diagnostic
    analyzer = DiagnosticAnalyzer()
    report = analyzer.analyze(cell)

    # Format output
    if args.format == "markdown":
        output = report.to_markdown()
    else:
        output = report.model_dump_json(indent=2)

    # Write output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Report written to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
