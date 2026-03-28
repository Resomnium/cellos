"""CellOS Demo — Showcases the full framework in action.

This demo:
1. Loads Resomnium's real cell definition from YAML
2. Runs a diagnostic analysis
3. Creates a coordination runtime
4. Demonstrates scope checking, task routing, and escalation
5. Shows the audit trail

Run: python examples/demo.py
"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from cellos.schema.loader import load_cell_from_yaml
from cellos.schema.json_schema import generate_cell_json_schema
from cellos.engine.cell_runtime import CellRuntime, TaskStatus
from cellos.engine.coordinator import Coordinator
from cellos.engine.audit import ActionType
from cellos.diagnostic.analyzer import DiagnosticAnalyzer

console = Console()


def main():
    console.print(Panel.fit(
        "[bold cyan]CellOS Demo[/bold cyan]\n"
        "Open Framework for Human-AI Organizational Coordination\n"
        "https://resomnium.com",
        border_style="cyan",
    ))

    # --- 1. Load a real cell definition ---
    console.print("\n[bold]1. Loading Resomnium's Cell Definition[/bold]\n")

    cell_path = Path(__file__).parent / "resomnium-cell.yaml"
    cell = load_cell_from_yaml(cell_path)

    table = Table(title=f"Cell: {cell.name}", box=box.ROUNDED)
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("ID", cell.id)
    table.add_row("Participants", str(len(cell.participants)))
    table.add_row("Human", str(len(cell.get_human_participants())))
    table.add_row("AI", str(len(cell.get_ai_participants())))
    table.add_row("Roles", str(len(cell.roles)))
    table.add_row("Handoff Protocols", str(len(cell.handoff_protocols)))
    console.print(table)

    # Show participants
    p_table = Table(title="Participants", box=box.SIMPLE)
    p_table.add_column("ID")
    p_table.add_column("Name")
    p_table.add_column("Type")
    p_table.add_column("Role")
    for p in cell.participants:
        p_table.add_row(p.id, p.name, p.participant_type.value, p.role)
    console.print(p_table)

    # --- 2. Run Diagnostic ---
    console.print("\n[bold]2. Running Diagnostic Analysis[/bold]\n")

    analyzer = DiagnosticAnalyzer()
    report = analyzer.analyze(cell)

    console.print(f"  Overall Score: [bold {'green' if report.overall_score >= 70 else 'yellow' if report.overall_score >= 50 else 'red'}]{report.overall_score:.0f}/100[/bold {'green' if report.overall_score >= 70 else 'yellow' if report.overall_score >= 50 else 'red'}]")
    console.print(f"  Findings: {len(report.findings)} ({report.critical_count} critical, {report.high_count} high)")
    console.print(f"  Summary: {report.summary}")

    if report.findings:
        console.print("\n  [bold]Top Findings:[/bold]")
        for f in report.findings[:3]:
            severity_color = {"critical": "red", "high": "yellow", "medium": "cyan", "low": "dim"}.get(f.severity.value, "white")
            console.print(f"    [{severity_color}]{f.severity.value.upper()}[/{severity_color}] {f.title}")

    # --- 3. Coordination Engine ---
    console.print("\n[bold]3. Coordination Engine Demo[/bold]\n")

    runtime = CellRuntime(cell)

    # Scope checking
    console.print("  [bold]Scope Checks:[/bold]")

    checks = [
        ("vox", "search_web for competitor analysis"),
        ("vox", "publish content to Substack"),
        ("scout", "contact_lead at TechCorp"),
        ("zach", "assign_task to Vox"),
        ("corra", "review_output of lead brief"),
    ]

    for participant_id, action in checks:
        result = runtime.check_scope(participant_id, action)
        status = "[green]ALLOWED[/green]" if result.allowed else "[red]DENIED[/red]"
        approval = " [yellow](needs approval)[/yellow]" if result.requires_approval else ""
        console.print(f"    {participant_id} -> {action}: {status}{approval}")
        if not result.allowed:
            console.print(f"      Reason: {result.reason}")

    # Task routing
    console.print("\n  [bold]Task Routing:[/bold]")

    tasks_to_create = [
        "Analyze competitor pricing strategy",
        "Generate lead report for construction vertical",
        "Review quality of latest content draft",
    ]

    for title in tasks_to_create:
        task = runtime.create_task(title)
        routed = runtime.route_task(task.id)
        participant = cell.get_participant(routed.assigned_to) if routed.assigned_to else None
        name = participant.name if participant else "UNASSIGNED"
        console.print(f"    '{title}' -> {name} ({routed.status.value})")

    # Complete a task
    tasks = runtime.get_tasks(status=TaskStatus.ASSIGNED)
    if tasks:
        completed = runtime.complete_task(tasks[0].id, "Analysis complete with 5 key findings")
        console.print(f"\n    Completed: '{completed.title}' -> Result: {completed.result}")

    # --- 4. Audit Trail ---
    console.print("\n[bold]4. Audit Trail[/bold]\n")

    summary = runtime.audit.summary(cell.id)
    a_table = Table(title="Audit Summary", box=box.SIMPLE)
    a_table.add_column("Metric")
    a_table.add_column("Value", justify="right")
    a_table.add_row("Total Actions", str(summary["total_actions"]))
    a_table.add_row("Scope Violations", str(summary["scope_violations"]))
    a_table.add_row("Escalations", str(summary["escalations"]))
    a_table.add_row("Unique Actors", str(summary["unique_actors"]))
    console.print(a_table)

    # Show recent audit entries
    recent = runtime.audit.get_entries(cell_id=cell.id)[-5:]
    if recent:
        console.print("\n  [bold]Recent Audit Entries:[/bold]")
        for entry in recent:
            console.print(f"    [{entry.action.value}] {entry.actor_id} ({entry.actor_role}): {entry.description}")

    # --- 5. Cell Status ---
    console.print("\n[bold]5. Cell Status[/bold]\n")

    status = runtime.get_cell_status()
    s_table = Table(title="Operational Status", box=box.SIMPLE)
    s_table.add_column("Metric")
    s_table.add_column("Value", justify="right")
    s_table.add_row("Total Tasks", str(status["total_tasks"]))
    s_table.add_row("Audit Entries", str(status["audit_entries"]))
    s_table.add_row("Scope Violations", str(status["scope_violations"]))
    s_table.add_row("Escalations", str(status["escalations"]))
    for task_status, count in status.get("task_status", {}).items():
        s_table.add_row(f"  Tasks: {task_status}", str(count))
    console.print(s_table)

    # --- 6. JSON Schema ---
    console.print("\n[bold]6. JSON Schema Export[/bold]\n")

    schema = generate_cell_json_schema()
    lines = schema.split("\n")
    console.print(f"  Generated CellOS JSON Schema: {len(lines)} lines, {len(schema)} bytes")
    console.print(f"  First 3 lines:")
    for line in lines[:3]:
        console.print(f"    {line}")
    console.print("    ...")

    # --- Done ---
    console.print(Panel.fit(
        "[bold green]Demo Complete[/bold green]\n\n"
        "CellOS provides the missing infrastructure for human-AI coordination:\n"
        "  - Formal cell definitions (YAML/JSON Schema)\n"
        "  - Runtime scope enforcement & audit trails\n"
        "  - Diagnostic analysis with actionable recommendations\n\n"
        "Apache 2.0 | https://github.com/resomnium/cellos",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
