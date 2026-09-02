"""Validate a live model with a ``.feature`` file compiled through rules.

:mod:`pycadwork.gherkin` is a driving adapter over :mod:`pycadwork.rules`: it
parses a documented Gherkin subset, compiles each ``Then`` into ``Rule``
objects, and runs them through :func:`~pycadwork.rules.check`. It does **not**
replace the linter. The snapshot is injected, so the same file is valid
against the **live model** (``ModelReader().read()``) or the test suite's
fake adapter.

    uv run python -m examples.gherkin

Reading the live model needs a backend, so ``run()`` executes inside cadwork or
under the test suite's fake adapter.
"""

from __future__ import annotations

from pathlib import Path

from pycadwork import AxisPoints, Beam, Point3D, RectSection, run_features
from pycadwork.persistence import ModelReader

_FEATURE = Path(__file__).resolve().parent / "features" / "framing.feature"


def _seed_model() -> list[Beam]:
    """Three 80 mm pine studs classified as IfcBeam — the feature's happy path."""
    studs = [
        Beam.create_rectangular(
            RectSection(80.0, 200.0),
            AxisPoints(Point3D(x, 0, 0), Point3D(x, 0, 2900), Point3D(x + 1, 0, 0)),
        )
        for x in (0.0, 600.0, 1200.0)
    ]
    for stud in studs:
        stud.attrs.name = "Stud"
        stud.attrs.material_name = "Pine"
        stud.attrs.ifc_type = "IfcBeam"
    return studs


def demo_pass() -> None:
    """The feature matches the seeded model — ``report.ok`` is the test gate."""
    report = run_features(ModelReader().read(), _FEATURE)
    print(f"  pass ok={report.ok} scenarios={len(report.scenarios)}")
    print(f"  rules_run={len(report.rules_run)} failures={len(report.failures)}")


def demo_fail(studs: list[Beam]) -> None:
    """One stud's material drifts; the same feature names the step and element."""
    studs[0].attrs.material_name = "Oak"
    report = run_features(ModelReader().read(), _FEATURE)
    print(f"  fail ok={report.ok} failures={len(report.failures)}")
    for failure in report.failures:
        print(
            f"  {failure.scenario} | {failure.step} | "
            f"#{failure.element_id} {failure.message}"
        )


def run() -> None:
    """Seed the model, show a passing feature run, then a failing one."""
    studs = _seed_model()
    demo_pass()
    demo_fail(studs)


if __name__ == "__main__":
    run()
