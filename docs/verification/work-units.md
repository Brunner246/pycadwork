# Verification: Work units for bulk live-model mutations

> **Source Spec:** `docs/spec/work-units.md`
> **Source research:** `docs/research/work-units.md`
> **Source architecture:** `docs/architecture/work-units.md`
> **Status:** Draft
>
> Owns the **verification-evidence** layer only. It cites Spec `## Testing Decisions`
> (testing intent) and architecture `## 5` (test doubles) — it never re-decides them.

## 1. Context

Correctness is behavioral on a new context manager: a tracked set of live
elements either keeps the attributes `apply` / `run` wrote (and registers undo)
or is restored to the enter/track snapshot when a step raises, with a frozen
`WorkReport` describing which. Architecture §5 says the shipped
`FakeCadworkAdapter` is the double; Spec Testing Decisions say no real-cadwork
Ctrl+Z IT in v1. Proof is therefore exact pytest assertions on model state,
`FakeState.modified_undo_calls`, report fields, isolation, public exports, and
the example tour — the harness already exists.

## 2. Per-story acceptance methodology

| Spec story | Acceptance check (what you run) | Observable signal | Judging method | Factory scope |
|-----------|----------------------------------|-------------------|----------------|---------------|
| US-1: bulk `apply` rolls back on error | `uv run pytest tests/work/test_unit.py -k "apply or rollback or typo"` | After `apply(name=…)` then a raising `apply`/`run`, every tracked `attrs.name` equals the pre-unit value; original exception type propagates | `exact` | `repo-local` |
| US-2: sequence of `run` callables is one unit | `uv run pytest tests/work/test_unit.py -k run` | Two `run`s that mutate tracked attrs both persist on success; if the second raises, both mutations are gone; `fn` return value is passed through; default step name is `fn.__qualname__` | `exact` | `repo-local` |
| US-3: success registers cadwork Undo | `uv run pytest tests/work/test_unit.py -k undo` | Default `WorkUnit(beams)` success: `fake._state.modified_undo_calls == [[tracked ids]]`. `undo=False`: the list is empty. Rollback path: the list is empty | `exact` | `repo-local` |
| US-4: frozen `WorkReport` | `uv run pytest tests/work/test_unit.py -k report` | After success: `report.status is WorkStatus.COMMITTED`, `element_ids` match tracked ids, `diffs` contain `(id, "name", before, after)`. After rollback: `status is ROLLED_BACK`. `.report` before `__exit__` raises `RuntimeError` | `exact` | `repo-local` |
| US-5: mid-unit `track()` | `uv run pytest tests/work/test_unit.py -k track` | Element tracked after an `apply` snapshots *current* attrs; rollback restores it to track-time, not to a pre-unit value it never had in the snapshot. `track` / `apply` / `run` outside the context raise `RuntimeError` | `exact` | `repo-local` |
| US-6: module doc + example tour | `uv run pytest tests/test_examples.py -k work` | `examples.work.run()` completes; `"work"` is in `examples.MODULES`. `docs/work.md` exists (assert `Path("docs/work.md").is_file()` in the work tests or a tiny docs-presence case) | `exact` | `repo-local` |
| US-7: fake-backed suite, no live cadwork | `uv run pytest tests/work/ -q` | Suite green under autouse `fake_cadwork` (`tests/conftest.py`); no skipif for cadwork | `exact` | `repo-local` |
| US-8: undo goes through the seam | `uv run pytest tests/test_isolation.py tests/test_public_surface.py tests/work/test_unit.py -k undo` | `pycadwork.work` is absent from isolation offenders; `WORK_EXPORTS` are on `pycadwork` and in `__all__`; live adapter method name is `add_modified_elements_to_undo` (fake records it) | `exact` | `repo-local` |

All rows are bot-runnable unattended (`uv run pytest …`). No graphical legs. No
deferred Manual: Ctrl+Z in a real cadwork session is explicitly out of v1
(Spec Testing Decisions; architecture §5 runtime-verification gap).

## 3. Verification assets (Reuse vs `[NEW]`)

### 3.1 What was searched

