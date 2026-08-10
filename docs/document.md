# The document & project

`Document` is the top-level handle for the active cadwork project. It does two
jobs: it **is the element repository** — a *live* view over the whole model — and
it **manages the project** through its `project` component (a `ProjectInfo`).
Construction takes no arguments; there is exactly one active project.

```python
from pycadwork import Document, Beam

doc = Document()

doc.elements()  # list[Element] — every identifiable element, typed
doc.active()  # list[Element] — the currently selected elements
doc.elements_of(Beam)  # list[Beam]    — narrowed by runtime type
doc.get(1234)  # Element       — wrap one id (delegates to from_id)
doc.covers()  # list[Aggregate] — every Wall / Slab / Roof
doc.delete(some_beams)  # batched delete

doc.guid  # the project GUID (convenience delegate to .project)
```

Reads are queries against the backend at call time — there is no cached state,
in keeping with the rest of the package. Every per-type accessor is subsumed by
the parameterized `elements_of(cls)`, so adding a new element subclass never
requires a new method here.

`ProjectInfo` mirrors `Element.attrs`: project metadata is exposed as live
read/write properties (reads are properties, writes are `set_*` methods), plus
indexed project user-attributes and a project-data key/value store.

```python
project = Document().project

project.name  # read
project.set_name("Cabin A")  # write
project.set_architect("M. Brunner")
project.latitude, project.longitude, project.elevation

project.set_user_attribute(1, "phase-1")
project.set_data("revision", "C")
project.data_keys()  # list[str]
```
