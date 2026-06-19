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
| [`details.py`](details.py) | Author a detail **by type** with `DetailBuilder().of_type(...)`; `to_json`/`from_json`; `load_definition` (native + foreign schema); realize with `build_detail` |
| [`edge_detail.py`](edge_detail.py) | Author the **AW260** corner edge pair (two 260 mm framed walls) by type with `EdgeDetailBuilder` — the build-up as a structural core + skin `Layer`s, the framing as sections + spacing; the template computes every member's **centric** placement. The detail-catalog 3dc workflow: build, inspect the layer build-up, surface the corner-resolving cutting elements, and serialize. Applying it to modelled covers (`run_calculation`) is a separate step, not shown here. The bundled `data/aw260_edge.json` is the canonical reference |
| [`registered_details.py`](registered_details.py) | The two registries: the **type-builder** registry (`of_type` / `builder_for`) and the named-definition **catalog** (`@register_detail`, `detail_names`, `get_detail`, `build_named_detail`) |
| [`detail_reader.py`](detail_reader.py) | Read details back out of the model — the inverse of `build_detail`: `read_detail` reconstructs one cover's `DetailDefinition` (sections, placement, properties), `discover_details` scans them all; `detail_type` is an override (not readable) |
| [`read_selection_in_cadwork.py`](read_selection_in_cadwork.py) | **Run inside cadwork.** Read the active *selection* (selected walls/floors/roofs) and write one detail JSON per cover to `OUTPUT_DIR` — the practical way to capture a real, hand-modelled detail. Not in the fake suite (live selection + file output); its helpers are tested separately |
| [`containers_and_mep.py`](containers_and_mep.py) | `Container.create_from_standard`, `parent_container`, `discover_containers`; `CircularMep` / `RectangularMep` |
| [`connectivity.py`](connectivity.py) | `find_connected`, `build_connection_graph`, components, and a custom contact predicate |
| [`raycast.py`](raycast.py) | `cast_ray`: which elements a ray hits (nearest-first `RayCastResult` / `RayHit`), the `radius` thickness, and `among=` |
| [`building_storeys.py`](building_storeys.py) | The pure `StoreyStack` classifier and the model-driven `StoreyAssigner` |
| [`utilities.py`](utilities.py) | `DisplayRefreshScope` (context, `@auto_recreate`, `@DisplayRefreshScope()`, `recreate_after`), `suppressed_display`, and `batch_apply` |
| [`decorators.py`](decorators.py) | The pure-Python class decorators: `auto_repr` (bare + fields), `auto_eq` / `auto_hash`, and `deprecated` |
| [`persistence.py`](persistence.py) | `open_sqlite`, `Synchronizer` pull/push, `ModelReader`, `diff`, `UnitOfWork`, and raw SQL |
| [`persistence_queries.py`](persistence_queries.py) | Read the model into SQL, then query it back: typed `Gateway` reads, a cross-table SQL JOIN report, and the `BuildingQuery` facade (building → storeys → elements) |
| [`sql_builder.py`](sql_builder.py) | The table-as-data SQL builder (`Table` / `Column`, `create_table`, `Insert` / `Update` / `Delete` / `Select`), then using it to query a pulled model |

## Running inside cadwork vs. anywhere

The examples use only the public `pycadwork` API. Two of them — `geometry_basics`
and `decorators` — touch no live model and run in any interpreter. The rest *create elements*
(including `persistence` and `sql_builder`, which mirror a real model), so they
run fully **inside cadwork** (where the real adapter is live) or **under the test
suite's in-memory fake**.

A handful seed model state that a real project gets from the cadwork UI — a beam
flagged as a wall, a building's BMT storeys. Those steps go through the
version-isolation seam (`pycadwork.cadwork_adapter.cadwork`) and are clearly
commented as *setup that mimics the cadwork UI*. They are not part of normal
day-to-day pycadwork usage.

One example, [`read_selection_in_cadwork.py`](read_selection_in_cadwork.py), is
the opposite: it is meant to run **inside cadwork on a live model**, reading the
elements you have selected and writing real detail JSON to disk. It is not in the
auto-run `MODULES` list (it would need a live selection and would write files),
so its read/serialize helpers are covered by a dedicated test instead.

## Verified in CI

`tests/test_examples.py` runs every module's `run()` against the fake adapter, so
these examples are guaranteed to stay in step with the public API:

```bash
uv run pytest tests/test_examples.py
```
