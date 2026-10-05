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
    """Create a complete, valid cell for testing.

    Five human stewards in a flat ring, each AI agent working beneath one of them.
    """
    return Cell(
        id="test-cell",
        name="Test Cell",
        mandate="Testing the Cell Framework",
        roles=[
            Role(
                name="Clarity Steward",
                steward_role=StewardRole.CLARITY,
                participant_type=ParticipantType.HUMAN,
                description="Owns direction and scope",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["decide", "review"]),
                kpis=["decisions_per_week"],
            ),
            Role(
                name="Execution Steward",
                steward_role=StewardRole.EXECUTION,
                participant_type=ParticipantType.HUMAN,
                description="Owns delivery",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["deliver", "review"]),
                kpis=["on_time_delivery"],
            ),
            Role(
                name="Narrative Steward",
                steward_role=StewardRole.NARRATIVE,
                participant_type=ParticipantType.HUMAN,
                description="Owns the story",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["publish", "review"]),
                kpis=["content_quality"],
            ),
            Role(
                name="Access Steward",
                steward_role=StewardRole.ACCESS,
                participant_type=ParticipantType.HUMAN,
                description="Owns relationships",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["engage", "review"]),
                kpis=["connections_made"],
            ),
            Role(
                name="Integrity Steward",
                steward_role=StewardRole.INTEGRITY,
                participant_type=ParticipantType.HUMAN,
                description="Owns trust",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["audit", "review"]),
                kpis=["issues_caught"],
            ),
            Role(
                name="Executor",
                participant_type=ParticipantType.AI,
                description="Executes tasks",
                decision_rights=DecisionRight.CONDITIONAL,
                scope=ScopeDefinition(
                    allowed_actions=["execute", "report"],
                    forbidden_actions=["delete", "publish"],
                ),
                accountability_to="Execution Steward",
                escalation_rules=[
                    EscalationRule(
                        trigger=EscalationTrigger.SCOPE_BOUNDARY,
                        target_role="Execution Steward",
                    )
                ],
                kpis=["tasks_completed"],
            ),
            Role(
                name="Narrator",
                participant_type=ParticipantType.AI,
                description="Drafts content",
                decision_rights=DecisionRight.ADVISORY,
                scope=ScopeDefinition(allowed_actions=["draft", "analyze"]),
                accountability_to="Narrative Steward",
                kpis=["drafts_accepted"],
            ),
        ],
        participants=[
            Participant(
                id="human-1",
                name="Alice",
                participant_type=ParticipantType.HUMAN,
                role="Clarity Steward",
                capabilities=["strategy", "review"],
            ),
            Participant(
                id="human-2",
                name="Bilal",
                participant_type=ParticipantType.HUMAN,
                role="Execution Steward",
                capabilities=["delivery"],
            ),
            Participant(
                id="human-3",
                name="Chen",
                participant_type=ParticipantType.HUMAN,
                role="Narrative Steward",
                capabilities=["writing"],
            ),
            Participant(
                id="human-4",
                name="Dara",
                participant_type=ParticipantType.HUMAN,
                role="Access Steward",
                capabilities=["partnerships"],
            ),
            Participant(
                id="human-5",
                name="Emeka",
                participant_type=ParticipantType.HUMAN,
                role="Integrity Steward",
                capabilities=["audit"],
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
        ],
        handoff_protocols=[
            HandoffProtocol(
                from_role="Executor",
                to_role="Execution Steward",
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
        assert len(cell.roles) == 7
        assert len(cell.participants) == 7

    def test_get_role(self):
        cell = make_complete_cell()
        role = cell.get_role("Clarity Steward")
        assert role is not None
        assert role.steward_role == StewardRole.CLARITY

    def test_get_participant(self):
        cell = make_complete_cell()
        p = cell.get_participant("ai-1")
        assert p is not None
        assert p.name == "Bot-Exec"

    def test_get_participants_for_role(self):
        cell = make_complete_cell()
        parts = cell.get_participants_for_role("Clarity Steward")
        assert len(parts) == 1
        assert parts[0].id == "human-1"

    def test_get_human_participants(self):
        cell = make_complete_cell()
        humans = cell.get_human_participants()
        assert len(humans) == 5

    def test_get_ai_participants(self):
        cell = make_complete_cell()
        ais = cell.get_ai_participants()
        assert len(ais) == 2

    def test_get_steward(self):
        cell = make_complete_cell()
        clarity = cell.get_steward(StewardRole.CLARITY)
        assert clarity is not None
        assert clarity.name == "Clarity Steward"

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


class TestHumanStewards:
    def test_require_human_stewards_is_on_by_default(self):
        assert CellConfig().require_human_stewards is True

    def test_ai_held_steward_is_incomplete(self):
        cell = make_complete_cell()
        cell.get_role("Integrity Steward").participant_type = ParticipantType.AI
        cell.get_participant("human-5").participant_type = ParticipantType.AI
        issues = cell.validate_completeness()
        assert any("Integrity Steward" in i and "human" in i for i in issues)

    def test_ai_participant_in_human_steward_role_is_incomplete(self):
        cell = make_complete_cell()
        cell.participants.append(
            Participant(id="ai-3", name="Bot-Seat", participant_type=ParticipantType.AI,
                        role="Execution Steward")
        )
        issues = cell.validate_completeness()
        assert any("Execution Steward" in i and "human" in i for i in issues)

    def test_hybrid_steward_is_incomplete(self):
        cell = make_complete_cell()
        cell.get_role("Access Steward").participant_type = ParticipantType.HYBRID
        issues = cell.validate_completeness()
        assert any("Access Steward" in i and "human" in i for i in issues)

    def test_steward_with_a_reporting_line_is_incomplete(self):
        cell = make_complete_cell()
        cell.get_role("Narrative Steward").accountability_to = "Clarity Steward"
        issues = cell.validate_completeness()
        assert any("Narrative Steward" in i and "peers" in i for i in issues)

    def test_agent_without_a_steward_is_incomplete(self):
        cell = make_complete_cell()
        cell.get_role("Narrator").accountability_to = None
        issues = cell.validate_completeness()
        assert any("Narrator" in i and "steward" in i for i in issues)

    def test_agent_accountability_cycle_is_incomplete(self):
        cell = make_complete_cell()
        cell.get_role("Executor").accountability_to = "Narrator"
        cell.get_role("Narrator").accountability_to = "Executor"
        issues = cell.validate_completeness()
        assert any("Executor" in i and "steward" in i for i in issues)
        assert any("Narrator" in i and "steward" in i for i in issues)

    def test_agent_may_answer_to_a_steward_through_another_agent(self):
        cell = make_complete_cell()
        cell.roles.append(
            Role(name="Sub-Agent", participant_type=ParticipantType.AI,
                 scope=ScopeDefinition(allowed_actions=["execute"]), accountability_to="Executor")
        )
        cell.participants.append(
            Participant(id="ai-3", name="Bot-Sub", participant_type=ParticipantType.AI, role="Sub-Agent")
        )
        cell.config.max_participants = 8
        assert cell.validate_completeness() == []

    def test_human_steward_checks_can_be_switched_off(self):
        cell = make_complete_cell()
        cell.config = CellConfig(require_human_stewards=False)
        assert cell.config.require_human_stewards is False
        cell.get_role("Integrity Steward").participant_type = ParticipantType.AI
        cell.get_participant("human-5").participant_type = ParticipantType.AI
        cell.get_role("Integrity Steward").accountability_to = "Clarity Steward"
        assert cell.validate_completeness() == []


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
