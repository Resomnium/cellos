"""Coordinator - manages multiple cells and inter-cell coordination."""

from __future__ import annotations

from cellos.schema.models import Cell, HandoffProtocol
from cellos.engine.audit import ActionType, AuditLog
from cellos.engine.cell_runtime import CellRuntime, Task


class Coordinator:
    """Manages multiple cells and coordinates work between them.

    The Coordinator is the top-level orchestrator that handles:
    - Cell registration and lifecycle
    - Inter-cell task routing
    - Cross-cell handoffs
    - Organization-wide audit trail
    """

    def __init__(self) -> None:
        self.audit = AuditLog()
        self._runtimes: dict[str, CellRuntime] = {}

    def register_cell(self, cell: Cell) -> CellRuntime:
        """Register a cell and create its runtime."""
        runtime = CellRuntime(cell=cell, audit_log=self.audit)
        self._runtimes[cell.id] = runtime
        return runtime

    def get_runtime(self, cell_id: str) -> CellRuntime | None:
        """Get the runtime for a specific cell."""
        return self._runtimes.get(cell_id)

    def get_all_runtimes(self) -> list[CellRuntime]:
        """Get all registered cell runtimes."""
        return list(self._runtimes.values())

    def handoff_task(
        self,
        task: Task,
        from_cell_id: str,
        to_cell_id: str,
        context: dict | None = None,
    ) -> Task:
        """Hand off a task from one cell to another.

        Args:
            task: The task to hand off.
            from_cell_id: Source cell ID.
            to_cell_id: Target cell ID.
            context: Additional context to pass with the handoff.
        """
        from_runtime = self._runtimes.get(from_cell_id)
        to_runtime = self._runtimes.get(to_cell_id)

        if not from_runtime:
            raise ValueError(f"Source cell not found: {from_cell_id}")
        if not to_runtime:
            raise ValueError(f"Target cell not found: {to_cell_id}")

        # Create a new task in the target cell
        new_task = to_runtime.create_task(
            title=task.title,
            description=task.description,
            creator_id=f"handoff-from-{from_cell_id}",
            context={**(task.context or {}), **(context or {}), "source_cell": from_cell_id},
        )

        # Log the handoff
        self.audit.log(
            cell_id=from_cell_id,
            action=ActionType.HANDOFF,
            actor_id=task.assigned_to or "system",
            actor_role=task.assigned_role or "system",
            target_id=to_cell_id,
            description=f"Handed off task '{task.title}' to cell '{to_runtime.cell.name}'",
            context={
                "source_task_id": task.id,
                "target_task_id": new_task.id,
                "target_cell": to_cell_id,
            },
        )

        # Route the task in the target cell
        to_runtime.route_task(new_task.id)

        return new_task

    def get_organization_status(self) -> dict:
        """Get a summary of the entire organization's status."""
        cell_statuses = []
        total_tasks = 0
        total_violations = 0
        total_escalations = 0

        for runtime in self._runtimes.values():
            status = runtime.get_cell_status()
            cell_statuses.append(status)
            total_tasks += status["total_tasks"]
            total_violations += status["scope_violations"]
            total_escalations += status["escalations"]

        return {
            "total_cells": len(self._runtimes),
            "total_tasks": total_tasks,
            "total_scope_violations": total_violations,
            "total_escalations": total_escalations,
            "total_audit_entries": self.audit.size,
            "cells": cell_statuses,
        }
