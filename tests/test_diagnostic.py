"""Tests for the Diagnostic Toolkit."""

from cellos.schema.models import (
    Cell,
    DecisionRight,
    Participant,
    ParticipantType,
    Role,
    ScopeDefinition,
    StewardRole,
)
from cellos.diagnostic.analyzer import DiagnosticAnalyzer, FindingCategory, Severity


def make_healthy_cell() -> Cell:
    """A well-configured cell that should score high."""
    return Cell(
        id="healthy",
        name="Healthy Cell",
        roles=[
            Role(name="Lead", steward_role=StewardRole.CLARITY, participant_type=ParticipantType.HUMAN,
                 description="Leads", decision_rights=DecisionRight.FULL,
                 scope=ScopeDefinition(allowed_actions=["decide"]), kpis=["quality"]),
            Role(name="Exec", steward_role=StewardRole.EXECUTION, participant_type=ParticipantType.AI,
                 description="Executes", decision_rights=DecisionRight.CONDITIONAL,
                 scope=ScopeDefinition(allowed_actions=["execute"], forbidden_actions=["delete"]),
                 accountability_to="Lead", kpis=["speed"],
                 escalation_rules=[{"trigger": "scope_boundary", "target_role": "Lead"}]),
            Role(name="Writer", steward_role=StewardRole.NARRATIVE, participant_type=ParticipantType.AI,
                 description="Writes", decision_rights=DecisionRight.ADVISORY,
                 scope=ScopeDefinition(allowed_actions=["write"]),
                 accountability_to="Lead", kpis=["output"],
                 escalation_rules=[{"trigger": "scope_boundary", "target_role": "Lead"}]),
            Role(name="Networker", steward_role=StewardRole.ACCESS, participant_type=ParticipantType.AI,
                 description="Networks", decision_rights=DecisionRight.ADVISORY,
                 scope=ScopeDefinition(allowed_actions=["connect"]),
                 accountability_to="Lead", kpis=["connections"],
                 escalation_rules=[{"trigger": "scope_boundary", "target_role": "Lead"}]),
            Role(name="Checker", steward_role=StewardRole.INTEGRITY, participant_type=ParticipantType.AI,
                 description="Checks", decision_rights=DecisionRight.ADVISORY,
                 scope=ScopeDefinition(allowed_actions=["review"]),
                 accountability_to="Lead", kpis=["accuracy"],
                 escalation_rules=[{"trigger": "scope_boundary", "target_role": "Lead"}]),
        ],
        participants=[
            Participant(id="h1", name="Human", participant_type=ParticipantType.HUMAN, role="Lead"),
            Participant(id="a1", name="AI-1", participant_type=ParticipantType.AI, role="Exec"),
            Participant(id="a2", name="AI-2", participant_type=ParticipantType.AI, role="Writer"),
            Participant(id="a3", name="AI-3", participant_type=ParticipantType.AI, role="Networker"),
            Participant(id="a4", name="AI-4", participant_type=ParticipantType.AI, role="Checker"),
        ],
        handoff_protocols=[
            {"from_role": "Exec", "to_role": "Lead", "trigger": "done", "required_context": ["result"]},
        ],
    )


def make_broken_cell() -> Cell:
    """A poorly-configured cell that should score low."""
    return Cell(
        id="broken",
        name="Broken Cell",
        roles=[
            Role(name="Bot", participant_type=ParticipantType.AI,
                 decision_rights=DecisionRight.FULL),
        ],
        participants=[
            Participant(id="b1", name="Lonely Bot", participant_type=ParticipantType.AI, role="Bot"),
        ],
    )


class TestDiagnosticAnalyzer:
    def test_healthy_cell_scores_high(self):
        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(make_healthy_cell())
        assert report.overall_score >= 70

    def test_broken_cell_scores_low(self):
        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(make_broken_cell())
        assert report.overall_score < 50

    def test_broken_cell_has_critical_findings(self):
        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(make_broken_cell())
        assert report.critical_count > 0

    def test_missing_steward_detected(self):
        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(make_broken_cell())
        steward_findings = [
            f for f in report.findings if "steward" in f.title.lower()
        ]
        assert len(steward_findings) > 0

    def test_no_human_oversight_detected(self):
        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(make_broken_cell())
        oversight_findings = [
            f for f in report.findings if f.category == FindingCategory.OVERSIGHT_GAP
        ]
        assert len(oversight_findings) > 0

    def test_accountability_gap_detected(self):
        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(make_broken_cell())
        accountability_findings = [
            f for f in report.findings if f.category == FindingCategory.ACCOUNTABILITY_GAP
        ]
        assert len(accountability_findings) > 0

    def test_markdown_report_generated(self):
        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(make_healthy_cell())
        md = report.to_markdown()
        assert "# Diagnostic Report" in md
        assert "Healthy Cell" in md
        assert "Score:" in md

    def test_recommendations_generated(self):
        analyzer = DiagnosticAnalyzer()
        report = analyzer.analyze(make_broken_cell())
        assert len(report.recommendations) > 0
