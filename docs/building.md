# Building & storey assignment

cadwork's BMT structure gives a building an ordered set of storeys, each anchored
at an absolute Z elevation. `StoreyAssigner` reads that structure for one
building and classifies elements into storeys by their vertical extent: each
element lands in the storey it *mostly* sits in (the >50%-overlap majority rule),
and anything that straddles a storey plane is assigned to the majority storey and
**marked** in an indexed user-attribute for human review. Cover aggregates are
treated as a unit — the parent's storey is forced onto all its children.

```python
from pycadwork import StoreyAssigner, BuildingName, Document

report = StoreyAssigner(BuildingName("Building A")).assign(Document().elements())
for assignment in report:
    print(assignment.element, assignment.storey.name, assignment.spans)

# the marker slot and value are configurable
StoreyAssigner(
    BuildingName("Building A"), mark_attribute_index=7, mark_value="REVIEW"
).assign(elements)
```

The classification core, `StoreyStack`, is **pure** — no cadwork involved — so it
is unit-testable as plain geometry. It partitions the vertical axis into
half-open intervals and reports both the chosen storey and whether the extent
spans more than one:

```python
from pycadwork import Storey, StoreyStack, StoreyName

stack = StoreyStack([
    Storey(StoreyName("GF"), elevation=0.0),
    Storey(StoreyName("1F"), elevation=3000.0),
    Storey(StoreyName("2F"), elevation=6000.0),
])

result = stack.classify(z_lo=100.0, z_hi=2800.0)
result.storey.name  # StoreyName("GF")
result.spans  # False

result = stack.classify(z_lo=2900.0, z_hi=3300.0)  # crosses the GF/1F plane
result.storey.name  # StoreyName("1F")  — majority
result.spans  # True
```
