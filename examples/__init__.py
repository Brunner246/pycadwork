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
* :mod:`examples.collision`            — clash / contact / near-miss / clearance checks
* :mod:`examples.raycast`              — cast_ray: which elements a ray hits, nearest-first
* :mod:`examples.building_storeys`     — StoreyStack and StoreyAssigner
* :mod:`examples.utilities`            — DisplayRefreshScope, suppressed_display, batch_apply
* :mod:`examples.decorators`           — pure-Python class decorators (auto_repr, auto_eq)
* :mod:`examples.persistence`          — mirror the model to SQL and back
* :mod:`examples.persistence_queries`  — read the model into SQL, then query it (BuildingQuery)
* :mod:`examples.sql_builder`          — the table-as-data SQL builder; query a pulled model
* :mod:`examples.reporting`            — cutting lists and material totals over a snapshot
* :mod:`examples.rules`                — validate the model against declarative rules
* :mod:`examples.versioning`           — a git workflow over the model: commit, branch, restore

Three scripts are **not** in the ``MODULES`` tour because they need a live model
and a real git repository, so they only run inside cadwork (not under the fake
adapter). All git work in them goes through the :class:`ModelVersioning` facade —
no raw ``git`` / ``subprocess``:

* :mod:`examples.versioning_in_cadwork` — commit the live model to a real git repo,
  then branch / diff / merge (run from cadwork's API menu; see its module docstring)
* :mod:`examples.versioning_branch_workflow` — branch + 5 beams + push, then switch
  back to ``main`` without merging
* :mod:`examples.versioning_idle_session` — the same lifecycle as a copy-paste
  session for cadwork's interactive Python shell (IDLE)
* :mod:`examples.versioning_dock_widget` — a PyQt6 (MVVM) dock widget that docks
  into cadwork's main window to commit / branch / push / pull / revert the live
  model interactively (needs PyQt6 in addition to the git backend)

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
    "collision",
    "raycast",
    "building_storeys",
    "utilities",
    "decorators",
    "persistence",
    "persistence_queries",
    "sql_builder",
    "reporting",
    "rules",
    "versioning",
)

__all__ = ["MODULES"]
