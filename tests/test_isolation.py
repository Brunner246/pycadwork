"""Architectural fitness: cwapi3d is reachable from one package only.

The rule keeps the package agnostic of any specific cwapi3d version. If
this test starts failing, do not relax it -- route the new cadwork call
through a sub-adapter in ``pycadwork.cadwork_adapter`` instead.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

FORBIDDEN_TOPLEVEL = {
    "cadwork",
    "element_controller",
    "geometry_controller",
    "attribute_controller",
    "list_controller",
    "material_controller",
    "machine_controller",
    "visualization_controller",
    "shop_drawing_controller",
    "file_controller",
    "scene_controller",
    "menu_controller",
    "bim_controller",
    "dimension_controller",
    "endtype_controller",
    "connector_axis_controller",
    "multi_layer_cover_controller",
    "roof_controller",
    "utility_controller",
}

ALLOWED_PREFIX = (Path("src") / "pycadwork" / "cadwork_adapter").as_posix() + "/"

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _python_files() -> list[Path]:
    return list((PROJECT_ROOT / "src" / "pycadwork").rglob("*.py"))


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module.split(".")[0])
    return out


def test_only_cadwork_adapter_package_touches_cadwork_packages():
    offenders: dict[str, set[str]] = {}
    for path in _python_files():
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if rel.startswith(ALLOWED_PREFIX):
            continue
        forbidden_used = _imports(path) & FORBIDDEN_TOPLEVEL
        if forbidden_used:
            offenders[rel] = forbidden_used
    assert not offenders, (
        "These files import cwapi3d directly; route the calls through "
        "pycadwork.cadwork_adapter instead:\n"
        + "\n".join(f"  {p}: {sorted(mods)}" for p, mods in offenders.items())
    )


def test_importing_versioning_does_not_import_gitpython():
    """``import pycadwork.versioning`` must not pull in GitPython.

    GitPython (the ``git`` module) is the optional, often-absent backend; the
    package must import cleanly without it (it is imported lazily, inside
    methods). Run in a subprocess so an earlier in-process test that imported
    ``git`` cannot mask a regression.
    """
    code = (
        "import sys\n"
        "import pycadwork.versioning\n"
        "assert 'git' not in sys.modules, "
        "'GitPython was imported at pycadwork.versioning import time'\n"
    )
    src = PROJECT_ROOT / "src"
    env = {
        "PYTHONPATH": f"{src}{__import__('os').pathsep}{PROJECT_ROOT}",
        "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
        "PATH": __import__("os").environ.get("PATH", ""),
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
