"""The shipped example cells must model the Cell Framework they teach."""

from pathlib import Path

import pytest
from cellos.diagnostic.analyzer import DiagnosticAnalyzer, Severity
from cellos.schema.loader import load_cell_from_yaml

EXAMPLES = Path(__file__).parent.parent / "examples"
EXAMPLE_CELLS = ["resomnium-cell.yaml", "starter-cell.yaml"]


@pytest.mark.parametrize("filename", EXAMPLE_CELLS)
def test_example_cell_is_complete(filename):
    cell = load_cell_from_yaml(EXAMPLES / filename)
    assert cell.validate_completeness() == []


@pytest.mark.parametrize("filename", EXAMPLE_CELLS)
def test_example_cell_has_no_critical_or_high_findings(filename):
    report = DiagnosticAnalyzer().analyze(load_cell_from_yaml(EXAMPLES / filename))
    serious = [f.title for f in report.findings if f.severity in (Severity.CRITICAL, Severity.HIGH)]
    assert serious == []
