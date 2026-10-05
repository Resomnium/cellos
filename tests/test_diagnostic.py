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
    """A well-configured cell that should score high.

    Five human stewards, flat, with AI agents working beneath their own steward.
    """
    return Cell(
        id="healthy",
        name="Healthy Cell",
        roles=[
            Role(name="Clarity", steward_role=StewardRole.CLARITY, participant_type=ParticipantType.HUMAN,
                 description="Owns direction", decision_rights=DecisionRight.FULL,
                 scope=ScopeDefinition(allowed_actions=["decide"]), kpis=["focus"]),
            Role(name="Execution", steward_role=StewardRole.EXECUTION, participant_type=ParticipantType.HUMAN,
                 description="Owns delivery", decision_rights=DecisionRight.FULL,
                 scope=ScopeDefinition(allowed_actions=["deliver"]), kpis=["speed"]),
            Role(name="Narrative", steward_role=StewardRole.NARRATIVE, participant_type=ParticipantType.HUMAN,
                 description="Owns the story", decision_rights=DecisionRight.FULL,
                 scope=ScopeDefinition(allowed_actions=["publish"]), kpis=["reach"]),
            Role(name="Access", steward_role=StewardRole.ACCESS, participant_type=ParticipantType.HUMAN,
                 description="Owns the doors", decision_rights=DecisionRight.FULL,
                 scope=ScopeDefinition(allowed_actions=["engage"]), kpis=["connections"]),
            Role(name="Integrity", steward_role=StewardRole.INTEGRITY, participant_type=ParticipantType.HUMAN,
                 description="Owns trust", decision_rights=DecisionRight.FULL,
                 scope=ScopeDefinition(allowed_actions=["audit"]), kpis=["accuracy"]),
            Role(name="Exec Agent", participant_type=ParticipantType.AI,
                 description="Executes", decision_rights=DecisionRight.CONDITIONAL,
                 scope=ScopeDefinition(allowed_actions=["execute"], forbidden_actions=["delete"]),
                 accountability_to="Execution", kpis=["throughput"],
                 escalation_rules=[{"trigger": "scope_boundary", "target_role": "Execution"}]),
            Role(name="Writer Agent", participant_type=ParticipantType.AI,
                 description="Drafts", decision_rights=DecisionRight.ADVISORY,
                 scope=ScopeDefinition(allowed_actions=["write"], forbidden_actions=["publish"]),
                 accountability_to="Narrative", kpis=["drafts"],
                 escalation_rules=[{"trigger": "scope_boundary", "target_role": "Narrative"}]),
        ],
        participants=[
            Participant(id="h1", name="Human-1", participant_type=ParticipantType.HUMAN, role="Clarity"),
            Participant(id="h2", name="Human-2", participant_type=ParticipantType.HUMAN, role="Execution"),
            Participant(id="h3", name="Human-3", participant_type=ParticipantType.HUMAN, role="Narrative"),
            Participant(id="h4", name="Human-4", participant_type=ParticipantType.HUMAN, role="Access"),
            Participant(id="h5", name="Human-5", participant_type=ParticipantType.HUMAN, role="Integrity"),
            Participant(id="a1", name="AI-1", participant_type=ParticipantType.AI, role="Exec Agent"),
            Participant(id="a2", name="AI-2", participant_type=ParticipantType.AI, role="Writer Agent"),
        ],
        handoff_protocols=[
            {"from_role": "Exec Agent", "to_role": "Execution", "trigger": "done", "required_context": ["result"]},
            {"from_role": "Writer Agent", "to_role": "Narrative", "trigger": "draft_ready",
             "required_context": ["draft"]},
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

    def test_missing_integrity_explains_what_it_owns(self):
        cell = make_healthy_cell()
        cell.roles = [r for r in cell.roles if r.steward_role != StewardRole.INTEGRITY]
        report = DiagnosticAnalyzer().analyze(cell)
        missing = [f for f in report.findings if f.title == "Missing steward role: integrity"]
        assert len(missing) == 1
        assert "trust" in missing[0].description


def findings_for(report, category, role_name):
    return [f for f in report.findings if f.category == category and role_name in f.affected_roles]


class TestHumanStewards:
    def test_healthy_cell_has_no_critical_or_high_findings(self):
        report = DiagnosticAnalyzer().analyze(make_healthy_cell())
        assert report.critical_count == 0
        assert report.high_count == 0

    def test_ai_held_steward_is_critical(self):
        cell = make_healthy_cell()
        cell.get_role("Integrity").participant_type = ParticipantType.AI
        cell.get_participant("h5").participant_type = ParticipantType.AI
        report = DiagnosticAnalyzer().analyze(cell)
        found = findings_for(report, FindingCategory.STEWARD_NOT_HUMAN, "Integrity")
        assert [f.severity for f in found] == [Severity.CRITICAL]

    def test_ai_participant_in_steward_seat_is_critical(self):
        cell = make_healthy_cell()
        cell.participants.append(
            Participant(id="a3", name="AI-3", participant_type=ParticipantType.AI, role="Access")
        )
        report = DiagnosticAnalyzer().analyze(cell)
        found = findings_for(report, FindingCategory.STEWARD_NOT_HUMAN, "Access")
        assert [f.severity for f in found] == [Severity.CRITICAL]

    def test_hybrid_steward_is_high(self):
        cell = make_healthy_cell()
        cell.get_role("Access").participant_type = ParticipantType.HYBRID
        report = DiagnosticAnalyzer().analyze(cell)
        found = findings_for(report, FindingCategory.STEWARD_NOT_HUMAN, "Access")
        assert [f.severity for f in found] == [Severity.HIGH]

    def test_steward_is_not_told_to_report_to_someone(self):
        # The old check told a non-human steward to set accountability_to,
        # which pushes the cell into hub-and-spoke. The fix is a human in the seat.
        cell = make_healthy_cell()
        cell.get_role("Access").participant_type = ParticipantType.HYBRID
        report = DiagnosticAnalyzer().analyze(cell)
        assert findings_for(report, FindingCategory.ACCOUNTABILITY_GAP, "Access") == []

    def test_steward_reporting_line_is_flagged(self):
        cell = make_healthy_cell()
        cell.get_role("Narrative").accountability_to = "Clarity"
        report = DiagnosticAnalyzer().analyze(cell)
        found = findings_for(report, FindingCategory.HIERARCHY, "Narrative")
        assert [f.severity for f in found] == [Severity.HIGH]

    def test_agent_not_answering_to_a_steward_is_flagged(self):
        cell = make_healthy_cell()
        cell.roles.append(
            Role(name="Coordinator", participant_type=ParticipantType.HUMAN,
                 description="Not a steward", scope=ScopeDefinition(allowed_actions=["coordinate"]),
                 kpis=["flow"])
        )
        cell.participants.append(
            Participant(id="h6", name="Human-6", participant_type=ParticipantType.HUMAN, role="Coordinator")
        )
        cell.get_role("Writer Agent").accountability_to = "Coordinator"
        report = DiagnosticAnalyzer().analyze(cell)
        found = findings_for(report, FindingCategory.ACCOUNTABILITY_GAP, "Writer Agent")
        assert [f.severity for f in found] == [Severity.HIGH]

    def test_one_human_hub_with_ai_stewards_scores_low(self):
        # The shape the library used to call healthy: one human lead,
        # four AI-held stewards all accountable to that lead.
        cell = make_healthy_cell()
        for name, pid in [("Execution", "h2"), ("Narrative", "h3"), ("Access", "h4"), ("Integrity", "h5")]:
            cell.get_role(name).participant_type = ParticipantType.AI
            cell.get_role(name).accountability_to = "Clarity"
            cell.get_participant(pid).participant_type = ParticipantType.AI
        report = DiagnosticAnalyzer().analyze(cell)
        assert report.critical_count == 4
        assert len([f for f in report.findings if f.category == FindingCategory.HIERARCHY]) == 4
        assert report.overall_score < 50
