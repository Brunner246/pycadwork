"""Runnable, learn-by-reading examples for every pycadwork subsystem.

Each module here mirrors one area of the package layout and holds a handful of
small ``demo_*`` functions plus a module-level ``run()`` that calls them in
order. Read them top to bottom to learn the API, or run one directly:

    uv run python -m examples.geometry_basics

Every module is exercised by ``tests/test_examples.py``, which runs each
``run()`` against the in-memory fake adapter — so these examples are guaranteed
to stay in step with the real public API on every CI run.

Modules:

* :mod:`examples.geometry_basics`      — pure geometry value-types (no cadwork)
* :mod:`examples.elements`             — Beam / Plate / Drilling: create, read, write-back
* :mod:`examples.document_and_project` — the Document repository and ProjectInfo
* :mod:`examples.covers`               — Wall / Slab / Roof, CoverBuilder, discover_covers
* :mod:`examples.containers_and_mep`   — Container containment and MEP runs
* :mod:`examples.connectivity`         — find_connected and the connection graph
* :mod:`examples.building_storeys`     — StoreyStack and StoreyAssigner
* :mod:`examples.utilities`            — DisplayRefreshScope and batch_apply
* :mod:`examples.persistence`          — mirror the model to SQL and back
* :mod:`examples.sql_builder`          — the table-as-data SQL builder; query a pulled model

.. note::

   A few examples need model state that, in a real project, is produced by the
   cadwork UI (a flagged wall, a building's BMT storeys). To stay runnable
   standalone, those examples seed that state through the version-isolation seam
   (``pycadwork.cadwork_adapter.cadwork``). Each such call is clearly marked as
   *setup that mimics the cadwork UI* — it is not part of normal day-to-day use.
"""

from __future__ import annotations

#: The example module names, in learning order — also used by the test suite.
MODULES: tuple[str, ...] = (
    "geometry_basics",
    "elements",
    "document_and_project",
    "covers",
    "containers_and_mep",
    "connectivity",
    "building_storeys",
    "utilities",
    "persistence",
    "sql_builder",
)

__all__ = ["MODULES"]
