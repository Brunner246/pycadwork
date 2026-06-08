# pycadwork examples

Runnable, learn-by-reading examples — one module per subsystem of the package.
Read them top to bottom to learn the API, or run any one directly.

```bash
uv run python -m examples.geometry_basics   # pure geometry — runs anywhere
```

Each module has several small `demo_*` functions and a module-level `run()` that
calls them in order, with comments and `print(...)` of the interesting result.

| Module | Teaches |
| --- | --- |
| [`geometry_basics.py`](geometry_basics.py) | `Point3D` / `Vector3D` algebra, `Frame3D`, AABB, and the creation specs (`RectSection`, `AxisPoints`, …) |
| [`elements.py`](elements.py) | Create `Beam` / `Plate` / `Drilling`; read `attrs` & `geometry`; write dimensions back; `from_id` |
| [`document_and_project.py`](document_and_project.py) | The `Document` repository (`elements`, `elements_of`, `get`, `covers`) and `ProjectInfo` metadata |
| [`covers.py`](covers.py) | `Wall` / `Slab` / `Roof`, `children_of`, the `CoverBuilder`, and `discover_covers` |
| [`containers_and_mep.py`](containers_and_mep.py) | `Container.create_from_standard`, `parent_container`, `discover_containers`; `CircularMep` / `RectangularMep` |
| [`connectivity.py`](connectivity.py) | `find_connected`, `build_connection_graph`, components, and a custom contact predicate |
| [`building_storeys.py`](building_storeys.py) | The pure `StoreyStack` classifier and the model-driven `StoreyAssigner` |
| [`utilities.py`](utilities.py) | `DisplayRefreshScope` (context + `@auto_recreate`) and `batch_apply` |
| [`persistence.py`](persistence.py) | `open_sqlite`, `Synchronizer` pull/push, `ModelReader`, `diff`, and raw SQL |
| [`sql_builder.py`](sql_builder.py) | The table-as-data SQL builder (`Table` / `Column`, `create_table`, `Insert` / `Update` / `Delete` / `Select`), then using it to query a pulled model |

## Running inside cadwork vs. anywhere

The examples use only the public `pycadwork` API. One of them — `geometry_basics`
— touches no live model and runs in any interpreter. The rest *create elements*
(including `persistence` and `sql_builder`, which mirror a real model), so they
run fully **inside cadwork** (where the real adapter is live) or **under the test
suite's in-memory fake**.

A handful seed model state that a real project gets from the cadwork UI — a beam
flagged as a wall, a building's BMT storeys. Those steps go through the
version-isolation seam (`pycadwork.cadwork_adapter.cadwork`) and are clearly
commented as *setup that mimics the cadwork UI*. They are not part of normal
day-to-day pycadwork usage.

## Verified in CI

`tests/test_examples.py` runs every module's `run()` against the fake adapter, so
these examples are guaranteed to stay in step with the public API:

```bash
uv run pytest tests/test_examples.py
```