| Repo | Searched (dir / keyword) | Found / Not found |
|------|--------------------------|-------------------|
| pycadwork | `tests/work/` | not found — module does not exist yet |
| pycadwork | `tests/conftest.py` autouse fake | `tests/conftest.py:11-39` |
| pycadwork | `FakeCadworkAdapter` / `FakeState` call lists | `src/pycadwork/testing/cadwork_adapter.py:258-282, 378+` |
| pycadwork | `tests/utility/test_batch.py` | batch_apply exact-call tests |
| pycadwork | `tests/test_examples.py`, `examples/MODULES` | `tests/test_examples.py:19-23`; `examples/__init__.py:60-78` |
| pycadwork | `tests/test_isolation.py`, `tests/test_public_surface.py` | isolation AST scan; `VERSIONING_EXPORTS` pattern |
| pycadwork | goldens / fixtures for attribute diffs | not found — not needed (exact live attrs on fake elements) |
| pycadwork | cadwork run-program IT for undo | versioning IT only; none for attribute undo |

### 3.2 Classification

| Asset | Kind | Verdict | Source / Rationale |
|-------|------|---------|--------------------|
| Autouse `fake_cadwork` | fixture/double | **Reuse** | `tests/conftest.py:11-39`; architecture §5 |
| `FakeCadworkAdapter` / `FakeState` | fixture/double | **Reuse** (extend with `modified_undo_calls`) | architecture §5; research finding 6 |
| `tests/utility/test_batch.py` patterns | harness | **Reuse** | spy-on-setter style for US-1 write-path if needed; work tests assert state first |
| `tests/test_examples.py` | harness | **Reuse** | US-6; adding `"work"` to `MODULES` is enough |
| `tests/test_isolation.py` | harness | **Reuse** | US-8; no change if work stays above the seam |
| `tests/test_public_surface.py` `VERSIONING_EXPORTS` pattern | harness | **Reuse** (extend) | add `WORK_EXPORTS` tuple |
| Beam-create helpers in work tests | fixture | **Reuse** (copy local helper) | same `_make_beam` shape as `tests/utility/test_batch.py:12-16` — inline, not a shared golden |
| `tests/work/test_unit.py` | test module | **`[NEW]`** | Searched `tests/work/`; missing because the product module is new. Producer of US-1–5, US-7 |
| `modified_undo_calls` on `FakeState` | fixture field | **`[NEW]`** | Searched FakeState observables; operations have `subtract_calls` etc., no undo list |
| `docs/work.md` + `examples/work.py` | teaching assets | **`[NEW]`** | Product docs/example; US-6 consumes them as files the example tour executes |
| Golden attr-diff JSON / real `.3d` undo IT | golden / e2e | **not authored** | Spec Testing Decisions: exact fake asserts; no Ctrl+Z IT in v1 |

## 4. Verification tooling / harness (`[NEW]` only)

Every §2 method uses existing `uv run pytest`. No new comparator, runner, or
e2e command.

| Tool | What it does | Will live at | Becomes command | Consumed by |
|------|--------------|--------------|-----------------|-------------|
| *(none)* | — | — | — | — |

Existing commands used as-is:

- `uv run pytest tests/work/`
- `uv run pytest tests/test_examples.py`
- `uv run pytest tests/test_isolation.py tests/test_public_surface.py`
- `uv run pytest -q` (full suite / no-regressions)

## 5. Whole-feature acceptance methodology (capstone contract)

### 5a. Per-repo capstone contract — one block per `Target repo`

- **Repo:** `pycadwork`
- **Broad command:** `uv run pytest tests/work/ tests/test_examples.py tests/test_public_surface.py tests/test_isolation.py -q`
- **Fed inputs:** in-memory fake elements created in tests / examples (no fixture files)
- **Judged by:** §2 `exact` methods
- **Against goldens:** none
- **No-regressions clause:** full suite `uv run pytest -q` green
- **Graphical legs:** none — headless-only
- **Deferred Manual (HITL) legs:** none — fully AFK. (Real cadwork Ctrl+Z is out of v1, not deferred.)

### 5b. Cross-factory acceptance leg (integration capstone)

n/a — every story is repo-local; the per-repo capstone suffices.

## 6. Open questions

(none)
