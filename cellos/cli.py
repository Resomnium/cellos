"""Main CLI entry point for CellOS."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cellos.schema.loader import load_cell_from_yaml, load_cell_from_json, validate_cell


def main(argv: list[str] | None = None) -> None:
    """CellOS CLI."""
    parser = argparse.ArgumentParser(
        prog="cellos",
        description="CellOS - Open Framework for Human-AI Organizational Coordination",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a cell definition")
    validate_parser.add_argument("cell_file", help="Path to cell definition (YAML/JSON)")

    # info command
    info_parser = subparsers.add_parser("info", help="Show cell information")
    info_parser.add_argument("cell_file", help="Path to cell definition (YAML/JSON)")

    # diagnose command
    diagnose_parser = subparsers.add_parser("diagnose", help="Run diagnostic analysis")
    diagnose_parser.add_argument("cell_file", help="Path to cell definition (YAML/JSON)")
    diagnose_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    diagnose_parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Load cell
    path = Path(args.cell_file)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    if path.suffix in (".yml", ".yaml"):
        cell = load_cell_from_yaml(path)
    elif path.suffix == ".json":
        cell = load_cell_from_json(path)
    else:
        print(f"Error: Unsupported format: {path.suffix}", file=sys.stderr)
        sys.exit(1)

    if args.command == "validate":
        issues = validate_cell(cell)
        if issues:
            print(f"Validation found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print(f"Cell '{cell.name}' is valid.")

    elif args.command == "info":
        humans = cell.get_human_participants()
        ais = cell.get_ai_participants()
        print(f"Cell: {cell.name} (ID: {cell.id})")
        print(f"Mandate: {cell.mandate}")
        print(f"Roles: {len(cell.roles)}")
        print(f"Participants: {len(cell.participants)} ({len(humans)} human, {len(ais)} AI)")
        print(f"Handoff protocols: {len(cell.handoff_protocols)}")
        print()
        print("Roles:")
        for role in cell.roles:
            steward = f" [{role.steward_role.value}]" if role.steward_role else ""
            print(f"  {role.name}{steward} ({role.participant_type.value})")
            parts = cell.get_participants_for_role(role.name)
            for p in parts:
                print(f"    -> {p.name} ({p.participant_type.value})")

    elif args.command == "diagnose":
        from cellos.diagnostic.analyzer import DiagnosticAnalyzer

        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(cell)

        if args.format == "markdown":
            output = report.to_markdown()
        else:
            output = report.model_dump_json(indent=2)

        if args.output:
            Path(args.output).write_text(output)
            print(f"Report written to: {args.output}")
        else:
            print(output)


if __name__ == "__main__":
    main()
