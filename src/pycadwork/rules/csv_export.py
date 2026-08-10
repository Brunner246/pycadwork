"""CSV serialization for a rule report — stdlib ``csv``, stream-based.

The writer takes a text stream, not a path, so callers own the file lifecycle
and tests write to :class:`io.StringIO` — exactly like
:func:`pycadwork.reporting.write_parts_csv`. Severity is written as its name
(``ERROR`` / ``WARNING`` / ``INFO``); a model-wide violation writes its
``element_id`` as the :data:`~pycadwork.rules.records.MODEL_WIDE` sentinel.
"""

from __future__ import annotations

import csv
from typing import TextIO

from pycadwork.rules.records import RuleReport
from pycadwork.rules.severity import Severity


def write_violations_csv(
    report: RuleReport, stream: TextIO, *, min_severity: Severity = Severity.INFO
) -> None:
    """Write a rule report's violations as CSV, one row per violation."""
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["rule_id", "severity", "element_id", "element_type", "message"])
    for violation in report.violations:
        if violation.severity < min_severity:
            continue
        writer.writerow(
            [
                violation.rule_id,
                violation.severity.name,
                violation.element_id,
                violation.element_type,
                violation.message,
            ]
        )
