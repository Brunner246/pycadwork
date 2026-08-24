"""In-cadwork probe: report the live userprofile via cwapi3d.

Runs inside cadwork's interpreter (``cadwork open --run-program``). Host tests
must not import this module — it needs ``utility_controller``.
"""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path


def _userprofil_path() -> str:
    import utility_controller as uc

    getter = getattr(uc, "get_user_profil", None) or uc.get_3d_userprofil_path
    return getter()


def main(result_path: str) -> int:
    payload: dict[str, object] = {"ok": False}
    try:
        import utility_controller as uc

        payload["userprofil"] = _userprofil_path()
        payload["plugin_path"] = uc.get_plugin_path()
        payload["env_CADWORK_USP"] = os.environ.get("CADWORK_USP")
        payload["env_CISTART_USP"] = os.environ.get("CISTART_USP")
        payload["ok"] = True
    except Exception as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"
        payload["traceback"] = traceback.format_exc()

    Path(result_path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    try:
        import utility_controller as uc

        uc.close_cadwork_document_unsaved()
    except Exception:
        pass
    return 0 if payload.get("ok") else 1
