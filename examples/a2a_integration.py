"""Example: Integrating CellOS with the Google A2A Protocol.

Shows how CellOS cell definitions can reference A2A agent cards,
so an external A2A-compatible agent can sit inside a cell with the
same scope, accountability and audit rules as any other participant.

The A2A participant here is Zach, Resomnium's public inbox:
https://resomnium.com/.well-known/agent-card.json
Zach accepts a message, emails it to a human, and returns a receipt
that says exactly that. It does not answer, analyze, or decide.
"""

from __future__ import annotations

from cellos import (
    Cell,
    CellRuntime,
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

    Two of the five human stewards are shown. Each agent works beneath
    the steward whose function it serves: the inbox beneath Access,
    the local agent beneath Execution.
    """
    return Cell(
        id="a2a-demo",
        name="A2A-Integrated Cell",
        mandate="Demonstrate cross-protocol coordination between CellOS and A2A agents",
        roles=[
            Role(
                name="Access Steward",
                steward_role=StewardRole.ACCESS,
                participant_type=ParticipantType.HUMAN,
                description="Owns the doors. Every inbound A2A message lands with this human.",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["reply_to_inquiry", "engage_client", "review"]),
                kpis=["inquiry_reply_time"],
            ),
            Role(
                name="Execution Steward",
                steward_role=StewardRole.EXECUTION,
                participant_type=ParticipantType.HUMAN,
                description="Owns the doing. Turns accepted work into tasks for the agents beneath.",
                decision_rights=DecisionRight.FULL,
                scope=ScopeDefinition(allowed_actions=["assign_task", "approve", "review"]),
                kpis=["on_time_delivery_rate"],
            ),
            Role(
                name="A2A Inbox",
                participant_type=ParticipantType.AI,
                description=(
                    "External agent reachable via the Google A2A protocol. Accepts "
                    "message/send, emails the message to a human, returns a receipt."
                ),
                decision_rights=DecisionRight.NONE,
                scope=ScopeDefinition(
                    allowed_actions=["receive_message", "relay_to_email", "issue_receipt"],
                    forbidden_actions=["reply_to_inquiry", "process_task", "make_commitment"],
                ),
                accountability_to="Access Steward",
                escalation_rules=[
                    EscalationRule(
                        trigger=EscalationTrigger.ERROR,
                        target_role="Access Steward",
                    ),
                    EscalationRule(
                        trigger=EscalationTrigger.TIMEOUT,
                        target_role="Access Steward",
                        timeout_seconds=300,  # 5-minute timeout for A2A responses
                    ),
                ],
                kpis=["delivery_success_rate"],
            ),
            Role(
                name="Local Agent",
                participant_type=ParticipantType.AI,
                description="Local AI agent running within the CellOS runtime",
                decision_rights=DecisionRight.ADVISORY,
                scope=ScopeDefinition(
                    allowed_actions=["draft", "analyze", "summarize"],
                    forbidden_actions=["publish", "contact_external"],
                ),
                accountability_to="Execution Steward",
                escalation_rules=[
                    EscalationRule(
                        trigger=EscalationTrigger.SCOPE_BOUNDARY,
                        target_role="Execution Steward",
                    ),
                    EscalationRule(
                        trigger=EscalationTrigger.CONFIDENCE_LOW,
                        target_role="Execution Steward",
                        threshold=0.7,
                    ),
                ],
                kpis=["output_quality"],
            ),
        ],
        participants=[
            Participant(
                id="access-steward",
                name="Access Steward",
                participant_type=ParticipantType.HUMAN,
                role="Access Steward",
                capabilities=["client_engagement", "review"],
                availability="business_hours",
                contact_protocol="email",
            ),
            Participant(
                id="execution-steward",
                name="Execution Steward",
                participant_type=ParticipantType.HUMAN,
                role="Execution Steward",
                capabilities=["delivery", "review"],
                availability="business_hours",
                contact_protocol="email",
            ),
            Participant(
                id="zach-a2a",
                name="Zach (A2A)",
                participant_type=ParticipantType.AI,
                role="A2A Inbox",
                capabilities=["receive_message", "relay_to_email", "issue_receipt"],
                availability="always",
                # The A2A agent card URL - this is a real endpoint
                contact_protocol="a2a:https://resomnium.com/.well-known/agent-card.json",
                metadata={
                    "protocol": "a2a",
                    "agent_card_url": "https://resomnium.com/.well-known/agent-card.json",
                    "transport": "json-rpc",
                    "mode": "honest-inbox",
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
                from_role="A2A Inbox",
                to_role="Access Steward",
                trigger="message_received",
                required_context=["sender", "message", "receipt_id"],
                validation="Access Steward replies or declines",
            ),
            HandoffProtocol(
                from_role="Access Steward",
                to_role="Execution Steward",
                trigger="work_accepted",
                required_context=["client", "agreed_scope", "deadline"],
                validation="Execution Steward accepts the scope as a peer",
            ),
            HandoffProtocol(
                from_role="Local Agent",
                to_role="Execution Steward",
                trigger="task_complete_or_escalation",
                required_context=["result", "confidence_score"],
                validation="Execution Steward reviews output",
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

    # Scope check: the inbox relays messages to a human
    check1 = runtime.check_scope("zach-a2a", "relay_to_email inbound message")
    print(f"\nScope check - relay_to_email: {'ALLOWED' if check1.allowed else 'DENIED'}")

    # Scope check: the inbox does not do the work itself
    check2 = runtime.check_scope("zach-a2a", "process_task: analyze market data")
    print(f"Scope check - process_task: {'ALLOWED' if check2.allowed else 'DENIED'}")
    print(f"  Reason: {check2.reason}")

    # Work the Access Steward accepted goes to the agent beneath the Execution Steward
    task = runtime.create_task(
        "Analyze competitor pricing for construction vertical",
        context={"source": "a2a_inquiry", "vertical": "construction"},
    )
    assigned = runtime.assign_task(task.id, "local-agent")
    agent = cell.get_participant(assigned.assigned_to)
    steward = cell.get_role(assigned.assigned_role).accountability_to
    print(f"\nTask assigned to: {agent.name} (beneath {steward})")

    # Show how A2A integration works in practice
    print("\n--- A2A Integration Flow ---")
    print("1. An external agent reads Zach's agent card")
    print("   GET https://resomnium.com/.well-known/agent-card.json")
    print("2. It sends message/send to the endpoint the card lists")
    print("3. Zach emails the message to a human and returns a receipt saying so")
    print("4. Handoff protocol: message, sender and receipt go to the Access Steward")
    print("5. The Access Steward decides. Accepted work goes to the Execution Steward as a peer")
    print("6. The Execution Steward assigns it to the Local Agent, inside that agent's scope")
    print("7. All actions logged in CellOS audit trail")

    # Show audit trail
    print(f"\nAudit trail: {runtime.audit.size} entries logged")
    violations = runtime.audit.get_scope_violations(cell.id)
    print(f"Scope violations: {len(violations)}")

    print("\n" + "=" * 60)
    print("This demonstrates how CellOS extends A2A with:")
    print("  - Scope enforcement (what the A2A agent CAN and CANNOT do)")
    print("  - Accountability (each agent answers to the human steward it works beneath)")
    print("  - Escalation (when the agent should defer to humans)")
    print("  - Audit (full trail of all coordination decisions)")
    print("=" * 60)


if __name__ == "__main__":
    demo_a2a_coordination()
