# Verification: Git-like model versioning (model-aware defaults)

> **Source Spec:** `docs/spec/git-like-model-versioning.md`
> **Source research:** `docs/research/git-like-model-versioning.md`
> **Source architecture:** `docs/architecture/git-like-model-versioning.md`
> **Status:** Draft
>
> Owns the **verification-evidence** layer only. It cites Spec `## Testing Decisions`
> (testing intent) and architecture `## 5` (test doubles) — it never re-decides them.

## 1. Context

Correctness here is behavioral policy on an existing facade: do git-named verbs load
the live model by default, refuse dirty live state without `force`, and keep
`apply_to_model=False` pure-git? Most proof is exact assertions on fake-backed unit
tests (architecture §5). One story needs a real cadwork process over the timber
fixture; that path is optional enrichment gated by skipif so default CI stays
green (Spec Testing Decisions; research finding 8).

## 2. Per-story acceptance methodology

| Spec story | Acceptance check (what you run) | Observable signal | Judging method | Factory scope |
|-----------|----------------------------------|-------------------|----------------|---------------|
| US-1: branch switch loads model | `uv run pytest tests/versioning/test_versioning.py -k "checkout or switch"` (extended cases) | After `checkout("main")` with prior feature commit, live element count/ids match baseline commit (not feature-only element) | `exact` | `repo-local` |
| US-2: pull/merge load model | `uv run pytest tests/versioning/ -k "pull or merge"` (new cases on FakeRepository) | After successful pull/merge with `apply_to_model=True`, live model reflects merged snapshot; after conflict, model unchanged and `MergeConflictError` raised | `exact` | `repo-local` |
| US-3: dirty refuse unless force | `uv run pytest tests/versioning/ -k dirty` | Divergent live model + `checkout`/`reload_model` without `force` raises `DirtyWorkingTreeError`; with `force=True` succeeds | `exact` | `repo-local` |
| US-4: pure-git escape hatch | `uv run pytest tests/versioning/ -k apply_to_model` | `checkout(..., apply_to_model=False)` changes JSONL tree, live element set unchanged; return is `None` | `exact` | `repo-local` |
| US-5: dock matches defaults | Manual review of example code paths + `uv run pytest tests/test_examples.py` if dock remains import-gated; smoke: ViewModel pull/merge messages no longer instruct a second load | Diff of `examples/versioning_dock_widget.py` shows confirm+`force=True` checkout; pull/merge use report summary without “Load model to version” after-success copy | `exact` (string/API presence assertions optional; code review for example-only surface) | `repo-local` |
| US-6: real-cadwork IT | `uv run pytest tests/versioning/test_cadwork_run_program.py -v` | Skip if no `ci_start`/git; else exit 0 and result JSON `{"ok": true, …}` | `exact` | `repo-local` |
| US-7: examples/docs teach defaults | Grep/read pass + example import tour for CI-listed modules | No remaining “checkout does not rewind the live model” teaching; `docs/versioning.md` documents model-aware defaults + flags | `exact` (forbidden-string grep in examples/docs for old surprise wording) | `repo-local` |

All rows are bot-runnable unattended except incidental human reading of the dock
example; the dock is not a Headless:false GUI leg (no bot-piloted Qt required —
example code is the deliverable).

## 3. Verification assets (Reuse vs `[NEW]`)

### 3.1 What was searched

| Repo | Searched (dir / keyword) | Found / Not found |
|------|---------------------------|-------------------|
| pycadwork | `tests/versioning/` | full unit + git integration suite |
| pycadwork | `tests/_fakes/repository.py` | FakeRepository |
| pycadwork | `tests/fixtures/model/` | `timber-framed-slab.3d` |
| pycadwork | cadwork run-program IT | not found |
| pycadwork | golden versioning JSON | not found (not needed — exact behavioral asserts) |

### 3.2 Classification

| Asset | Kind | Verdict | Source / Rationale |
|-------|------|---------|--------------------|
| `FakeRepository` + fake cadwork | fixture/double | **Reuse** | architecture §5; `tests/_fakes/repository.py` |
| Existing `tests/versioning/test_*.py` patterns | harness | **Reuse** | extend in place |
| `timber-framed-slab.3d` | input fixture | **Reuse** | `tests/fixtures/model/timber-framed-slab.3d` |
| IT run-program script + result JSON schema | fixture/tooling input | **`[NEW]`** | No prior cadwork IT script; authored under `tests/versioning/` (or `tests/fixtures/versioning/`) |
| Forbidden-string list for old UX wording | golden strings | **`[NEW]`** | Small literal list in US-7 test or verification seed checklist |

## 4. Verification tooling / harness (`[NEW]` only)

| Tool | What it does | Will live at | Becomes command | Consumed by |
|------|--------------|--------------|-----------------|-------------|
| Cadwork run-program IT harness | Copies fixture, writes/runs in-cadwork script via terminal/`ProcessLauncher`, asserts result JSON | `tests/versioning/test_cadwork_run_program.py` (+ helper script file if needed) | `uv run pytest tests/versioning/test_cadwork_run_program.py` | US-6 |
| `DirtyWorkingTreeError` unit cases | Assert refuse/force matrix | extend `tests/versioning/test_versioning.py` | `uv run pytest tests/versioning/ -k dirty` | US-3 |

Existing commands used as-is: `uv run pytest`, `uv run pytest tests/versioning/`,
`uv run pytest tests/test_examples.py`.

## 5. Whole-feature acceptance methodology (capstone contract)

### 5a. Per-repo capstone contract — one block per `Target repo`

- **Repo:** `pycadwork`
- **Broad command:** `uv run pytest tests/versioning/ tests/test_examples.py -q`
- **Fed inputs:** fake-backed models via autouse adapter; optional IT uses
  `tests/fixtures/model/timber-framed-slab.3d`
- **Judged by:** §2 exact methods (unit + skipif IT + docs/example string checks)
- **Against goldens:** none required beyond exact assert expectations and IT
  `ok: true` result file
- **No-regressions clause:** full suite `uv run pytest -q` green (IT skipped when
  cadwork absent is still GREEN)
- **Graphical legs:** none — headless-only
- **Deferred Manual (HITL) legs:** optional human smoke of the dock inside
  cadwork (non-blocking); not required for capstone GREEN

### 5b. Cross-factory acceptance leg (integration capstone)

n/a — every story is repo-local; per-repo capstone suffices.

## 6. Open questions

(none)
