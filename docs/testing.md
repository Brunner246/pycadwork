# Testing

The single-seam design is what makes the library testable without cadwork. A
`conftest.py` fixture swaps the live sub-adapters for an in-memory
`FakeCadworkAdapter` on every test, so the full suite runs anywhere:

```bash
uv run pytest                       # full suite (900+ tests, no cadwork needed)
uv run pytest tests/element         # one area
uv run pytest -k connectivity       # by keyword
```

When you add a cadwork call, the recipe is symmetric: add it to the right
sub-adapter in `cadwork_adapter/`, mirror it on the matching fake in
`pycadwork/testing/cadwork_adapter.py`, then expose it on the relevant wrapper.

## Using the fake from a downstream plugin

`FakeCadworkAdapter` is **shipped, not test-only** — it lives in
`src/pycadwork/testing/` and is part of the wheel, so a project built on
pycadwork can run its own suite against real pycadwork logic (real
`build_connection_graph`, real `RTreeIndex3D`, real geometry maths) with no
cadwork process and no vendored copy of the fake:

```bash
uv add "pycadwork[testing]"         # the extra is empty — pure Python, no new deps
```

The supported way to install it is the injection seam documented on
`src/pycadwork/cadwork_adapter/__init__.py:9`:

```python
import pycadwork.cadwork_adapter
from pycadwork.testing import FakeCadworkAdapter

monkeypatch.setattr(pycadwork.cadwork_adapter, "cadwork", FakeCadworkAdapter())
```

That module-attribute swap is enough when the code under test resolves
`pycadwork.cadwork_adapter.cadwork` at call time. Production call sites that do
`from pycadwork.cadwork_adapter import cadwork` capture the singleton at import
time instead, so pycadwork's own `tests/conftest.py` additionally swaps each
**sub-adapter slot** (`cadwork.attributes`, `cadwork.geometry`, …) on the live
singleton — every call goes through `cadwork.<sub>.method(...)`, so each lookup
hits the fake. Copy that fixture if your tests exercise such call sites; the
sub-adapter classes are exported from `pycadwork.testing` for exactly this.

The fake shares one `FakeState` across all sub-adapters, so a write through
`fake.attributes.set_name` is immediately visible to `fake.geometry` and to
`fake.grouping` queries — round-tripping (create → read back) works without a
CAD kernel.
