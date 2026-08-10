# Cover objects: walls, slabs, roofs

In cadwork, a wall/floor/roof and its members are **not** linked by a container
API — they share a `group` (or `subgroup`) value, and which one is the
project-wide setting read from `get_element_grouping_type()`. `pycadwork` models
this faithfully:

- `Wall`, `Slab`, `Roof` are `Aggregate` subclasses — themselves real cadwork
  elements flagged with a `CoverKind` (`FRAMED_WALL`, `SOLID_FLOOR`, …).
- `Group` is a value-typed view over everyone sharing a grouping key, reading
  the active mode live so the same code adapts when the project setting changes.
- An aggregate's `children` are its siblings in the group, minus itself.

```python
from pycadwork import Wall, Beam, Plate, CoverKind, CoverBuilder, cadwork

# children are polymorphic; narrow by type when you need to
wall.children  # list[Element]
wall.children_of(Beam)  # list[Beam]
wall.kind  # CoverKind.FRAMED_WALL

# imperative attach / detach
wall.add_child(beam)
wall.add_children([beam, plate])
wall.replace_children(new_members)
wall.remove_child(beam)
```

## Assembling covers with `CoverBuilder`

The builder takes a bunch of elements, lets you set assembly options fluently,
then `build()` returns the assembled covers as `list[Aggregate]`. The
`aggregate_by_grouping` strategy buckets the elements by their active
`group`/`subgroup` key and types each bucket holding a wall/floor/roof element:

```python
from pycadwork import CoverBuilder, Wall, Document

# every cover among the active elements, typed Wall / Slab / Roof
covers = CoverBuilder(Document.active()).aggregate_by_grouping().build()

# narrow the result to one cover family
walls = CoverBuilder(elements).aggregate_by_grouping().only(Wall).build()
```

The builder offers multiple assembly strategies by design. To *attach* children
to a cover, use the imperative `Aggregate.add_child` / `add_children` directly.

## Discovering covers in a model

`discover_covers` scans the model (or a custom set of IDs), buckets elements by
their grouping key, and returns one typed aggregate per bucket that contains a
wall/floor/roof parent. It's a **module-level free function**, not a classmethod:

```python
from pycadwork import discover_covers

for cover in discover_covers():  # list[Aggregate] (Wall/Slab/Roof)
    print(cover, len(cover.children))
```
