"""Example: Integrating CellOS with the Google A2A Protocol.

Shows how CellOS cell definitions can reference A2A agent cards,
enabling seamless coordination between cell participants and
external A2A-compatible agents.

This example uses Resomnium's real A2A endpoint at:
https://resomnium.com/.well-known/agent-card.json
"""

from __future__ import annotations

from cellos import (
    Cell,
    CellRuntime,
    Coordinator,
    Participant,
    ParticipantType,
    Role,
    StewardRole,
)
from cellos.schema.models import (
    DecisionRight,
    EscalationRule,
    EscalationTrigger,
    HandoffProtocol,
    ScopeDefinition,
)


def create_a2a_integrated_cell() -> Cell:
    """Create a cell that includes an A2A-connected agent.

    Demonstrates how CellOS participants can reference external
    A2A agent cards for interoperable coordination.
    """
    return Cell(
        id="a2a-demo",
        name="A2A-Integrated Operations Cell",
        mandate="Demonstrate cross-protocol coordination between CellOS and A2A agents",
        roles=[
            Role(
                name="Coordinator",
                steward_role=StewardRole.CLARITY,
                participant_type=ParticipantType.HUMAN,
                description="Human coordinator who oversees all operations",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["approve", "direct", "review"]),
                kpis=["coordination_quality"],
            ),
            Role(
                name="A2A Agent",
                steward_role=StewardRole.EXECUTION,
                participant_type=ParticipantType.AI,
                description=(
                    "External AI agent accessible via Google A2A protocol. "
                    "Can receive tasks via JSON-RPC and respond asynchronously."
                ),
                decision_rights=DecisionRight.CONDITIONAL,
                scope=ScopeDefinition(
                    allowed_actions=["process_task", "analyze", "generate_report"],
                    forbidden_actions=["send_email", "make_purchase", "modify_data"],
                    requires_approval_for=["external_communication"],
                ),
                accountability_to="Coordinator",
                escalation_rules=[
                    EscalationRule(
                        trigger=EscalationTrigger.SCOPE_BOUNDARY,
                        target_role="Coordinator",
                    ),
                    EscalationRule(
                        trigger=EscalationTrigger.CONFIDENCE_LOW,
                        target_role="Coordinator",
                        threshold=0.7,
                    ),
                    EscalationRule(
                        trigger=EscalationTrigger.TIMEOUT,
                        target_role="Coordinator",
                        timeout_seconds=300,  # 5-minute timeout for A2A responses
                    ),
                ],
                kpis=["task_completion_rate", "response_time"],
            ),
            Role(
                name="Local Agent",
                steward_role=StewardRole.NARRATIVE,
                participant_type=ParticipantType.AI,
                description="Local AI agent running within the CellOS runtime",
                decision_rights=DecisionRight.ADVISORY,
                scope=ScopeDefinition(
                    allowed_actions=["draft", "analyze", "summarize"],
                    forbidden_actions=["publish", "contact_external"],
                ),
                accountability_to="Coordinator",
                kpis=["output_quality"],
            ),
        ],
        participants=[
            Participant(
                id="human-coordinator",
                name="Filip",
                participant_type=ParticipantType.HUMAN,
                role="Coordinator",
                capabilities=["strategy", "approval", "review"],
                availability="business_hours",
                contact_protocol="email:filip@resomnium.com",
            ),
            Participant(
                id="zach-a2a",
                name="Zach (A2A)",
                participant_type=ParticipantType.AI,
                role="A2A Agent",
                capabilities=["task_processing", "analysis", "report_generation"],
                availability="always",
                # The A2A agent card URL — this is a real endpoint
                contact_protocol="a2a:https://resomnium.com/.well-known/agent-card.json",
                metadata={
                    "protocol": "a2a",
                    "agent_card_url": "https://resomnium.com/.well-known/agent-card.json",
                    "transport": "json-rpc",
                    "version": "1.0",
                },
            ),
            Participant(
                id="local-agent",
                name="LocalBot",
                participant_type=ParticipantType.AI,
                role="Local Agent",
                capabilities=["drafting", "analysis", "summarization"],
                availability="always",
                contact_protocol="internal",
            ),
        ],
        handoff_protocols=[
            HandoffProtocol(
                from_role="A2A Agent",
                to_role="Coordinator",
                trigger="task_complete_or_escalation",
                required_context=["result", "confidence_score", "processing_time"],
                validation="Coordinator acknowledges receipt",
            ),
            HandoffProtocol(
                from_role="Local Agent",
                to_role="A2A Agent",
                trigger="needs_external_processing",
                required_context=["task_description", "input_data", "expected_output_format"],
                validation="A2A Agent confirms task acceptance via JSON-RPC",
                fallback_role="Coordinator",
            ),
        ],
    )


