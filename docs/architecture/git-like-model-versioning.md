# Architecture: Git-like model versioning (model-aware defaults)

> **Source Spec:** `docs/spec/git-like-model-versioning.md`
> **Source research:** `docs/research/git-like-model-versioning.md`
> **Status:** Draft
>
> Every decision below cites Spec §, research `file:line`, or is labeled `[NEW]` (rules in §10).

## 1. Context

This plan does **not** redesign `pycadwork.versioning`. The package already sits
hexagonally: a deep facade (`ModelVersioning`) over a driven `Repository` port,
pure codec/sync modules, and cadwork access only through `Document` /
persistence (`docs/architecture.md`, research Context). The work is **policy
relocation**: model-load and dirty-tree rules move into the facade’s public git
verbs so callers get git-like defaults without a second API. Ports and adapters
stay; signatures and one error type change.

## 2. System shape (hexagonal map)

```text
Driving adapters                    Domain core                         Driven adapters
─────────────────                   ───────────                         ───────────────
Dock / examples  ──►  ModelVersioning (facade policy)  ──►  Repository  ──►  GitRepository
Scripts / IT     ──►         │                            │              ──►  FakeRepository
                             ├── SnapshotCodec (pure)
                             ├── classify / SyncPlan (pure)
                             └── Document / ModelReader / ModelWriter
                                         │
                                         ▼
                                  cadwork_adapter (existing seam)
```

### 2.1 Driving (primary) ports — what callers do

There is no separate Protocol for the facade today; the **public surface is the
class** (consistent with the rest of pycadwork). Callers depend on:

| Port (conceptual) | Shape (key methods) | Source |
|-------------------|---------------------|--------|
| `ModelVersioning` | `commit`, `checkout`, `pull`, `merge`, `reload_model`, `switch_to`, `sync_status`, `preview_switch`, `status`, `log`, … | Spec Implementation Decisions — API; research key finding 1–3 |

No new driving port type is introduced.

### 2.2 Driven (secondary) ports — what the core needs from outside

| Port | Shape | Test double | Source |
|------|-------|-------------|--------|
| `Repository` | `stage`, `commit`, `checkout`, `merge`, `pull`, `push`, `log`, `status`, `read_file_at_ref`, … | `FakeRepository` | research Reusable building blocks; `_repository.py` |
| Cadwork / model I/O | via `Document`, `ModelReader`, `ModelWriter` (existing) | `FakeCadworkAdapter` (autouse in unit tests) | `docs/testing.md`, research finding 8 |

### 2.3 Adapters

| Adapter | Implements port | Tech | Reuses |
|---------|-----------------|------|--------|
| `GitRepository` | `Repository` | GitPython + `git` CLI | research; `_git.py` |
| `FakeRepository` | `Repository` | in-memory + tmp working tree | `tests/_fakes/repository.py` |
| `SubprocessLauncher` | `ProcessLauncher` | host process spawn for IT only | `terminal/launcher.py` — **not** part of versioning domain; IT host adapter |

### 2.4 Cross-factory port contracts

n/a — no story spans repos.

## 3. Deep modules

### 3.1 `ModelVersioning` (policy facade)

- **Interface (what callers see):**
  - `checkout(ref, *, apply_to_model=True, strategy="smart", force=False) -> ReloadReport | SmartSwitchReport | None`
  - `pull` / `merge` with the same keyword pattern
  - `switch_to` → alias of model-aware `checkout`
  - `reload_model`, `commit`, `sync_status`, `preview_switch` (existing)
  - raises `DirtyWorkingTreeError` when guard trips
- **Hidden complexity:** dirty preflight via `sync_status`; ordered git-then-load;
  conflict short-circuit (no load after `MergeConflictError`); smart vs full
  reload; binary path resolution under `model/`.
- **Why deep, not shallow:** callers name one verb; the facade owns the
  model↔git coupling that used to leak into every example.
- **Source:** Spec Implementation Decisions — API; research findings 1–4.

### 3.2 `Repository` + pure helpers (unchanged depth)

- **Interface:** Protocol in `_repository.py` — pure git.
- **Hidden complexity:** LFS, conflict detection, detached HEAD naming — stay in
  `GitRepository`.
- **Why deep:** versioning remains testable with `FakeRepository` and no cadwork
  in the git layer.
- **Source:** research finding 6; existing package design.

### 3.3 Integration-test host harness (thin)

- **Interface:** pytest module that copies fixture, writes run-program script,
  launches via terminal/`ProcessLauncher`, asserts result file.
- **Hidden complexity:** discovery of `ci_start`, skipif gates, temp isolation.
- **Why deep enough:** host never imports live model state; cadwork process owns
  the domain exercise.
- **Source:** Spec Testing Decisions; research finding 7–8.

## 4. SOLID review (per module)

| Module | SRP | OCP | LSP | ISP | DIP |
|--------|-----|-----|-----|-----|-----|
| `ModelVersioning` | One reason: bridge live model ↔ repo policy | New strategies stay on `strategy` / flags without new subclasses | Reports remain frozen dataclasses; `None` only when apply_to_model=False | Callers use facade methods, not Protocol soup | Depends on `Repository` Protocol + persistence types, not GitPython |
| `Repository` | Git operations only | New git ops only if facade needs them (none in this plan) | Fake and Git both satisfy Protocol | Narrow method set already | N/A (port) |
| IT harness | Process orchestration only | Swap launcher fake in unit tests of harness if any | N/A | Does not pull versioning internals | Uses public `ModelVersioning` inside the *in-cadwork* script |

