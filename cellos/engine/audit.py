"""Audit logging for cell operations.

Every action within a cell is logged with full context for accountability.
The audit trail captures who did what, under what authority, and what the outcome was.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of auditable actions within a cell."""

    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    HANDOFF = "handoff"
    ESCALATION = "escalation"
    DECISION = "decision"
    SCOPE_CHECK = "scope_check"
    SCOPE_VIOLATION = "scope_violation"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"


class AuditEntry(BaseModel):
    """A single audit log entry."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cell_id: str
    action: ActionType
    actor_id: str = Field(description="ID of the participant who performed the action")
    actor_role: str = Field(description="Role of the actor at time of action")
    target_id: str | None = Field(default=None, description="ID of the target participant/task")
    description: str = ""
    context: dict = Field(default_factory=dict, description="Additional context for the action")
    scope_check_passed: bool | None = Field(
        default=None,
        description="Whether the action was within the actor's scope",
    )
    accountable_to: str | None = Field(
        default=None,
        description="Role that is ultimately accountable for this action",
    )


class AuditLog:
    """In-memory audit log for cell operations.

    Provides append-only logging with query capabilities.
    In production, this would be backed by a persistent store.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def log(
        self,
        cell_id: str,
        action: ActionType,
        actor_id: str,
        actor_role: str,
        target_id: str | None = None,
        description: str = "",
        context: dict | None = None,
        scope_check_passed: bool | None = None,
        accountable_to: str | None = None,
    ) -> AuditEntry:
        """Record an action in the audit log."""
        entry = AuditEntry(
            cell_id=cell_id,
            action=action,
            actor_id=actor_id,
            actor_role=actor_role,
            target_id=target_id,
            description=description,
            context=context or {},
            scope_check_passed=scope_check_passed,
            accountable_to=accountable_to,
        )
        self._entries.append(entry)
        return entry

    def get_entries(
        self,
        cell_id: str | None = None,
        actor_id: str | None = None,
        action: ActionType | None = None,
        since: datetime | None = None,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters."""
        results = self._entries
        if cell_id:
            results = [e for e in results if e.cell_id == cell_id]
        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]
        if action:
            results = [e for e in results if e.action == action]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results

    def get_scope_violations(self, cell_id: str | None = None) -> list[AuditEntry]:
        """Get all scope violations, optionally filtered by cell."""
        return self.get_entries(cell_id=cell_id, action=ActionType.SCOPE_VIOLATION)

    def get_escalations(self, cell_id: str | None = None) -> list[AuditEntry]:
        """Get all escalations, optionally filtered by cell."""
        return self.get_entries(cell_id=cell_id, action=ActionType.ESCALATION)

    def get_accountability_chain(self, entry: AuditEntry) -> list[AuditEntry]:
        """Trace the accountability chain for a specific action.

        Returns all related entries that form the decision/approval chain.
        """
        chain = [entry]
        if entry.target_id:
            related = [
                e
                for e in self._entries
                if e.actor_id == entry.target_id and e.cell_id == entry.cell_id
            ]
            chain.extend(related)
        return sorted(chain, key=lambda e: e.timestamp)

    @property
    def size(self) -> int:
        """Number of entries in the log."""
        return len(self._entries)

    def summary(self, cell_id: str) -> dict:
        """Generate a summary of cell activity."""
        entries = self.get_entries(cell_id=cell_id)
        action_counts: dict[str, int] = {}
        for e in entries:
            action_counts[e.action.value] = action_counts.get(e.action.value, 0) + 1

        violations = self.get_scope_violations(cell_id)
        escalations = self.get_escalations(cell_id)

        return {
            "cell_id": cell_id,
            "total_actions": len(entries),
            "action_breakdown": action_counts,
            "scope_violations": len(violations),
            "escalations": len(escalations),
            "unique_actors": len({e.actor_id for e in entries}),
        }
