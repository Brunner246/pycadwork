"""Bundled definition loaders.

Importing this package registers every bundled loader in
:data:`pycadwork.detail.loader.REGISTRY` as a side effect, so by the time
:func:`pycadwork.detail.loader.load_definition` is reachable the native loader
(and the worked foreign example) are already wired in.
"""

from __future__ import annotations

from pycadwork.detail.loaders import _example_foreign, native

__all__ = ["_example_foreign", "native"]
