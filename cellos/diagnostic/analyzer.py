"""Organizational AI-readiness analyzer.

Analyzes an organization's human-AI collaboration patterns and identifies
coordination failures, accountability gaps, and role ambiguity.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from cellos.schema.models import Cell, DecisionRight, ParticipantType, StewardRole


class Severity(str, Enum):
    """Severity of a diagnostic finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Categories of diagnostic findings."""

    ACCOUNTABILITY_GAP = "accountability_gap"
    COORDINATION_FAILURE = "coordination_failure"
    ROLE_AMBIGUITY = "role_ambiguity"
    SCOPE_MISSING = "scope_missing"
    OVERSIGHT_GAP = "oversight_gap"
    HANDOFF_MISSING = "handoff_missing"
    SCALABILITY_RISK = "scalability_risk"
    SINGLE_POINT_OF_FAILURE = "single_point_of_failure"
    STEWARD_NOT_HUMAN = "steward_not_human"
    HIERARCHY = "hierarchy"


class Finding(BaseModel):
    """A single diagnostic finding."""

    category: FindingCategory
    severity: Severity
    title: str
    description: str
    recommendation: str
    affected_roles: list[str] = Field(default_factory=list)
    affected_participants: list[str] = Field(default_factory=list)


class DiagnosticReport(BaseModel):
    """Complete diagnostic report for a cell or organization."""

    cell_id: str
    cell_name: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    overall_score: float = Field(description="0-100 readiness score")
    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    def to_markdown(self) -> str:
        """Generate a human-readable markdown report."""
        lines = [
            f"# Diagnostic Report: {self.cell_name}",
            f"**Cell ID:** {self.cell_id}",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Overall Score:** {self.overall_score:.0f}/100",
            "",
            "## Summary",
            self.summary,
            "",
        ]

        if self.findings:
            lines.append("## Findings")
            lines.append("")

            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
                findings = [f for f in self.findings if f.severity == severity]
                if findings:
                    lines.append(f"### {severity.value.upper()} ({len(findings)})")
                    lines.append("")
                    for f in findings:
                        lines.append(f"**{f.title}** [{f.category.value}]")
                        lines.append(f"  {f.description}")
                        lines.append(f"  *Recommendation:* {f.recommendation}")
                        if f.affected_roles:
                            lines.append(f"  *Affected roles:* {', '.join(f.affected_roles)}")
                        lines.append("")

        if self.recommendations:
            lines.append("## Action Plan")
            lines.append("")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")

        return "\n".join(lines)


class DiagnosticAnalyzer:
    """Analyzes cells for AI-readiness and organizational health."""

    def analyze(self, cell: Cell) -> DiagnosticReport:
        """Run a full diagnostic analysis on a cell."""
        findings: list[Finding] = []

        findings.extend(self._check_steward_coverage(cell))
        findings.extend(self._check_steward_holders(cell))
        findings.extend(self._check_accountability_chains(cell))
        findings.extend(self._check_scope_definitions(cell))
        findings.extend(self._check_human_oversight(cell))
        findings.extend(self._check_handoff_coverage(cell))
        findings.extend(self._check_escalation_paths(cell))
        findings.extend(self._check_role_clarity(cell))
        findings.extend(self._check_single_points_of_failure(cell))

        score = self._calculate_score(cell, findings)
        summary = self._generate_summary(cell, findings, score)
        recommendations = self._generate_recommendations(findings)

        return DiagnosticReport(
            cell_id=cell.id,
            cell_name=cell.name,
            overall_score=score,
            findings=findings,
            summary=summary,
            recommendations=recommendations,
        )

    def _check_steward_coverage(self, cell: Cell) -> list[Finding]:
        """Check if all five steward roles are assigned."""
        findings = []
        assigned = {r.steward_role for r in cell.roles if r.steward_role}

        for sr in StewardRole:
            if sr not in assigned:
                findings.append(
                    Finding(
                        category=FindingCategory.ROLE_AMBIGUITY,
                        severity=Severity.HIGH,
                        title=f"Missing steward role: {sr.value}",
                        description=(
                            f"The {sr.value} steward role is not assigned to any role in this cell, "
                            f"so nobody owns {self._steward_description(sr)}."
                        ),
                        recommendation=(
                            f"Assign the {sr.value} steward function to a role held by a human."
                        ),
                    )
                )
        return findings

    def _check_steward_holders(self, cell: Cell) -> list[Finding]:
        """Check that every steward role is held by a human and reports to no one."""
        findings = []
        for role in cell.roles:
            if not role.steward_role:
                continue
            sr = role.steward_role

            participants = cell.get_participants_for_role(role.name)
            ai_held = role.participant_type == ParticipantType.AI or any(
                p.participant_type == ParticipantType.AI for p in participants
            )
            if ai_held:
                findings.append(
                    Finding(
                        category=FindingCategory.STEWARD_NOT_HUMAN,
                        severity=Severity.CRITICAL,
                        title=f"Steward role '{role.name}' is held by AI",
                        description=(
                            f"Role '{role.name}' holds the {sr.value} steward function, which owns "
                            f"{self._steward_description(sr)}. Steward roles are held by humans. "
                            f"AI agents work beneath a steward and never hold the seat."
                        ),
                        recommendation=(
                            f"Put a human in '{role.name}' and move its AI participants into a "
                            f"role beneath it, with accountability_to set to '{role.name}'."
                        ),
                        affected_roles=[role.name],
                        affected_participants=[
                            p.id for p in participants if p.participant_type == ParticipantType.AI
                        ],
                    )
                )
            elif not cell.is_human_held(role):
                findings.append(
                    Finding(
                        category=FindingCategory.STEWARD_NOT_HUMAN,
                        severity=Severity.HIGH,
                        title=f"Steward role '{role.name}' is not held by a human",
                        description=(
                            f"Role '{role.name}' holds the {sr.value} steward function but is not "
                            f"declared human (type: {role.participant_type.value}). Steward roles "
                            f"are held by humans."
                        ),
                        recommendation=(
                            f"Set participant_type to human on '{role.name}' and make sure "
                            f"a human fills it."
                        ),
                        affected_roles=[role.name],
                    )
                )

            if role.accountability_to:
                findings.append(
                    Finding(
                        category=FindingCategory.HIERARCHY,
                        severity=Severity.HIGH,
                        title=f"Steward '{role.name}' reports to '{role.accountability_to}'",
                        description=(
                            f"Stewards are peers. A reporting line from steward '{role.name}' "
                            f"to '{role.accountability_to}' puts a boss node above the cell."
                        ),
                        recommendation=(
                            f"Remove accountability_to from '{role.name}'. Stewards answer to "
                            f"each other as peers, not up a chain."
                        ),
                        affected_roles=[role.name, role.accountability_to],
                    )
                )
        return findings

    def _check_accountability_chains(self, cell: Cell) -> list[Finding]:
        """Check that every agent role answers, possibly through other agents, to a steward."""
        findings = []
        for role in cell.roles:
            # Steward roles answer to no one; _check_steward_holders covers them.
            if role.steward_role:
                continue

            if not role.accountability_to:
                if role.participant_type != ParticipantType.HUMAN:
                    findings.append(
                        Finding(
                            category=FindingCategory.ACCOUNTABILITY_GAP,
                            severity=Severity.CRITICAL,
                            title=f"AI role '{role.name}' has no accountability chain",
                            description=(
                                f"Role '{role.name}' (type: {role.participant_type.value}) "
                                f"is not accountable to any other role. Every AI agent must "
                                f"answer to the human steward it works beneath."
                            ),
                            recommendation=(
                                f"Set accountability_to for role '{role.name}' to the steward "
                                f"role whose function it works under."
                            ),
                            affected_roles=[role.name],
                        )
                    )
                continue

            # Check for circular accountability
            target = cell.get_role(role.accountability_to)
            if target and target.accountability_to == role.name:
                findings.append(
                    Finding(
                        category=FindingCategory.ACCOUNTABILITY_GAP,
                        severity=Severity.HIGH,
                        title=f"Circular accountability: {role.name} <-> {target.name}",
                        description=(
                            f"Roles '{role.name}' and '{target.name}' are accountable "
                            f"to each other, creating a circular chain that never reaches a steward."
                        ),
                        recommendation=(
                            "Break the circle: each agent answers to the one steward it works beneath."
                        ),
                        affected_roles=[role.name, target.name],
                    )
                )
            elif not cell.is_human_held(role) and not cell.get_accountable_steward(role):
                findings.append(
                    Finding(
                        category=FindingCategory.ACCOUNTABILITY_GAP,
                        severity=Severity.HIGH,
                        title=f"Role '{role.name}' does not answer to a steward",
                        description=(
                            f"Role '{role.name}' is accountable to '{role.accountability_to}', "
                            f"but that chain never reaches a steward role. Every agent works "
                            f"beneath one of the five human stewards."
                        ),
                        recommendation=(
                            f"Point accountability_to for '{role.name}' at the steward role whose "
                            f"function it works under, or at an agent that answers to that steward."
                        ),
                        affected_roles=[role.name],
                    )
                )
        return findings

    def _check_scope_definitions(self, cell: Cell) -> list[Finding]:
        """Check if AI roles have explicit scope boundaries."""
        findings = []
        for role in cell.roles:
            participants = cell.get_participants_for_role(role.name)
            ai_participants = [p for p in participants if p.participant_type == ParticipantType.AI]

            if ai_participants and not role.scope.allowed_actions and not role.scope.forbidden_actions:
                findings.append(
                    Finding(
                        category=FindingCategory.SCOPE_MISSING,
                        severity=Severity.HIGH,
                        title=f"AI role '{role.name}' has no scope boundaries",
                        description=(
                            f"Role '{role.name}' has AI participants but no defined scope "
                            f"boundaries. Without explicit allowed/forbidden actions, "
                            f"AI agents may take actions outside their intended authority."
                        ),
                        recommendation=(
                            f"Define allowed_actions and forbidden_actions for role '{role.name}'."
                        ),
                        affected_roles=[role.name],
                        affected_participants=[p.id for p in ai_participants],
                    )
                )
        return findings

    def _check_human_oversight(self, cell: Cell) -> list[Finding]:
        """Check for adequate human oversight of AI participants."""
        findings = []
        humans = cell.get_human_participants()
        ais = cell.get_ai_participants()

        if not humans and ais:
            findings.append(
                Finding(
                    category=FindingCategory.OVERSIGHT_GAP,
                    severity=Severity.CRITICAL,
                    title="No human participants in cell with AI agents",
                    description=(
                        "This cell has AI participants but no human participants. "
                        "There is no human oversight of AI operations."
                    ),
                    recommendation="Add at least one human participant with oversight authority.",
                )
            )

        # Check AI roles with full decision rights
        for role in cell.roles:
            if role.decision_rights == DecisionRight.FULL:
                ai_in_role = [
                    p
                    for p in cell.get_participants_for_role(role.name)
                    if p.participant_type == ParticipantType.AI
                ]
                if ai_in_role:
                    findings.append(
                        Finding(
                            category=FindingCategory.OVERSIGHT_GAP,
                            severity=Severity.MEDIUM,
                            title=f"AI has full decision rights in role '{role.name}'",
                            description=(
                                f"AI participant(s) in role '{role.name}' have FULL decision "
                                f"rights. Consider whether CONDITIONAL rights with defined "
                                f"parameters would be more appropriate."
                            ),
                            recommendation=(
                                f"Review whether CONDITIONAL decision rights with explicit "
                                f"parameters would be safer for role '{role.name}'."
                            ),
                            affected_roles=[role.name],
                            affected_participants=[p.id for p in ai_in_role],
                        )
                    )
        return findings

    def _check_handoff_coverage(self, cell: Cell) -> list[Finding]:
        """Check for missing handoff protocols between roles that interact."""
        findings = []
        ai_roles = {
            r.name
            for r in cell.roles
            if any(
                p.participant_type == ParticipantType.AI
                for p in cell.get_participants_for_role(r.name)
            )
        }
        human_roles = {
            r.name
            for r in cell.roles
            if any(
                p.participant_type == ParticipantType.HUMAN
                for p in cell.get_participants_for_role(r.name)
            )
        }

        # Check AI-to-human handoffs exist
        handoff_pairs = {(h.from_role, h.to_role) for h in cell.handoff_protocols}

        for ai_role in ai_roles:
            role = cell.get_role(ai_role)
            if role and role.accountability_to and role.accountability_to in human_roles:
                if (ai_role, role.accountability_to) not in handoff_pairs:
                    findings.append(
                        Finding(
                            category=FindingCategory.HANDOFF_MISSING,
                            severity=Severity.MEDIUM,
                            title=f"No handoff protocol: {ai_role} -> {role.accountability_to}",
                            description=(
                                f"AI role '{ai_role}' is accountable to human role "
                                f"'{role.accountability_to}' but there is no defined handoff "
                                f"protocol for transitioning work between them."
                            ),
                            recommendation=(
                                f"Define a HandoffProtocol from '{ai_role}' to "
                                f"'{role.accountability_to}' with required context and validation."
                            ),
                            affected_roles=[ai_role, role.accountability_to],
                        )
                    )
        return findings

    def _check_escalation_paths(self, cell: Cell) -> list[Finding]:
        """Check that AI roles have escalation paths defined."""
        findings = []
        for role in cell.roles:
            ai_in_role = [
                p
                for p in cell.get_participants_for_role(role.name)
                if p.participant_type == ParticipantType.AI
            ]
            if ai_in_role and not role.escalation_rules:
                findings.append(
                    Finding(
                        category=FindingCategory.COORDINATION_FAILURE,
                        severity=Severity.MEDIUM,
                        title=f"No escalation rules for AI role '{role.name}'",
                        description=(
                            f"AI role '{role.name}' has no defined escalation rules. "
                            f"When AI encounters situations outside its capability or scope, "
                            f"there is no defined path for escalating to human judgment."
                        ),
                        recommendation=(
                            f"Add escalation rules for common triggers: scope_boundary, "
                            f"confidence_low, error."
                        ),
                        affected_roles=[role.name],
                    )
                )
        return findings

    def _check_role_clarity(self, cell: Cell) -> list[Finding]:
        """Check for roles with unclear or overlapping definitions."""
        findings = []
        for role in cell.roles:
            if not role.description:
                findings.append(
                    Finding(
                        category=FindingCategory.ROLE_AMBIGUITY,
                        severity=Severity.LOW,
                        title=f"Role '{role.name}' has no description",
                        description=(
                            f"Role '{role.name}' lacks a description. Clear role descriptions "
                            f"help all participants understand expectations and boundaries."
                        ),
                        recommendation=f"Add a description to role '{role.name}'.",
                        affected_roles=[role.name],
                    )
                )

            if not role.kpis:
                findings.append(
                    Finding(
                        category=FindingCategory.ROLE_AMBIGUITY,
                        severity=Severity.LOW,
                        title=f"No KPIs defined for role '{role.name}'",
                        description=(
                            f"Role '{role.name}' has no KPIs. Without measurable indicators, "
                            f"it is difficult to assess whether the role is being performed well."
                        ),
                        recommendation=f"Define 2-3 KPIs for role '{role.name}'.",
                        affected_roles=[role.name],
                    )
                )
        return findings

    def _check_single_points_of_failure(self, cell: Cell) -> list[Finding]:
        """Check for roles with only one participant (SPOF risk)."""
        findings = []
        for role in cell.roles:
            participants = cell.get_participants_for_role(role.name)
            if len(participants) == 1 and role.steward_role:
                findings.append(
                    Finding(
                        category=FindingCategory.SINGLE_POINT_OF_FAILURE,
                        severity=Severity.LOW,
                        title=f"Single participant in steward role '{role.name}'",
                        description=(
                            f"Steward role '{role.name}' ({role.steward_role.value}) has only "
                            f"one participant. If that participant is unavailable, this steward "
                            f"function has no coverage."
                        ),
                        recommendation=(
                            f"Consider adding a backup participant or defining a fallback "
                            f"protocol for role '{role.name}'."
                        ),
                        affected_roles=[role.name],
                        affected_participants=[participants[0].id],
                    )
                )
        return findings

    def _calculate_score(self, cell: Cell, findings: list[Finding]) -> float:
        """Calculate an overall readiness score (0-100)."""
        score = 100.0
        for f in findings:
            if f.severity == Severity.CRITICAL:
                score -= 20
            elif f.severity == Severity.HIGH:
                score -= 10
            elif f.severity == Severity.MEDIUM:
                score -= 5
            elif f.severity == Severity.LOW:
                score -= 2
        return max(0.0, score)

    def _generate_summary(self, cell: Cell, findings: list[Finding], score: float) -> str:
        """Generate a human-readable summary."""
        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)
        humans = len(cell.get_human_participants())
        ais = len(cell.get_ai_participants())

        if score >= 80:
            assessment = "well-structured for human-AI collaboration"
        elif score >= 60:
            assessment = "partially ready but has significant gaps to address"
        elif score >= 40:
            assessment = "not ready for effective human-AI collaboration"
        else:
            assessment = "critically lacking coordination infrastructure"

        return (
            f"Cell '{cell.name}' has {humans} human and {ais} AI participants. "
            f"The diagnostic found {len(findings)} issues ({critical} critical, {high} high). "
            f"Overall, the cell is {assessment} (score: {score:.0f}/100)."
        )

    def _generate_recommendations(self, findings: list[Finding]) -> list[str]:
        """Generate a prioritized list of recommendations."""
        recs = []
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM]:
            for f in findings:
                if f.severity == severity and f.recommendation not in recs:
                    recs.append(f.recommendation)
        return recs

    @staticmethod
    def _steward_description(sr: StewardRole) -> str:
        """Get a human-readable description of a steward role."""
        descriptions = {
            StewardRole.CLARITY: "the question (direction, scope and what done means)",
            StewardRole.EXECUTION: (
                "the doing (delivery, quality, tooling, and what gets automated)"
            ),
            StewardRole.NARRATIVE: "the story (what is said, where, and in whose voice)",
            StewardRole.ACCESS: "the doors (customers, partners and capital)",
            StewardRole.INTEGRITY: "trust (governance, incentives, conflict and accountability)",
        }
        return descriptions.get(sr, sr.value)
