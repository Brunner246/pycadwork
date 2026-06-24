# Testing

The single-seam design is what makes the library testable without cadwork. A
`conftest.py` fixture swaps the live sub-adapters for an in-memory
`FakeCadworkAdapter` on every test, so the full suite runs anywhere:

```bash
uv run pytest                       # full suite (630 tests, no cadwork needed)
uv run pytest tests/element         # one area
uv run pytest -k connectivity       # by keyword
```

When you add a cadwork call, the recipe is symmetric: add it to the right
sub-adapter in `cadwork_adapter/`, mirror it on the matching fake in
`tests/_fakes/cadwork_adapter.py`, then expose it on the relevant wrapper.
