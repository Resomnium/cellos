"""Core data models for the Cell Schema specification.

Defines the formal structure for organizational cells where humans
and AI agents collaborate with explicit roles, accountability, and
coordination protocols.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ParticipantType(str, Enum):
    """Whether a cell participant is human or AI."""

    HUMAN = "human"
    AI = "ai"
    HYBRID = "hybrid"  # Role can be filled by either


class StewardRole(str, Enum):
    """The five fixed steward roles in the Cell Framework.

    Every cell has these five roles filled. Additional domain-specific
    roles can be added via the Role model.
    """

    CLARITY = "clarity"  # Strategic direction, priorities
    EXECUTION = "execution"  # Operational coordination, delivery
    NARRATIVE = "narrative"  # Content, messaging, distribution
    ACCESS = "access"  # Relationships, partnerships
    GOVERNANCE = "governance"  # Financial discipline, accountability


class DecisionRight(str, Enum):
    """Level of autonomous decision-making authority."""

    FULL = "full"  # Can decide and act without approval
    CONDITIONAL = "conditional"  # Can decide within defined parameters
    ADVISORY = "advisory"  # Can recommend, human decides
    NONE = "none"  # No decision authority, execution only


class EscalationTrigger(str, Enum):
    """Conditions that trigger escalation to a human or higher authority."""

    SCOPE_BOUNDARY = "scope_boundary"  # Task exceeds defined scope
    CONFIDENCE_LOW = "confidence_low"  # Agent confidence below threshold
    COST_THRESHOLD = "cost_threshold"  # Action cost exceeds limit
    TIMEOUT = "timeout"  # No response within deadline
    CONFLICT = "conflict"  # Conflicting directives from multiple sources
    ERROR = "error"  # Unrecoverable error
    EXPLICIT = "explicit"  # Human explicitly requested


class ScopeDefinition(BaseModel):
    """Defines the boundaries of what a participant can do."""

    allowed_actions: list[str] = Field(
        default_factory=list,
        description="Actions this participant is authorized to perform",
    )
    forbidden_actions: list[str] = Field(
        default_factory=list,
        description="Actions explicitly forbidden for this participant",
    )
    resource_limits: dict[str, Any] = Field(
        default_factory=dict,
        description="Resource limits (e.g., budget caps, API call limits, time limits)",
    )
    requires_approval_for: list[str] = Field(
        default_factory=list,
        description="Actions that require explicit approval before execution",
    )


class EscalationRule(BaseModel):
    """Defines when and how to escalate to a human or higher authority."""

    trigger: EscalationTrigger
    target_role: str = Field(description="Role to escalate to")
    timeout_seconds: int | None = Field(
        default=None,
        description="Max time to wait before escalating (for timeout triggers)",
    )
    threshold: float | None = Field(
        default=None,
        description="Threshold value (e.g., confidence score, cost amount)",
    )
    message_template: str | None = Field(
        default=None,
        description="Template for the escalation notification",
    )


class HandoffProtocol(BaseModel):
    """Defines how work transitions between participants."""

    from_role: str
    to_role: str
    trigger: str = Field(description="Condition that initiates the handoff")
    required_context: list[str] = Field(
        default_factory=list,
        description="Information that must be passed during handoff",
    )
    validation: str | None = Field(
        default=None,
        description="Validation step before handoff completes",
    )
    fallback_role: str | None = Field(
        default=None,
        description="Role to hand off to if primary target is unavailable",
    )


class Role(BaseModel):
    """A role within a cell, which can be filled by a human or AI participant."""

    name: str
    steward_role: StewardRole | None = Field(
        default=None,
        description="Which steward role this maps to, if any",
    )
    participant_type: ParticipantType = ParticipantType.HYBRID
    description: str = ""
    decision_rights: DecisionRight = DecisionRight.ADVISORY
    scope: ScopeDefinition = Field(default_factory=ScopeDefinition)
    escalation_rules: list[EscalationRule] = Field(default_factory=list)
    accountability_to: str | None = Field(
        default=None,
        description="Role that this role is accountable to",
    )
    kpis: list[str] = Field(
        default_factory=list,
        description="Key performance indicators for this role",
    )


class Participant(BaseModel):
    """A concrete participant (human or AI) assigned to a role in a cell."""

    id: str
    name: str
    participant_type: ParticipantType
    role: str = Field(description="Name of the Role this participant fills")
    capabilities: list[str] = Field(
        default_factory=list,
        description="What this participant can do",
    )
    availability: str = Field(
        default="always",
        description="Availability schedule (always, business_hours, on_demand)",
    )
    contact_protocol: str | None = Field(
        default=None,
        description="How to reach this participant (email, API endpoint, A2A agent card URL)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional participant-specific metadata",
    )


class CellConfig(BaseModel):
    """Configuration parameters for cell behavior."""

    max_participants: int = Field(default=7, ge=2, le=15)
    require_human_oversight: bool = Field(
        default=True,
        description="Whether at least one human must be in every decision chain",
    )
    audit_all_actions: bool = Field(
        default=True,
        description="Whether to log every action for accountability",
    )
    default_escalation_timeout: int = Field(
        default=3600,
        description="Default seconds before unresponded tasks escalate",
    )
    allow_ai_to_ai_handoffs: bool = Field(
        default=True,
        description="Whether AI participants can hand off directly to other AI",
    )
    require_scope_boundaries: bool = Field(
        default=True,
        description="Whether every role must have explicit scope definitions",
    )


class Cell(BaseModel):
    """A cell: the fundamental unit of human-AI organizational coordination.

    A cell is a small, autonomous team of 2-15 participants (human and AI)
    with explicit roles, accountability chains, and coordination protocols.
    """

    id: str
    name: str
    description: str = ""
    mandate: str = Field(
        default="",
        description="The cell's mission - what it exists to accomplish",
    )
    roles: list[Role] = Field(default_factory=list)
    participants: list[Participant] = Field(default_factory=list)
    handoff_protocols: list[HandoffProtocol] = Field(default_factory=list)
    config: CellConfig = Field(default_factory=CellConfig)
    parent_cell_id: str | None = Field(
        default=None,
        description="ID of parent cell if this is a nested sub-cell",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_role(self, name: str) -> Role | None:
        """Get a role by name."""
        for role in self.roles:
            if role.name == name:
                return role
        return None

    def get_participant(self, id: str) -> Participant | None:
        """Get a participant by ID."""
        for p in self.participants:
            if p.id == id:
                return p
        return None

    def get_participants_for_role(self, role_name: str) -> list[Participant]:
        """Get all participants assigned to a specific role."""
        return [p for p in self.participants if p.role == role_name]

    def get_human_participants(self) -> list[Participant]:
        """Get all human participants in the cell."""
        return [p for p in self.participants if p.participant_type == ParticipantType.HUMAN]

    def get_ai_participants(self) -> list[Participant]:
        """Get all AI participants in the cell."""
        return [p for p in self.participants if p.participant_type == ParticipantType.AI]

    def get_steward(self, steward_role: StewardRole) -> Role | None:
        """Get the role assigned to a specific steward function."""
        for role in self.roles:
            if role.steward_role == steward_role:
                return role
        return None

    def validate_completeness(self) -> list[str]:
        """Check if the cell has all required steward roles filled.

        Returns a list of issues found. Empty list means the cell is complete.
        """
        issues = []

        # Check all steward roles are assigned
        assigned_stewards = {r.steward_role for r in self.roles if r.steward_role}
        for sr in StewardRole:
            if sr not in assigned_stewards:
                issues.append(f"Missing steward role: {sr.value}")

        # Check all roles have at least one participant
        for role in self.roles:
            participants = self.get_participants_for_role(role.name)
            if not participants:
                issues.append(f"Role '{role.name}' has no assigned participants")

        # Check participant count within limits
        if len(self.participants) > self.config.max_participants:
            issues.append(
                f"Too many participants: {len(self.participants)} > {self.config.max_participants}"
            )

        # Check human oversight requirement
        if self.config.require_human_oversight and not self.get_human_participants():
            issues.append("No human participants but human oversight is required")

        # Check scope boundaries requirement
        if self.config.require_scope_boundaries:
            for role in self.roles:
                if not role.scope.allowed_actions and not role.scope.forbidden_actions:
                    issues.append(f"Role '{role.name}' has no scope boundaries defined")

        # Check accountability chains
        for role in self.roles:
            if role.accountability_to:
                target = self.get_role(role.accountability_to)
                if not target:
                    issues.append(
                        f"Role '{role.name}' accountable to non-existent role "
                        f"'{role.accountability_to}'"
                    )

        # Check handoff protocol references
        for hp in self.handoff_protocols:
            if not self.get_role(hp.from_role):
                issues.append(f"Handoff from non-existent role '{hp.from_role}'")
            if not self.get_role(hp.to_role):
                issues.append(f"Handoff to non-existent role '{hp.to_role}'")

        return issues
