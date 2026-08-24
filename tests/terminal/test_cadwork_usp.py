"""Real-cadwork IT: ``cadwork open --usp`` must be the profile 3d actually loads.

Host-only. Writes a run-program that calls ``utility_controller.get_3d_userprofil_path``
(or ``get_user_profil`` if present), launches via the CLI, and asserts the sidecar
path is under the requested USP — not the registry default.

Opt-in: ``PYCADWORK_CADWORK_IT=1``. Skips when ``3d.exe`` is missing so
default CI stays green. Close any running 3d first (single-instance ignores ``/USP``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
import uuid
from pathlib import Path

import pytest

from pycadwork.terminal.cli import main as cadwork_main
from pycadwork.terminal.launcher import ExecutableNotFoundError, find_3d_exe
from pycadwork.terminal.registry import read_env_value, restore_values

IT_ENV = "PYCADWORK_CADWORK_IT"
SCRIPT_SOURCE = Path(__file__).resolve().parent / "_usp_probe.py"
RESULT_WAIT_S = 180
RESULT_POLL_S = 1.0

_CHARTS_USP = Path(r"D:\cadwork\userprofil_2026_charts")
_DEFAULT_USP = Path(r"D:\cadwork\userprofil_2026")
_MODEL_CANDIDATES = (
    Path(r"C:\Users\MichaelBrunner\Downloads\test_elements_walls.3d"),
    _DEFAULT_USP / "3d" / "INIT" / "CH_Holzbau.3d",
)


def _3d_available() -> bool:
    try:
        find_3d_exe()
        return True
    except ExecutableNotFoundError:
        return False


def _image_running(name: str) -> bool:
    if os.name != "nt":
        return False
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH"],
            text=True,
            errors="replace",
        )
    except OSError:
        return False
    return name.lower() in out.lower()


pytestmark = pytest.mark.skipif(
    os.environ.get(IT_ENV) != "1" or not _3d_available(),
    reason=f"set {IT_ENV}=1 and install cadwork (3d.exe) to run this IT",
)


def _norm(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _under(child: Path, parent: Path) -> bool:
    c, p = _norm(child), _norm(parent)
    return c == p or c.startswith(p + os.sep)


def _short_work_dir() -> Path:
    root = Path(tempfile.gettempdir()) / f"cwit-usp-{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _pick_model() -> Path:
    override = os.environ.get("PYCADWORK_IT_MODEL")
    if override:
        path = Path(override)
        if path.is_file():
            return path
    for candidate in _MODEL_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise pytest.skip("no .3d model found (set PYCADWORK_IT_MODEL)")


def _prepare_usp(work: Path) -> Path:
    """A distinct USP copy so registry fallback is detectable."""
    dest = work / "userprofil_2026_it"
    src = (
        Path(os.environ["PYCADWORK_IT_USP"])
        if os.environ.get("PYCADWORK_IT_USP")
        else (_CHARTS_USP if _CHARTS_USP.is_dir() else None)
    )
    if src is not None and src.is_dir():
        shutil.copytree(src, dest)
    else:
        dest.mkdir()
        (dest / "3d").mkdir()
    init_src = _DEFAULT_USP / "3d" / "INIT"
    init_dst = dest / "3d" / "INIT"
    if init_src.is_dir() and not init_dst.exists():
        shutil.copytree(init_src, init_dst)
    lang = _DEFAULT_USP / "LANG"
    if lang.is_file() and not (dest / "LANG").exists():
        shutil.copy2(lang, dest / "LANG")
    return dest


def _write_run_program(work: Path, result_path: Path) -> Path:
    body = work / "_usp_probe.py"
    shutil.copy2(SCRIPT_SOURCE, body)
    entry = work / "run_program.py"
    result_literal = str(result_path.resolve())
    body_dir = str(body.parent.resolve())
    entry.write_text(
        textwrap.dedent(f"""\
            import json
            import sys
            import traceback
            from pathlib import Path

            _here = Path(r"{body_dir}")
            if str(_here) not in sys.path:
                sys.path.insert(0, str(_here))

            _result = Path(r"{result_literal}")
            try:
                import _usp_probe as _probe
                raise SystemExit(_probe.main(str(_result)))
            except SystemExit:
                raise
            except Exception as exc:
                _result.write_text(
                    json.dumps(
                        {{
                            "ok": False,
                            "error": f"{{type(exc).__name__}}: {{exc}}",
                            "traceback": traceback.format_exc(),
                        }},
                        indent=2,
                        sort_keys=True,
                    )
                    + "\\n",
                    encoding="utf-8",
                )
                raise SystemExit(1) from exc
            """),
        encoding="utf-8",
    )
    return entry


def _wait_for_result(result_path: Path, timeout_s: float = RESULT_WAIT_S) -> dict:
    deadline = time.monotonic() + timeout_s
    last_error: str | None = None
    while time.monotonic() < deadline:
        if result_path.is_file():
            try:
                text = result_path.read_text(encoding="utf-8")
                if text.strip():
                    return json.loads(text)
            except (OSError, json.JSONDecodeError) as exc:
                last_error = str(exc)
        time.sleep(RESULT_POLL_S)
    detail = f" last read error: {last_error}" if last_error else ""
    raise AssertionError(
        f"run-program did not produce a result sidecar at {result_path} "
        f"within {timeout_s}s.{detail} Close running 3d, then retry."
    )


def test_open_usp_is_the_profile_3d_reports() -> None:
    if _image_running("3d.exe"):
        pytest.skip(
            "3d.exe is already running — close it; /USP cannot switch a live instance"
        )

    work = _short_work_dir()
    saved_registry = {
        "CADWORK_USP": read_env_value("CADWORK_USP"),
        "CISTART_USP": read_env_value("CISTART_USP"),
    }
    try:
        usp = _prepare_usp(work)
        model = work / "model.3d"
        shutil.copy2(_pick_model(), model)
        result_path = work / "usp-result.json"
        script = _write_run_program(work, result_path)

        argv = [
            "open",
            str(model),
            "--usp",
            str(usp),
            "--run-program",
            str(script),
            "--no-gui",
        ]
        exe = Path(r"D:\cadwork.dir\exe_2026")
        if exe.is_dir():
            argv.extend(["--exe", str(exe)])

        cadwork_main(argv)

        payload = _wait_for_result(result_path)
        assert payload.get("ok") is True, payload

        reported = Path(str(payload["userprofil"]))
        assert _under(reported, usp), (
            f"3d loaded {reported} but --usp was {usp}. "
            f"registry CADWORK_USP={read_env_value('CADWORK_USP')!r}; "
            f"env_CADWORK_USP={payload.get('env_CADWORK_USP')!r}; "
            f"plugin_path={payload.get('plugin_path')!r}"
        )
        registry = read_env_value("CADWORK_USP")
        if registry and not _under(usp, Path(registry)):
            assert not _under(
                reported, Path(registry)
            ), f"--usp {usp} was ignored; 3d still on registry profile {reported}"
    finally:
        restore_values(saved_registry)
        shutil.rmtree(work, ignore_errors=True)
