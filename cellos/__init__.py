"""CellOS - Open Framework for Human-AI Organizational Coordination.

CellOS provides formal coordination protocols for teams where humans
and AI agents work together. It defines roles, accountability, handoffs,
and oversight between human and AI participants.

Three layers:
    1. Cell Schema - Formal specification for organizational cells
    2. Coordination Engine - Runtime coordination protocols
    3. Diagnostic Toolkit - Organizational AI-readiness assessment
"""

__version__ = "0.1.0"

from cellos.schema.models import (
    Cell,
    CellConfig,
    Participant,
    ParticipantType,
    Role,
    StewardRole,
)
from cellos.engine.cell_runtime import CellRuntime
from cellos.engine.coordinator import Coordinator

__all__ = [
    "Cell",
    "CellConfig",
    "CellRuntime",
    "Coordinator",
    "Participant",
    "ParticipantType",
    "Role",
    "StewardRole",
]
