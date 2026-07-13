"""pycadwork.ops — boolean, cutting, and process operations on elements.

cwapi3d exposes these as flat ``element_controller`` functions with
CAD-jargon names (``solder``, ``subtract``) and a cutters-first argument
order (``hard`` = cutters, ``soft`` = targets). This module renames them to
say what happens to the model and operates on :class:`Element` objects:

* :func:`union` / :func:`difference` / :func:`split` — boolean solids;
  ``difference(targets, cutters)`` reads as ``targets − cutters``, the flip
  to cwapi3d's cutters-first order happens here.
* :func:`cut_with_plane`, :func:`slice_with_plane`, :func:`cut_with_miter`,
  :func:`cut_with_overmeasure`, :func:`cut_with_processing_group`,
  :func:`cut_cross_lap` — cuts.
* :func:`extract_cutting_bodies` / :func:`cutting_bodies` /
  :func:`delete_processes` / :func:`delete_end_types` — process management.
  ``cutting_bodies`` is a context manager around the Ctrl+D extraction that
  restores the model on exit (re-subtract the surviving bodies, delete
  them); the restore reproduces the cut geometry, not the parametric
  processes themselves.

Multi-element parameters accept a single :class:`Element` or any iterable
of them.
"""

from __future__ import annotations

from pycadwork.ops.boolean import (
    cut_cross_lap,
    cut_with_miter,
    cut_with_overmeasure,
    cut_with_plane,
    cut_with_processing_group,
    difference,
    slice_with_plane,
    split,
    union,
)
from pycadwork.ops.processes import (
    CuttingBodyExtraction,
    cutting_bodies,
    delete_end_types,
    delete_processes,
    extract_cutting_bodies,
)

__all__ = [
    "CuttingBodyExtraction",
    "cut_cross_lap",
    "cut_with_miter",
    "cut_with_overmeasure",
    "cut_with_plane",
    "cut_with_processing_group",
    "cutting_bodies",
    "delete_end_types",
    "delete_processes",
    "difference",
    "extract_cutting_bodies",
    "slice_with_plane",
    "split",
    "union",
]
