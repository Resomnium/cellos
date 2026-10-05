# CellOS

**Open Framework for Human-AI Organizational Coordination**

CellOS provides formal coordination protocols for teams where humans and AI agents work together. It solves the gap between "we have AI agents" and "our organization actually works with them."

## The Problem

Organizations adopt AI agents but have no standards for:
- Who (human or AI) is responsible for what
- How work transitions between human and AI participants
- When AI should escalate to human judgment
- What actions are within an agent's authority

CellOS fills this gap with three layers.

## Three Layers

### 1. Cell Schema

A formal specification for defining **cells** — small autonomous teams (2-15 participants) with explicit roles, scope boundaries, and accountability chains.

```yaml
# Define a cell in YAML
id: my-team
name: Product Cell
roles:
  - name: Product Lead
    steward_role: clarity
    participant_type: human
    decision_rights: full
  - name: Research Agent
    participant_type: ai
    decision_rights: conditional
    scope:
      allowed_actions: [search, analyze, summarize]
      forbidden_actions: [publish, purchase]
    accountability_to: Product Lead
```

### 2. Coordination Engine

A Python runtime that enforces cell coordination: scope checking, task routing, handoff protocols, escalation triggers, and audit logging.

```python
from cellos import CellRuntime
from cellos.schema.loader import load_cell_from_yaml

cell = load_cell_from_yaml("my-cell.yaml")
runtime = CellRuntime(cell)

# Check if an action is within scope
result = runtime.check_scope("research-bot", "search web for competitors")
# ScopeCheckResult(allowed=True, reason="Action within defined scope")

result = runtime.check_scope("research-bot", "publish blog post")
# ScopeCheckResult(allowed=False, reason="Action 'publish' is explicitly forbidden")

# Create and route tasks
task = runtime.create_task("Analyze competitor pricing")
runtime.route_task(task.id)  # Routes to best-matching participant
```

### 3. Diagnostic Toolkit

Analyzes your cell definitions for AI-readiness issues:

```bash
cellos diagnose my-cell.yaml
```

```
# Diagnostic Report: Product Cell
**Overall Score:** 72/100

## CRITICAL (1)
**AI role 'Research Agent' has no accountability chain**
  Role has AI participants but no defined accountability to a human.
  *Recommendation:* Set accountability_to to a human-occupied role.

## HIGH (2)
**Missing steward role: integrity**
  ...
```

## Installation

```bash
pip install cellos
```

## Quick Start

```python
from cellos import Cell, Role, Participant, StewardRole, ParticipantType, CellRuntime

# Define a cell programmatically
cell = Cell(
    id="my-cell",
    name="My First Cell",
    roles=[
        Role(
            name="Director",
            steward_role=StewardRole.CLARITY,
            participant_type=ParticipantType.HUMAN,
        ),
        Role(
            name="Assistant",
            participant_type=ParticipantType.AI,
            accountability_to="Director",
        ),
    ],
    participants=[
        Participant(id="alice", name="Alice", participant_type=ParticipantType.HUMAN, role="Director"),
        Participant(id="bot-1", name="AssistantBot", participant_type=ParticipantType.AI, role="Assistant"),
    ],
)

# Run diagnostics
from cellos.diagnostic import DiagnosticAnalyzer
report = DiagnosticAnalyzer().analyze(cell)
print(report.to_markdown())
```

## The Cell Framework

CellOS implements the **Cell Framework** — an organizational design methodology where:

- **Cells** are small (2-15 participant) autonomous units
- Every cell has **5 steward roles**: Clarity, Execution, Narrative, Access, Integrity
- Human and AI participants have **explicit scope boundaries**
- **Accountability chains** ensure every AI action has a human accountable
- **Handoff protocols** define how work transitions between participants
- **Escalation rules** define when AI should defer to human judgment

## Examples

See the `examples/` directory for real-world cell definitions, including Resomnium's own operational cell.

## License

Apache 2.0

## About

Built by [Resomnium](https://resomnium.com) — organizational design for the AI age.

Application pending with [NGI Zero Commons Fund](https://nlnet.nl/commonsfund/).
