# Containers and MEP

A `Container` is an aggregate like a cover — it owns a set of typed children
through the same uniform `children` / `children_of(cls)` surface — but the link
is *real containment*, not grouping. A cover's members share a `group` /
`subgroup` value; a container's members are wired to it in the model, so a
container reads its contents with cadwork's containment API and any element can
report its owning container. `Container` therefore does **not** inherit the
grouping-driven cover `Aggregate`.

```python
from pycadwork import Container, discover_containers, parent_container

# Build a container from elements using a configured cadwork standard.
c = Container.create_from_standard([beam_a, beam_b], "C1", "MyContainerStandard")

c.children  # list[Element], wrapped to their typed classes
c.children_of(Beam)  # list[Beam]
c.add_child(beam_c)  # mutate membership (add / remove / replace)
c.remove_child(beam_a)
c.replace_children([beam_c])

parent_container(beam_c)  # -> Container | None  (free function, like discover_*)

for container in discover_containers():
    print(container, len(container.children))
```

`CircularMep` (a pipe) and `RectangularMep` (a duct) are ordinary leaf elements,
path-anchored like `Beam`/`Drilling`. A circular run carries a `diameter`; a
rectangular run carries `width` and `depth`:

```python
from pycadwork import CircularMep, RectangularMep, Point3D

pipe = CircularMep.create(80.0, [Point3D(0, 0, 0), Point3D(0, 0, 3000)])
duct = RectangularMep.create(200.0, 100.0, [Point3D(0, 0, 0), Point3D(0, 0, 3000)])
pipe.diameter  # 80.0
```
