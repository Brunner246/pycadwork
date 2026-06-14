"""The native loader: ``schema = "pycadwork.detail"``.

The native shape is exactly what :meth:`DetailDefinition.to_dict` emits, so the
loader is a thin pass-through to :meth:`DetailDefinition.from_dict`. It registers
for both the current native version and ``"*"`` (any version), so a definition
written by a future minor revision still round-trips through the same decoder.
"""

from __future__ import annotations

from typing import Any

from pycadwork.detail.definition import NATIVE_SCHEMA, NATIVE_VERSION, DetailDefinition
from pycadwork.detail.loader import register_loader


@register_loader
class NativeLoader:
    """Loads pycadwork's own detail JSON."""

    schema = NATIVE_SCHEMA
    versions = (NATIVE_VERSION, "*")

    def load(self, raw: dict[str, Any]) -> DetailDefinition:
        return DetailDefinition.from_dict(raw)