## 5. Fake-first test strategy

- **Default policy:** facade tests inject `FakeRepository` + autouse
  `FakeCadworkAdapter`. No mocks of `Repository` methods unless interaction
  order is the assertion.
- **Per-port doubles:** §2.2.
- **Direct-tested deep modules:** `ModelVersioning` (fake-backed);
  `classify`/`SnapshotCodec` already unit-tested — leave alone unless a
  regression appears.
- **Application-service-tested:** none new.
- **Runtime verification of real adapters:**
  - `GitRepository`: existing `tests/versioning/test_git_integration.py`
    (skipif no git).
  - Live cadwork path: new IT (skipif no `ci_start` / git) — Spec Testing
    Decisions.
- **Fake ownership:** continue `tests/_fakes/repository.py`; do not fork a
  second fake for dirty-guard tests.

## 6. Cross-cutting decisions

- **Concurrency / threading:** unchanged — facade is single-threaded; dock keeps
  GUI-thread ops (research Constraints). IT runs inside cadwork’s process via
  `/RUNPROGRAM`.
- **Error handling:**
  - `DirtyWorkingTreeError(RepositoryError)` — **`[NEW]`** — refuse load when
    live model has `stale`/`missing` vs checked-out snapshot and `force=False`.
  - `MergeConflictError` — still no model load after conflict.
  - Other failures remain `RepositoryError` / `GitNotAvailableError` /
    `CodecError`.
- **Logging / observability:** no new logging subsystem; dock continues
  `notified` signals; IT writes a JSON result sidecar.
- **Configuration / wiring:** `ModelVersioning.open(repo=…)` for tests;
  `open()` for live. IT script uses `open()` inside cadwork after fixture open.
- **ABI / packaging:** still optional `pycadwork[git]`; terminal remains host
  CLI. Breaking method defaults — call out in changelog/docs only (no package
  major required by this plan’s scope, but treat as breaking API note).

## 7. Out of scope (architectural)

- New `VersioningService` Protocol layer over the facade
- Stash/tag/rebase ports
- Moving smart-switch into the `Repository` port
- Auto-merge strategies
- QThread worker architecture for the dock

## 8. Open questions

(none)

## 9. References

- Spec: `docs/spec/git-like-model-versioning.md`
- Research: `docs/research/git-like-model-versioning.md`
- Package architecture overview: `docs/architecture.md`
- Domain docs: `docs/versioning.md`, `docs/terminal.md`, `docs/testing.md`

## 10. Reuse audit (REQUIRED — every capability classified)

### 10.1 What was searched

| Repo | Searched for | Found / Not found |
|------|--------------|-------------------|
| pycadwork | `ModelVersioning`, `switch_to`, `checkout`, `reload_model` | `src/pycadwork/versioning/_versioning.py` |
| pycadwork | `Repository` Protocol, `MergeConflictError` | `src/pycadwork/versioning/_repository.py` |
| pycadwork | `FakeRepository` | `tests/_fakes/repository.py` |
| pycadwork | `sync_status` / `classify` / `SyncPlan` | `_versioning.py`, `_sync.py` |
| pycadwork | `DirtyWorkingTree` / `dirty` error types in versioning | not found — only `is_dirty` on `RepoStatus` |
| pycadwork | `ProcessLauncher`, `--run-program` | `src/pycadwork/terminal/` |
| pycadwork | fixture `timber-framed-slab.3d` | `tests/fixtures/model/` |

### 10.2 Classification

| Capability | Verdict | Source / Rationale |
|------------|---------|--------------------|
| `Repository` port | **Reuse** | `_repository.py` — pure git seam unchanged |
| `GitRepository` | **Reuse** | `_git.py` |
| `FakeRepository` | **Reuse** | `tests/_fakes/repository.py` |
| `ModelVersioning` | **Reuse** (extend) | `_versioning.py` — re-semantics + kwargs only |
| `SnapshotCodec` / `classify` | **Reuse** | `_codec.py`, `_sync.py` |
| `Document` / persistence reader-writer | **Reuse** | existing model I/O |
| `ProcessLauncher` / terminal open | **Reuse** | IT host only |
| Fixture `.3d` | **Reuse** | `tests/fixtures/model/timber-framed-slab.3d` |
| `DirtyWorkingTreeError` | **`[NEW]`** | Searched versioning errors; only `RepositoryError` hierarchy exists — need a distinct, catchable refuse for live-model dirty guard (Spec Implementation Decisions) |
| Result-file IT script pattern | **`[NEW]`** (test-only) | No existing cadwork run-program IT; host harness is test code, not product surface |

### 10.3 Reuse-first rule for downstream slicing

Seeds must not invent a second repository port, a parallel smart-switch module, or
a new dock architecture. Implement policy only on `ModelVersioning`; use existing
fakes; IT hosts through terminal/launcher APIs already shipped.
