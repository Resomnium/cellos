"""Tests for the Cell Schema models."""

import json
from pathlib import Path

import pytest
from cellos.schema.json_schema import generate_cell_json_schema
from cellos.schema.models import (
    Cell,
    CellConfig,
    DecisionRight,
    EscalationRule,
    EscalationTrigger,
    HandoffProtocol,
    Participant,
    ParticipantType,
    Role,
    ScopeDefinition,
    StewardRole,
)


def make_complete_cell() -> Cell:
    """Create a complete, valid cell for testing."""
    return Cell(
        id="test-cell",
        name="Test Cell",
        mandate="Testing the Cell Framework",
        roles=[
            Role(
                name="Lead",
                steward_role=StewardRole.CLARITY,
                participant_type=ParticipantType.HUMAN,
                description="Strategic lead",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["decide", "review"]),
                kpis=["decisions_per_week"],
            ),
            Role(
                name="Executor",
                steward_role=StewardRole.EXECUTION,
                participant_type=ParticipantType.AI,
                description="Executes tasks",
                decision_rights=DecisionRight.CONDITIONAL,
                scope=ScopeDefinition(
                    allowed_actions=["execute", "report"],
                    forbidden_actions=["delete", "publish"],
                ),
                accountability_to="Lead",
                escalation_rules=[
                    EscalationRule(
                        trigger=EscalationTrigger.SCOPE_BOUNDARY,
                        target_role="Lead",
                    )
                ],
                kpis=["tasks_completed"],
            ),
            Role(
                name="Narrator",
                steward_role=StewardRole.NARRATIVE,
                participant_type=ParticipantType.AI,
                description="Content creation",
                decision_rights=DecisionRight.ADVISORY,
                scope=ScopeDefinition(allowed_actions=["draft", "analyze"]),
                accountability_to="Lead",
                kpis=["content_quality"],
            ),
            Role(
                name="Connector",
                steward_role=StewardRole.ACCESS,
                participant_type=ParticipantType.AI,
                description="Relationship management",
                decision_rights=DecisionRight.ADVISORY,
                scope=ScopeDefinition(allowed_actions=["track", "suggest"]),
                accountability_to="Lead",
                kpis=["connections_made"],
            ),
            Role(
                name="Auditor",
                steward_role=StewardRole.INTEGRITY,
                participant_type=ParticipantType.AI,
                description="Quality and compliance",
                decision_rights=DecisionRight.ADVISORY,
                scope=ScopeDefinition(allowed_actions=["review", "flag"]),
                accountability_to="Lead",
                kpis=["issues_caught"],
            ),
        ],
        participants=[
            Participant(
                id="human-1",
                name="Alice",
                participant_type=ParticipantType.HUMAN,
                role="Lead",
                capabilities=["strategy", "review"],
            ),
            Participant(
                id="ai-1",
                name="Bot-Exec",
                participant_type=ParticipantType.AI,
                role="Executor",
                capabilities=["execute", "report"],
            ),
            Participant(
                id="ai-2",
                name="Bot-Narrate",
                participant_type=ParticipantType.AI,
                role="Narrator",
                capabilities=["draft", "analyze"],
            ),
            Participant(
                id="ai-3",
                name="Bot-Connect",
                participant_type=ParticipantType.AI,
                role="Connector",
                capabilities=["track", "suggest"],
            ),
            Participant(
                id="ai-4",
                name="Bot-Audit",
                participant_type=ParticipantType.AI,
                role="Auditor",
                capabilities=["review", "flag"],
            ),
        ],
        handoff_protocols=[
            HandoffProtocol(
                from_role="Executor",
                to_role="Lead",
                trigger="task_complete",
                required_context=["result", "confidence"],
            ),
        ],
    )


class TestCellModel:
    def test_create_cell(self):
        cell = make_complete_cell()
        assert cell.id == "test-cell"
        assert cell.name == "Test Cell"
        assert len(cell.roles) == 5
        assert len(cell.participants) == 5

    def test_get_role(self):
        cell = make_complete_cell()
        role = cell.get_role("Lead")
        assert role is not None
        assert role.steward_role == StewardRole.CLARITY

    def test_get_participant(self):
        cell = make_complete_cell()
        p = cell.get_participant("ai-1")
        assert p is not None
        assert p.name == "Bot-Exec"

    def test_get_participants_for_role(self):
        cell = make_complete_cell()
        parts = cell.get_participants_for_role("Lead")
        assert len(parts) == 1
        assert parts[0].id == "human-1"

    def test_get_human_participants(self):
        cell = make_complete_cell()
        humans = cell.get_human_participants()
        assert len(humans) == 1

    def test_get_ai_participants(self):
        cell = make_complete_cell()
        ais = cell.get_ai_participants()
        assert len(ais) == 4

    def test_get_steward(self):
        cell = make_complete_cell()
        clarity = cell.get_steward(StewardRole.CLARITY)
        assert clarity is not None
        assert clarity.name == "Lead"

    def test_validate_completeness_valid(self):
        cell = make_complete_cell()
        issues = cell.validate_completeness()
        assert len(issues) == 0

    def test_validate_missing_steward(self):
        cell = make_complete_cell()
        cell.roles = [r for r in cell.roles if r.steward_role != StewardRole.INTEGRITY]
        issues = cell.validate_completeness()
        assert any("integrity" in i.lower() for i in issues)

    def test_validate_no_humans_required(self):
        cell = make_complete_cell()
        cell.participants = [p for p in cell.participants if p.participant_type != ParticipantType.HUMAN]
        issues = cell.validate_completeness()
        assert any("human" in i.lower() for i in issues)


class TestStewardRole:
    def test_governance_is_deprecated_alias_for_integrity(self):
        with pytest.warns(FutureWarning, match="integrity"):
            role = Role(name="Steward", steward_role="governance")
        assert role.steward_role is StewardRole.INTEGRITY
        assert role.model_dump(mode="json")["steward_role"] == "integrity"

    def test_published_schema_matches_models(self):
        schema_path = Path(__file__).parent.parent / "cellos" / "schema" / "cell-schema-v0.2.0.json"
        published = json.loads(schema_path.read_text(encoding="utf-8"))
        assert published == json.loads(generate_cell_json_schema())
        assert published["$defs"]["StewardRole"]["enum"] == [
            "clarity", "execution", "narrative", "access", "integrity",
        ]


class TestScopeDefinition:
    def test_scope_with_allowed_actions(self):
        scope = ScopeDefinition(
            allowed_actions=["read", "write"],
            forbidden_actions=["delete"],
        )
        assert "read" in scope.allowed_actions
        assert "delete" in scope.forbidden_actions

    def test_scope_with_resource_limits(self):
        scope = ScopeDefinition(resource_limits={"api_calls": 100, "budget_eur": 500})
        assert scope.resource_limits["api_calls"] == 100
