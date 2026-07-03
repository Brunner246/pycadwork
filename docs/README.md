# pycadwork documentation

The reference guide for [`pycadwork`](../README.md), split by topic. Start with
the [project README](../README.md) for the overview and quick start.

## Getting set up

- [Installation](installation.md) — dev vs. cadwork-runtime setup, junctions,
  native deps, and developing a plugin as its own `uv` project.
- [Architecture](architecture.md) — the one-seam design, the layer diagram, and
  the package layout table.
- [Design principles](design-principles.md) — the conventions that run through
  the whole codebase.

## The object model

- [The element model](elements.md) — `Element`, the `attrs` / `geometry`
  components, element types, and `from_id` dispatch.
- [The document & project](document.md) — `Document` as the live element
  repository and `ProjectInfo`.
- [Cover objects](covers.md) — `Wall` / `Slab` / `Roof`, `CoverBuilder`, and
  `discover_covers`.
- [Containers and MEP](containers-mep.md) — `Container` containment and the
  `CircularMep` / `RectangularMep` runs.
- [Geometry](geometry.md) — `Point3D`, `Vector3D`, `Frame3D`, B-reps, bounding
  boxes, and the R-tree spatial index.

## Working with the model

- [Connectivity](connectivity.md) — `find_connected` and the whole-model
  contact graph.
- [Collision](collision.md) — `check_collisions` for clash / contact /
  near-miss ("should touch but don't") / clearance, with spatial pruning.
- [Building & storey assignment](building.md) — `StoreyAssigner` and the pure
  `StoreyStack`.
- [Persistence](persistence.md) — mirror the model to normalized SQL and back.
- [Reporting](reporting.md) — cutting lists, material totals, and composable
  grouping dimensions.
- [Rules](rules.md) — validate the model against declarative, composable rules
  and get a pass/fail/severity report.
- [Versioning](versioning.md) — a git workflow over the `.3d` / `.3dc` with diffable
  JSONL.
- [Utilities](utilities.md) — `DisplayRefreshScope`, `batch_apply`, and the
  `auto_*` decorators.

## Contributing

- [Testing](testing.md) — the fake-adapter fixture and how to run the suite.
