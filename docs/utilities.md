# Utilities

## Suppressing display refresh during bulk work

cadwork repaints after every element mutation. For bulk operations that costs
more than the work itself. `DisplayRefreshScope` drives the seam's
disable / recreate / enable triple, exception-safe (refresh is always
re-enabled; recreate is skipped if the block raised):

```python
from pycadwork import DisplayRefreshScope

with DisplayRefreshScope() as scope:
    beams = [Beam.create_rectangular(sec, ax) for sec, ax in specs]
    scope.track(beams)  # recreated once, on exit
```

As decorators: `@DisplayRefreshScope()` / `@auto_recreate` (create-and-track in
one call) / `@suppressed_display` (suppress refresh, no recreate — for
attribute-only mutations that don't change geometry).

## Batch attribute writes

```python
from pycadwork import batch_apply

batch_apply(beams, group="frame", material_name="Pine")
# one adapter call per attribute, instead of one per element
```

Unknown attribute names raise `TypeError` so typos surface at the call site.
