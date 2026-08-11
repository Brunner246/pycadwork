"""In-cadwork body for the versioning run-program integration test.

The host writes a thin wrapper that calls :func:`main` with a baked result path
(cadwork may not inherit host env). Proves the model-aware commit → branch →
edit → ``checkout`` loop and writes a JSON result sidecar.

No FakeCadworkAdapter: real cadwork APIs only. Not collected as a pytest module.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

FEATURE_BRANCH = "feature/it"
MARKER_NAME = "pycadwork-it-marker"
RESULT_ENV = "PYCADWORK_IT_RESULT_PATH"

# Host wrappers may assign this before calling main() / run().
RESULT_PATH: str | None = None


def _ensure_git_identity() -> None:
    """Force a deterministic commit identity inside cadwork's process."""
    os.environ.setdefault("GIT_AUTHOR_NAME", "pycadwork-it")
    os.environ.setdefault("GIT_AUTHOR_EMAIL", "it@pycadwork.test")
    os.environ.setdefault("GIT_COMMITTER_NAME", "pycadwork-it")
    os.environ.setdefault("GIT_COMMITTER_EMAIL", "it@pycadwork.test")


def _result_path() -> Path:
    raw = RESULT_PATH or os.environ.get(RESULT_ENV)
    if not raw:
        raise RuntimeError(
            f"neither RESULT_PATH nor {RESULT_ENV} is set — the host harness "
            "must point the run-program script at a result sidecar path"
        )
    return Path(raw)


def _write_result(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _marker_count() -> int:
    from pycadwork import Beam, Document

    return sum(1 for b in Document().elements_of(Beam) if b.attrs.name == MARKER_NAME)


def _add_marker_beam() -> int:
    from pycadwork import AxisPoints, Beam, Point3D, RectSection

    beam = Beam.create_rectangular(
        RectSection(width=100.0, height=200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(1000, 0, 0), Point3D(0, 0, 1)),
    )
    beam.attrs.name = MARKER_NAME
    beam.attrs.group = "pycadwork-it"
    return beam.id


def run() -> dict:
    """Execute the versioning loop; return a JSON-serializable result payload."""
    from pycadwork import Document
    from pycadwork.versioning import ModelVersioning, is_git_available

    _ensure_git_identity()

    if not Document().file_path:
        return {
            "ok": False,
            "error": "model is unsaved — host must open a fixture with a path",
        }
    if not is_git_available():
        return {
            "ok": False,
            "error": "git / GitPython unavailable inside cadwork interpreter",
        }

    vcs = ModelVersioning.open()
    baseline_branch = vcs.current_branch()
    vcs.commit("baseline")

    if FEATURE_BRANCH in vcs.branches():
        # Pure-git delete of a leftover branch from a previous aborted run.
        vcs.checkout(baseline_branch, apply_to_model=False)
        vcs.delete_branch(FEATURE_BRANCH, force=True)

    vcs.create_branch(FEATURE_BRANCH)  # checkout=True by default
    marker_id = _add_marker_beam()
    markers_on_feature = _marker_count()
    if markers_on_feature < 1:
        return {
            "ok": False,
            "error": "marker beam missing after create",
            "marker_id": marker_id,
        }

    vcs.commit("feature change")

    # Model-aware default: git checkout + load baseline into the live model.
    report = vcs.checkout(baseline_branch)
    markers_after = _marker_count()
    if markers_after != 0:
        return {
            "ok": False,
            "error": "marker still present after model-aware checkout to baseline",
            "baseline_branch": baseline_branch,
            "markers_on_feature": markers_on_feature,
            "markers_after_checkout": markers_after,
            "marker_id": marker_id,
            "checkout_report_type": type(report).__name__ if report is not None else None,
        }

    return {
        "ok": True,
        "baseline_branch": baseline_branch,
        "feature_branch": FEATURE_BRANCH,
        "markers_on_feature": markers_on_feature,
        "markers_after_checkout": markers_after,
        "marker_id": marker_id,
        "checkout_report_type": type(report).__name__ if report is not None else None,
        "apply_to_model_default": True,
    }


def main(result_path: str | Path | None = None) -> int:
    """Entry point for cadwork ``/RUNPROGRAM``.

    ``result_path`` overrides the module-level / env configuration when provided.
    """
    global RESULT_PATH
    if result_path is not None:
        RESULT_PATH = str(result_path)
    path = _result_path()
    try:
        payload = run()
    except Exception as exc:  # pragma: no cover - exercised only inside cadwork
        payload = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
        _write_result(path, payload)
        print(f"pycadwork IT failed: {payload['error']}", file=sys.stderr)
        return 1

    _write_result(path, payload)
    if not payload.get("ok"):
        print(f"pycadwork IT assertion failed: {payload.get('error')}", file=sys.stderr)
        return 1
    print("pycadwork IT ok:", json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
