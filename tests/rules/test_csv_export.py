"""write_violations_csv: header, rows, severity name, min_severity filter."""

from __future__ import annotations

import io

from pycadwork.rules import RuleReport, Severity, Violation, write_violations_csv


def _report() -> RuleReport:
    return RuleReport(
        violations=(
            Violation(Severity.ERROR, "dims", 2, "plate", "too wide"),
            Violation(Severity.WARNING, "has-material", 3, "beam", "no material"),
            Violation(Severity.INFO, "prod", -1, "", "model-wide note"),
        )
    )


def test_header_and_rows() -> None:
    stream = io.StringIO()
    write_violations_csv(_report(), stream)
    lines = stream.getvalue().splitlines()
    assert lines[0] == "rule_id,severity,element_id,element_type,message"
    assert lines[1] == "dims,ERROR,2,plate,too wide"
    assert lines[3] == "prod,INFO,-1,,model-wide note"


def test_min_severity_filters_rows() -> None:
    stream = io.StringIO()
    write_violations_csv(_report(), stream, min_severity=Severity.WARNING)
    body = stream.getvalue().splitlines()[1:]
    assert all("INFO" not in line for line in body)
    assert len(body) == 2


def test_empty_report_writes_only_the_header() -> None:
    stream = io.StringIO()
    write_violations_csv(RuleReport(), stream)
    assert stream.getvalue().splitlines() == [
        "rule_id,severity,element_id,element_type,message"
    ]
