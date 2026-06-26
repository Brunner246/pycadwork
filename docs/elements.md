# The element model

Every concrete wrapper inherits from a single `Element` base. An `Element` is a
**live view over a cadwork ID** — reads are queries against the active backend,
not cached snapshots. It aggregates two component objects to keep its own
surface small:

- **`element.attrs`** — an `Attributes` view: `name`, `group`, `subgroup`,
  `comment`, `material_name`, `sku`, `production_number`, `part_number`,
  `cadwork_guid`, `additional_data`, `assembly_number`, and indexed
  `user_attribute(i)`. Each is a read/write property (`attrs.group = "frame"`),
  except read-only `cadwork_guid` and the indexed `user_attribute(i)` /
  `set_user_attribute(i, v)` pair, which stay methods.
- **`element.geometry`** — a `Geometry` view (narrowed per subclass) exposing
  `volume`, `weight`, `center_of_gravity`, `aabb`, `brep`, and — for linear and
  oriented elements — `start_point` / `end_point`, `frame`, `length` / `width` /
  `height`, `axis_points`, `axis_frame`, `obb`, and `thickness`.

```python
beam.attrs.name  # -> str
beam.attrs.material_name = "Pine"  # write-back via the matching setter property
beam.geometry.center_of_gravity  # -> Point3D
beam.geometry.frame  # -> Frame3D
beam.geometry.obb  # -> OrientedBoundingBox
```

## Element types

| Wrapper                  | cadwork concept                                         | Geometry component                    |
|--------------------------|---------------------------------------------------------|---------------------------------------|
| `Beam`                   | rectangular / circular / square / polygon linear member | `LinearGeometry`                      |
| `Plate`                  | panel (flat board/sheet)                                | `OrientedGeometry` (adds `thickness`) |
| `Drilling`               | drilling axis                                           | `LinearGeometry`                      |
| `ConnectorAxis`          | connector axis                                          | `LinearGeometry`                      |
| `Line`                   | line element                                            | `LinearGeometry`                      |
| `Node`                   | positioned point                                        | `NodeGeometry` (adds `position`)      |
| `Surface`                | surface element                                         | `Geometry`                            |
| `Opening`                | opening                                                 | —                                     |
| `AuxiliaryElement`       | auxiliary element                                       | —                                     |
| `Wall` / `Slab` / `Roof` | cover objects (aggregates)                              | see [Cover objects](covers.md)        |

## Uniform typing — no per-type accessors

Aggregate APIs always return `list[Element]`. To get a specific type, use the
generic, type-safe narrowing helper rather than a bespoke accessor:

```python
beams = group.members_of(Beam)  # list[Beam]
plates = wall.children_of(Plate)  # list[Plate]
```

This means adding a new element subclass never requires adding a new accessor
anywhere — the polymorphic base plus `members_of(cls)` covers it.

## Wrapping existing elements: `from_id`

To wrap an ID that already exists in the model, use `from_id`. It reads the
element's type once and dispatches to the most specific subclass via a
**declarative priority registry**:

```python
from pycadwork import from_id

elem = from_id(1234)  # -> Beam, Plate, Wall, … whichever matches
```

Each wrapper registers itself at class-definition time with a predicate over an
`ElementTypeSnapshot` and a *priority band* (`AGGREGATE` < `SPECIAL` <
`PRIMITIVE` < `GEOMETRIC`). Cover objects beat primitives because a wall also
satisfies `is_beam`. Registering a custom subclass is one decorator:

```python
from pycadwork import register_element
from pycadwork.element.registry import PRIMITIVE


@register_element(lambda s: s.is_beam, priority=PRIMITIVE)
class MyBeam(Beam):
    ...
```
