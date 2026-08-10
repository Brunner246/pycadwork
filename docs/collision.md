# Collision: clash / contact / near-miss / clearance

`pycadwork.collision` audits a model for several collision relationships at once
and returns a structured report. Where [`connectivity`](connectivity.md) answers
the single geometric question "do these touch?", this module distinguishes a
true clash from a flush contact, finds the **near-misses** ("elements that
should touch but don't"), and measures **clearance** — and reports them as
frozen value objects, the sibling of [`rules`](rules.md).

```python
from pycadwork import check_collisions, CollisionKind, highlight_clashes

report = check_collisions(
    kinds=[CollisionKind.OVERLAP, CollisionKind.NEAR_MISS],
    margin=5.0,                       # "should touch but don't" within 5 mm
)
print(report.ok)                      # False if anything interpenetrates
for clash in report.clashes:
    print(clash.kind.name, clash.first_id, clash.second_id, clash.distance)

highlight_clashes(report, kinds=[CollisionKind.OVERLAP])  # recolour the offenders
```

`check_collisions` defaults its element set to the active identifiable model,
builds one R-tree over the candidates, **prunes far-apart pairs**, runs the exact
test only on the spatially-near survivors, and returns a `CollisionReport` whose
`clashes` are deterministically sorted (`kind`, then the id pair).

## The four checks

You pass the `kinds` you care about; the scan classifies each surviving pair and
emits the requested findings. `CollisionKind` is ordered
`NEAR_MISS < CLEARANCE < CONTACT < OVERLAP`.

| Kind | Means | Distance reported |
|------|-------|-------------------|
| `OVERLAP` | solids interpenetrate — the classic clash error | `0.0` |
| `CONTACT` | solids touch (flush faces) without interpenetrating | `0.0` |
| `NEAR_MISS` | solids are apart but within `margin` — a missing contact | the gap |
| `CLEARANCE` | solids are apart by no more than `clearance_threshold` | the gap |

`NEAR_MISS` is the **bounding-box-extension** finder you reach for to catch
"these were supposed to meet": grow each element by `margin` and report the
pairs that newly reach one another while still not touching. `CLEARANCE` is the
minimum-spacing check — pass `clearance_threshold=` to set the limit.

```python
# elements that ought to meet but leave a gap up to 10 mm
gaps = check_collisions(kinds=[CollisionKind.NEAR_MISS], margin=10.0)

# nothing may sit closer than 30 mm
spacing = check_collisions(kinds=[CollisionKind.CLEARANCE], clearance_threshold=30.0)
```

## Spatial pruning — passing a large element set is cheap

The scan is broad-phase first: an [`RTreeIndex3D`](geometry.md) over the
candidate boxes is queried with each element's AABB grown by the largest
relevant reach (`margin` for near-miss, `clearance_threshold` for clearance,
else the touch tolerance). Anything outside that grown box is dropped before any
solid or OBB test runs, so the scan is `O(near-pairs)`, not `O(n²)`, and a
distant element is never compared. `report.pairs_tested` counts the pairs that
survived pruning and reached a narrow-phase test; `report.checked` counts the
elements scanned.

Scope the work with `elements=` (the focus set) and `among=` (the universe each
focus element is tested against, defaulting to the focus set itself):

```python
# test one assembly against the whole model, not against itself only
report = check_collisions([wall_member], among=document.elements())
```

## Excluding elements

`exclude=` drops elements from the scan entirely — an excluded element is
neither a subject nor a partner of any pair. It is an `(element) -> bool`
predicate, so any type or property filters cleanly:

```python
from pycadwork import Aggregate, CoverKind, check_collisions, CollisionKind

# ignore every cover (Wall / Slab / Roof all subclass Aggregate)
check_collisions(
    kinds=[CollisionKind.OVERLAP],
    exclude=lambda e: isinstance(e, Aggregate),
)

# ignore only solid walls — Aggregate exposes its `.kind`
check_collisions(
    kinds=[CollisionKind.OVERLAP],
    exclude=lambda e: isinstance(e, Aggregate) and e.kind is CoverKind.SOLID_WALL,
)

# any predicate works — by material, name, dimension, …
check_collisions(exclude=lambda e: e.attrs.material_name == "Insulation")
```

The predicate is applied to both the focus set and `among`, and `report.checked`
counts only the elements that survived. Excluding a type is the usual reason a
clash audit ignores cover shells, auxiliary geometry, or a sacrificial material.

## Two backends — what `backend=` actually changes

`backend=` chooses **how each surviving pair's relationship is computed** — it
does not change *which* pairs are looked at (the spatial pre-filter is the same
either way), only the test applied to each. The two backends answer the same
questions with very different machinery and trade-offs.

### `Backend.SOLID` (the default)

Asks cadwork itself, through the one version-isolation seam, to evaluate the
pair on the **real machined solids** — the geometry after trims, mitres,
drillings, and every boolean/CSG operation. Overlap, contact, and minimum
distance are three separate exact kernel queries
(`check_if_elements_are_in_collision`, `check_if_elements_are_in_contact`,
`get_minimum_distance_between_elements`). Because it runs against the actual
solids it can tell a true interpenetration apart from a flush face-to-face
contact, and the reported distance is the real gap. The cost: it needs a **live
cadwork session** (the kernel is not available on a pulled snapshot or under the
test fake's real geometry), and each pair is a kernel round-trip — which is why
the broad-phase pruning matters.

### `Backend.GEOMETRY`

Decides the pair from pycadwork's own **bounding volumes** instead of the
kernel: it reuses `connectivity`'s tolerance-aware OBB separating-axis test for
touch/overlap and the axis-aligned bounding-box gap for distance. It touches no
kernel, so it runs **anywhere** — against a snapshot, in CI, in the test suite —
and is the right choice when you don't have (or don't want to pay for) a live
model. The approximation has two consequences to know:

- **Overlap and contact collapse.** A box can't distinguish a solid that
  interpenetrates from one that merely sits flush, so any connected pair is
  reported as `CONTACT` (and is surfaced for an `OVERLAP` request too — the best
  a box test can offer).
- **It is conservative, not exact.** A bounding box *encloses* its solid, so the
  box-to-box gap is never larger than the true gap (a *lower* bound on
  clearance) and an OBB grown by the tolerance can register contact where the
  real faces are slightly apart. In practice it never *misses* a near-miss or
  clash, but it can *over-report* one for non-box shapes (an angled or trimmed
  member whose box is much larger than its solid).

### Which to use

| | `Backend.SOLID` (default) | `Backend.GEOMETRY` |
|---|---|---|
| Decided by | cadwork's real solid kernel | pycadwork OBB / AABB |
| Overlap vs. contact | distinguished exactly | collapsed to `CONTACT` |
| Distance | exact solid gap | box gap (lower bound) |
| Needs a live model | **yes** | no — snapshot / CI / tests |
| Accuracy on trimmed / angled solids | exact | conservative over-reporting |

`backend=Backend.AUTO` (the unspecified default) currently resolves to `SOLID`;
it is the single documented place a future heuristic could pick per situation.
Reach for `SOLID` whenever the overlap/contact distinction or an exact gap
matters; reach for `GEOMETRY` when there is no live model or a fast, conservative
box check is good enough.

## Pairwise predicates

The single-pair predicates behind the scan are public for direct use; each takes
the same `backend=`:

```python
from pycadwork import overlaps, touches, clearance, is_near_miss

overlaps(a, b)                       # interpenetrate?
touches(a, b, tolerance=1.0)         # touch or overlap? (tolerance is GEOMETRY-only)
clearance(a, b)                      # the minimum distance between them
is_near_miss(a, b, margin=10.0)      # within margin but not touching?
```

## The report, the CI gate, and acting on it

`report.ok` is `True` when there is **no `OVERLAP`** — contacts, near-misses and
clearances are advisories that do not break the gate, so `assert
check_collisions(...).ok` is a clean "nothing interpenetrates" check. The report
also offers `by_kind()` and `count(kind=None)`.

`highlight_clashes(report, *, color_id=…, comment=None, kinds=…)` is the separate,
opt-in step that makes findings visible — it recolours (and optionally comments)
the offending elements through the visualization seam and returns their ids. The
scan itself stays pure.

```python
import io
from pycadwork import write_clashes_csv

stream = io.StringIO()
write_clashes_csv(report, stream)    # kind, first_id, second_id, distance
```

A runnable tour — each check, the pruning, type exclusion, both backends, the
pairwise predicates, highlighting, and CSV — lives in
[`examples/collision.py`](../examples/collision.py).
