"""Tests for the Coordination Engine."""

import pytest
from cellos.schema.models import (
    Cell,
    DecisionRight,
    EscalationRule,
    EscalationTrigger,
    Participant,
    ParticipantType,
    Role,
    ScopeDefinition,
    StewardRole,
)
from cellos.engine.cell_runtime import CellRuntime, TaskStatus
from cellos.engine.coordinator import Coordinator
from cellos.engine.audit import AuditLog, ActionType


def make_test_cell() -> Cell:
    """Create a simple test cell."""
    return Cell(
        id="test",
        name="Test Cell",
        roles=[
            Role(
                name="Boss",
                steward_role=StewardRole.CLARITY,
                participant_type=ParticipantType.HUMAN,
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["approve", "review", "decide"]),
            ),
            Role(
                name="Worker",
                steward_role=StewardRole.EXECUTION,
                participant_type=ParticipantType.AI,
                decision_rights=DecisionRight.CONDITIONAL,
                scope=ScopeDefinition(
                    allowed_actions=["execute", "report", "analyze"],
                    forbidden_actions=["delete", "publish", "purchase"],
                    requires_approval_for=["external_communication"],
                ),
                accountability_to="Boss",
                escalation_rules=[
                    EscalationRule(
                        trigger=EscalationTrigger.SCOPE_BOUNDARY,
                        target_role="Boss",
                    ),
                    EscalationRule(
                        trigger=EscalationTrigger.CONFIDENCE_LOW,
                        target_role="Boss",
                        threshold=0.6,
                    ),
                ],
            ),
        ],
        participants=[
            Participant(
                id="human-1",
                name="Alice",
                participant_type=ParticipantType.HUMAN,
                role="Boss",
                capabilities=["strategy", "approval"],
                availability="business_hours",
            ),
            Participant(
                id="bot-1",
                name="WorkerBot",
                participant_type=ParticipantType.AI,
                role="Worker",
                capabilities=["execute", "analyze", "report"],
                availability="always",
            ),
        ],
    )


class TestCellRuntime:
    def test_create_task(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        task = runtime.create_task("Test task", "A test task")
        assert task.id == "task-0001"
        assert task.status == TaskStatus.PENDING

    def test_assign_task(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        task = runtime.create_task("Test task")
        assigned = runtime.assign_task(task.id, "bot-1")
        assert assigned.assigned_to == "bot-1"
        assert assigned.status == TaskStatus.ASSIGNED

    def test_route_task(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        task = runtime.create_task("Execute analysis report")
        routed = runtime.route_task(task.id)
        assert routed.assigned_to is not None
        assert routed.status == TaskStatus.ASSIGNED

    def test_complete_task(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        task = runtime.create_task("Test task")
        runtime.assign_task(task.id, "bot-1")
        completed = runtime.complete_task(task.id, "Done successfully")
        assert completed.status == TaskStatus.COMPLETED
        assert completed.result == "Done successfully"

    def test_scope_check_allowed(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        result = runtime.check_scope("bot-1", "execute task")
        assert result.allowed is True

    def test_scope_check_forbidden(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        result = runtime.check_scope("bot-1", "delete records")
        assert result.allowed is False
        assert "forbidden" in result.reason.lower()

    def test_scope_check_requires_approval(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        result = runtime.check_scope("bot-1", "external_communication to client")
        assert result.allowed is True
        assert result.requires_approval is True

    def test_scope_check_not_in_allowed(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        result = runtime.check_scope("bot-1", "send_invoice")
        assert result.allowed is False

    def test_escalation(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        task = runtime.create_task("Complex task")
        runtime.assign_task(task.id, "bot-1")
        escalated = runtime.escalate(task.id, EscalationTrigger.CONFIDENCE_LOW, "Not sure about this")
        assert escalated.status == TaskStatus.ESCALATED

    def test_get_cell_status(self):
        cell = make_test_cell()
        runtime = CellRuntime(cell)
        runtime.create_task("Task 1")
        runtime.create_task("Task 2")
        status = runtime.get_cell_status()
        assert status["total_tasks"] == 2
        assert status["human_participants"] == 1
        assert status["ai_participants"] == 1


class TestAuditLog:
    def test_log_entry(self):
        audit = AuditLog()
        entry = audit.log(
            cell_id="test",
            action=ActionType.TASK_CREATED,
            actor_id="system",
            actor_role="system",
            description="Created a task",
        )
        assert entry.cell_id == "test"
        assert audit.size == 1

    def test_query_by_action(self):
        audit = AuditLog()
        audit.log("test", ActionType.TASK_CREATED, "sys", "system")
        audit.log("test", ActionType.SCOPE_VIOLATION, "bot", "worker")
        audit.log("test", ActionType.TASK_COMPLETED, "bot", "worker")

        violations = audit.get_scope_violations()
        assert len(violations) == 1

    def test_summary(self):
        audit = AuditLog()
        audit.log("cell-1", ActionType.TASK_CREATED, "sys", "system")
        audit.log("cell-1", ActionType.TASK_ASSIGNED, "sys", "system")
        audit.log("cell-1", ActionType.SCOPE_VIOLATION, "bot", "worker")

        summary = audit.summary("cell-1")
        assert summary["total_actions"] == 3
        assert summary["scope_violations"] == 1


class TestCoordinator:
    def test_register_cells(self):
        coord = Coordinator()
        cell1 = make_test_cell()
        cell2 = Cell(
            id="cell-2",
            name="Cell 2",
            roles=[
                Role(
                    name="Analyst",
                    participant_type=ParticipantType.AI,
                    scope=ScopeDefinition(allowed_actions=["analyze"]),
                ),
            ],
            participants=[
                Participant(
                    id="bot-2",
                    name="AnalystBot",
                    participant_type=ParticipantType.AI,
                    role="Analyst",
                    capabilities=["analyze"],
                ),
            ],
        )
        coord.register_cell(cell1)
        coord.register_cell(cell2)
        assert len(coord.get_all_runtimes()) == 2

    def test_organization_status(self):
        coord = Coordinator()
        coord.register_cell(make_test_cell())
        runtime = coord.get_runtime("test")
        runtime.create_task("Task 1")

        status = coord.get_organization_status()
        assert status["total_cells"] == 1
        assert status["total_tasks"] == 1