def demo_a2a_coordination():
    """Demonstrate coordination between CellOS and an A2A agent."""
    print("=" * 60)
    print("CellOS + A2A Protocol Integration Demo")
    print("=" * 60)

    # Create the cell
    cell = create_a2a_integrated_cell()
    print(f"\nCell: {cell.name}")
    print(f"Participants: {len(cell.participants)}")

    # Show A2A participant details
    a2a_participant = cell.get_participant("zach-a2a")
    print(f"\nA2A Agent: {a2a_participant.name}")
    print(f"  Protocol: {a2a_participant.contact_protocol}")
    print(f"  Agent Card: {a2a_participant.metadata.get('agent_card_url')}")

    # Create runtime and demonstrate coordination
    runtime = CellRuntime(cell)

    # Scope check: A2A agent can process tasks
    check1 = runtime.check_scope("zach-a2a", "process_task: analyze market data")
    print(f"\nScope check - process_task: {'ALLOWED' if check1.allowed else 'DENIED'}")

    # Scope check: A2A agent cannot send emails
    check2 = runtime.check_scope("zach-a2a", "send_email to client@example.com")
    print(f"Scope check - send_email: {'ALLOWED' if check2.allowed else 'DENIED'}")
    print(f"  Reason: {check2.reason}")

    # Create a task and route it
    task = runtime.create_task(
        "Analyze competitor pricing for construction vertical",
        context={"source": "lead_generation_cycle_3", "vertical": "construction"},
    )
    routed = runtime.route_task(task.id)
    assigned = cell.get_participant(routed.assigned_to) if routed.assigned_to else None
    print(f"\nTask routed to: {assigned.name if assigned else 'UNASSIGNED'}")

    # Show how A2A integration would work in practice
    print("\n--- A2A Integration Flow ---")
    print("1. CellOS creates task and checks scope boundaries")
    print("2. Task routed to A2A Agent (Zach)")
    print("3. CellOS sends task via JSON-RPC to A2A endpoint")
    print("   POST https://resomnium.com/.well-known/agent-card.json")
    print("4. A2A Agent processes task asynchronously")
    print("5. On completion, A2A Agent responds via JSON-RPC")
    print("6. CellOS validates response against scope boundaries")
    print("7. Handoff protocol triggers: result + confidence sent to Coordinator")
    print("8. All actions logged in CellOS audit trail")

    # Show audit trail
    print(f"\nAudit trail: {runtime.audit.size} entries logged")
    violations = runtime.audit.get_scope_violations(cell.id)
    print(f"Scope violations: {len(violations)}")

    print("\n" + "=" * 60)
    print("This demonstrates how CellOS extends A2A with:")
    print("  - Scope enforcement (what the A2A agent CAN and CANNOT do)")
    print("  - Accountability (who is responsible for the agent's actions)")
    print("  - Escalation (when the agent should defer to humans)")
    print("  - Audit (full trail of all coordination decisions)")
    print("=" * 60)


if __name__ == "__main__":
    demo_a2a_coordination()
