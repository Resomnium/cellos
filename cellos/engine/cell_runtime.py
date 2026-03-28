"""Cell Runtime - manages the lifecycle and operations of a single cell."""

from __future__ import annotations

from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field

from cellos.schema.models import (
    Cell,
    DecisionRight,
    EscalationTrigger,
    Participant,
    ParticipantType,
    Role,
)
from cellos.engine.audit import ActionType, AuditLog


class TaskStatus(str, Enum):
    """Status of a task within a cell."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AWAITING_HANDOFF = "awaiting_handoff"
    AWAITING_APPROVAL = "awaiting_approval"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """A unit of work within a cell."""

    id: str
    title: str
    description: str = ""
    assigned_to: str | None = Field(default=None, description="Participant ID")
    assigned_role: str | None = Field(default=None, description="Role name")
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    result: str | None = None
    context: dict = Field(default_factory=dict)
    requires_approval_from: str | None = Field(
        default=None,
        description="Role that must approve before completion",
    )


class ScopeCheckResult(BaseModel):
    """Result of checking whether an action is within a participant's scope."""

    allowed: bool
    reason: str
    requires_approval: bool = False
    approval_from: str | None = None


class CellRuntime:
    """Manages the lifecycle and operations of a single cell.

    Handles task assignment, scope checking, escalation, and handoffs.
    """

    def __init__(self, cell: Cell, audit_log: AuditLog | None = None) -> None:
        self.cell = cell
        self.audit = audit_log or AuditLog()
        self._tasks: dict[str, Task] = {}
        self._task_counter = 0

    def check_scope(self, participant_id: str, action: str) -> ScopeCheckResult:
        """Check if an action is within a participant's defined scope.

        Args:
            participant_id: ID of the participant attempting the action.
            action: Description of the action being attempted.

        Returns:
            ScopeCheckResult indicating whether the action is allowed.
        """
        participant = self.cell.get_participant(participant_id)
        if not participant:
            return ScopeCheckResult(allowed=False, reason=f"Unknown participant: {participant_id}")

        role = self.cell.get_role(participant.role)
        if not role:
            return ScopeCheckResult(
                allowed=False, reason=f"Participant has invalid role: {participant.role}"
            )

        # Check forbidden actions first
        for forbidden in role.scope.forbidden_actions:
            if forbidden.lower() in action.lower():
                self.audit.log(
                    cell_id=self.cell.id,
                    action=ActionType.SCOPE_VIOLATION,
                    actor_id=participant_id,
                    actor_role=participant.role,
                    description=f"Attempted forbidden action: {action}",
                    scope_check_passed=False,
                )
                return ScopeCheckResult(
                    allowed=False,
                    reason=f"Action '{action}' is explicitly forbidden for role '{role.name}'",
                )

        # Check if action requires approval
        for requires_approval in role.scope.requires_approval_for:
            if requires_approval.lower() in action.lower():
                approval_from = role.accountability_to or "governance"
                self.audit.log(
                    cell_id=self.cell.id,
                    action=ActionType.SCOPE_CHECK,
                    actor_id=participant_id,
                    actor_role=participant.role,
                    description=f"Action requires approval: {action}",
                    scope_check_passed=True,
                    context={"requires_approval_from": approval_from},
                )
                return ScopeCheckResult(
                    allowed=True,
                    reason=f"Action allowed but requires approval from '{approval_from}'",
                    requires_approval=True,
                    approval_from=approval_from,
                )

        # Check allowed actions (if specified, action must match)
        if role.scope.allowed_actions:
            for allowed in role.scope.allowed_actions:
                if allowed.lower() in action.lower():
                    self.audit.log(
                        cell_id=self.cell.id,
                        action=ActionType.SCOPE_CHECK,
                        actor_id=participant_id,
                        actor_role=participant.role,
                        description=f"Action within scope: {action}",
                        scope_check_passed=True,
                    )
                    return ScopeCheckResult(allowed=True, reason="Action within defined scope")

            # Action not in allowed list
            self.audit.log(
                cell_id=self.cell.id,
                action=ActionType.SCOPE_CHECK,
                actor_id=participant_id,
                actor_role=participant.role,
                description=f"Action not in allowed list: {action}",
                scope_check_passed=False,
            )
            return ScopeCheckResult(
                allowed=False,
                reason=f"Action '{action}' not in allowed actions for role '{role.name}'",
            )

        # No explicit scope defined - allow by default
        self.audit.log(
            cell_id=self.cell.id,
            action=ActionType.SCOPE_CHECK,
            actor_id=participant_id,
            actor_role=participant.role,
            description=f"Action allowed (no scope restrictions): {action}",
            scope_check_passed=True,
        )
        return ScopeCheckResult(allowed=True, reason="No scope restrictions defined")

    def create_task(
        self,
        title: str,
        description: str = "",
        creator_id: str = "system",
        context: dict | None = None,
    ) -> Task:
        """Create a new task in the cell."""
        self._task_counter += 1
        task_id = f"task-{self._task_counter:04d}"

        task = Task(
            id=task_id,
            title=title,
            description=description,
            context=context or {},
        )
        self._tasks[task_id] = task

        self.audit.log(
            cell_id=self.cell.id,
            action=ActionType.TASK_CREATED,
            actor_id=creator_id,
            actor_role="system",
            target_id=task_id,
            description=f"Created task: {title}",
        )
        return task

    def assign_task(self, task_id: str, participant_id: str) -> Task:
        """Assign a task to a specific participant."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        participant = self.cell.get_participant(participant_id)
        if not participant:
            raise ValueError(f"Participant not found: {participant_id}")

        task.assigned_to = participant_id
        task.assigned_role = participant.role
        task.status = TaskStatus.ASSIGNED

        self.audit.log(
            cell_id=self.cell.id,
            action=ActionType.TASK_ASSIGNED,
            actor_id="system",
            actor_role="system",
            target_id=participant_id,
            description=f"Assigned task '{task.title}' to {participant.name} ({participant.role})",
            context={"task_id": task_id},
        )
        return task

    def route_task(self, task_id: str) -> Task:
        """Automatically route a task to the most appropriate participant.

        Routing considers: role relevance, participant type, availability,
        and decision rights.
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Find best match based on task context
        best_participant: Participant | None = None
        best_score = -1

        for participant in self.cell.participants:
            role = self.cell.get_role(participant.role)
            if not role:
                continue

            score = 0

            # Check capability match
            for cap in participant.capabilities:
                if cap.lower() in task.title.lower() or cap.lower() in task.description.lower():
                    score += 3

            # Prefer participants with higher decision rights for complex tasks
            if role.decision_rights == DecisionRight.FULL:
                score += 2
            elif role.decision_rights == DecisionRight.CONDITIONAL:
                score += 1

            # Prefer available participants
            if participant.availability == "always":
                score += 1

            if score > best_score:
                best_score = score
                best_participant = participant

        if best_participant:
            return self.assign_task(task_id, best_participant.id)

        # No suitable participant found - escalate
        task.status = TaskStatus.ESCALATED
        self.audit.log(
            cell_id=self.cell.id,
            action=ActionType.ESCALATION,
            actor_id="system",
            actor_role="system",
            target_id=task_id,
            description=f"Could not route task '{task.title}' - no suitable participant found",
        )
        return task

    def complete_task(self, task_id: str, result: str = "") -> Task:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.result = result

        self.audit.log(
            cell_id=self.cell.id,
            action=ActionType.TASK_COMPLETED,
            actor_id=task.assigned_to or "system",
            actor_role=task.assigned_role or "system",
            target_id=task_id,
            description=f"Completed task: {task.title}",
            context={"result": result},
        )
        return task

    def escalate(self, task_id: str, trigger: EscalationTrigger, reason: str = "") -> Task:
        """Escalate a task based on a trigger condition."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.status = TaskStatus.ESCALATED

        # Find escalation target
        target_role = None
        if task.assigned_role:
            role = self.cell.get_role(task.assigned_role)
            if role:
                for rule in role.escalation_rules:
                    if rule.trigger == trigger:
                        target_role = rule.target_role
                        break
                if not target_role and role.accountability_to:
                    target_role = role.accountability_to

        self.audit.log(
            cell_id=self.cell.id,
            action=ActionType.ESCALATION,
            actor_id=task.assigned_to or "system",
            actor_role=task.assigned_role or "system",
            target_id=task_id,
            description=f"Escalated: {reason or trigger.value}",
            context={
                "trigger": trigger.value,
                "reason": reason,
                "target_role": target_role,
            },
        )
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """Get all tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_cell_status(self) -> dict:
        """Get a summary of the cell's current operational status."""
        tasks = list(self._tasks.values())
        status_counts: dict[str, int] = {}
        for t in tasks:
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1

        return {
            "cell_id": self.cell.id,
            "cell_name": self.cell.name,
            "participants": len(self.cell.participants),
            "human_participants": len(self.cell.get_human_participants()),
            "ai_participants": len(self.cell.get_ai_participants()),
            "total_tasks": len(tasks),
            "task_status": status_counts,
            "audit_entries": self.audit.size,
            "scope_violations": len(self.audit.get_scope_violations(self.cell.id)),
            "escalations": len(self.audit.get_escalations(self.cell.id)),
        }
