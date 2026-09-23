# Research: git-like-model-versioning

## Context

`pycadwork.versioning` already implements a full git workflow over cadwork models:
JSONL snapshot + LFS-tracked binary, branch/checkout/commit/push/pull/merge, and a
**smart** live-model reconcile by content fingerprint. The remaining gap is
**mental-model mismatch**: users coming from git expect operations named like git
verbs to also affect the *working artifact* (here: the live 3d model). Today many
verbs only touch the working tree on disk and leave the live model stale, which
the package and examples document as a deliberate surprise.

This plan is a **breaking re-semantics** of those verbs so the default path
matches that expectation, with keyword escape hatches for pure-git scripting, a
dirty live-model guard, dock/example/doc alignment, and a real-cadwork
integration test driven by `pycadwork.terminal` + the timber-framed-slab fixture.

## Scope of exploration

- `src/pycadwork/versioning/` (facade, repository seam, git backend, smart sync, codec)
- `examples/versioning*.py` (dock widget + in-cadwork scripts + CI-safe fake tour)
- `docs/versioning.md`
- `tests/versioning/`, `tests/_fakes/repository.py`, `tests/fixtures/model/`
- `src/pycadwork/terminal/` (`--run-program` / `/RUNPROGRAM` for integration launch)

## Key findings

1. **Dual API is the root UX problem.** `checkout` only swaps git files
   (`_versioning.py:460-462`); `switch_to` is the one-shot "git checkout fully"
   path (`_versioning.py:393-407`) that calls `checkout` then `reload_model`.
   Docs and the branch-workflow example still teach the old two-step surprise
   (`examples/versioning_branch_workflow.py:18-24` uses
   `restore(apply_to_model=True)` after checkout).

2. **Pull / merge leave the live model stale.** Both are pure passthroughs
   (`_versioning.py:464-472`, `518-520`). The dock explicitly tells the user to
   press “Load model to version” after merge/pull
   (`examples/versioning_dock_widget.py:270-277`, `309-316`).

3. **Smart switch is production-ready and should remain the default load path.**
   Content-fingerprint classify lives in pure `_sync.py`; `reload_model` /
   `switch_to` default to `strategy="smart"` and only churn true deltas
   (`_versioning.py:331-374`). Container atomicity and GUID reimport limits are
   already documented in `docs/versioning.md`.

4. **Dirty live model is detectable but not gated.** `sync_status()` /
   `preview_switch(ref)` return a `SyncPlan(unchanged, stale, missing)` without
   mutating (`_versioning.py:415-437`). The dock confirms before switch/reload
   but the **API never refuses** a destructive switch. Git-like “refuse dirty
   unless force” needs a new error type and a shared preflight helper.

5. **Working-tree layout already solves Windows open-file constraints.** The
   managed `.gitignore` ignores the live open model at repo root and tracks only
   `manifest.json` + `model/` (`_versioning.py:67-90`, `_copy_binary` at
   `270-289`). Checkout never unlinks the file cadwork holds open. Re-semantics
   must not reintroduce tracking the open path.

6. **Repository seam stays pure-git.** `Repository` Protocol
   (`_repository.py:70-194`) has no model awareness — correct. All model load
   policy belongs on `ModelVersioning`. Fake-backed tests
   (`tests/_fakes/repository.py`) already exercise commit → branch → checkout
   without a git executable.

7. **Terminal launch path for integration tests already exists.**
   `cadwork open FILE --run-program PATH --no-gui` maps to `/RUNPROGRAM` +
   `/NO-GUI` (`terminal/cli.py:81-96`, `docs/terminal.md:192-211`).
   `ProcessLauncher` / `SubprocessLauncher` (`terminal/launcher.py:49-64`) and
   `find_ci_start` (`67-109`) mirror the versioning git-discovery pattern.
   Fixture model: `tests/fixtures/model/timber-framed-slab.3d`.

8. **Test pyramid today:** fake-backed facade tests
   (`tests/versioning/test_versioning.py`), pure codec/sync unit tests, real-git
   tests skipped without git (`test_git_integration.py`). **No** real-cadwork
   integration suite yet; autouse `FakeCadworkAdapter` in `tests/conftest.py`
   means a real-cadwork test must live outside that swap (or opt out of the
   fixture).

## Reusable building blocks

| Building block | Path | Role in this plan |
|----------------|------|-------------------|
| `ModelVersioning` facade | `src/pycadwork/versioning/_versioning.py` | Own re-semantics of checkout/pull/merge + dirty guard |
| `switch_to` / `reload_model` | `_versioning.py:331-407` | Become the default body of model-aware checkout |
| `sync_status` / `preview_switch` | `_versioning.py:415-437` | Dirty detection + dock previews |
| `classify` / `SyncPlan` | `src/pycadwork/versioning/_sync.py` | Content fingerprint reconcile (unchanged) |
| `Repository` Protocol | `src/pycadwork/versioning/_repository.py` | Pure-git port; unchanged contract |
| `GitRepository` | `src/pycadwork/versioning/_git.py` | Real git ops (checkout/merge/pull already correct) |
| `FakeRepository` | `tests/_fakes/repository.py` | Unit/integration-of-facade without git |
| Dock MVVM | `examples/versioning_dock_widget.py` | ViewModel already calls `switch_to`; simplify post-pull messaging |
| Terminal open + run-program | `src/pycadwork/terminal/cli.py`, `launcher.py` | Drive real cadwork for IT |
| Fixture `.3d` | `tests/fixtures/model/timber-framed-slab.3d` | Real model under version control for IT |
| Existing versioning unit tests | `tests/versioning/` | Extend for new defaults / force / DirtyWorkingTreeError |

## Constraints & gotchas

- **Breaking change:** any caller that today does `checkout` / `pull` / `merge`
  expecting file-only behavior will start loading the live model. Escape hatch:
  `apply_to_model=False`.
- **cadwork API is not thread-safe** — dock already runs ops on the GUI thread
  (`versioning_dock_widget.py:44-50`). Integration scripts under `/RUNPROGRAM`
  run inside cadwork’s process; they must not assume a host-Python event loop.
- **`import_3dc_file` is additive and mints new ids/GUIDs** — smart switch is
  mandatory default; `strategy="full"` remains the clean-reset escape hatch.
- **Merge conflicts** stay surfaced (`MergeConflictError`); never auto-resolve;
  do not load model after a conflicted merge/pull.
- **GitPython + git (+ optional LFS)** required for real repos; fake path for CI.
- **Real-cadwork IT** requires `ci_start.exe` + licensed cadwork; must
  `skipif` when unavailable so default CI stays green.
- **Autouse fake adapter** will break real-cadwork tests unless those tests are
  structured to not use it (e.g. module-level mark + no reliance on fake, or a
  dedicated test path that skips the monkeypatch when a env/skip gate fails
  early — prefer: IT script runs *inside* cadwork via `--run-program`, while
  the pytest host only launches the process and asserts exit code / sidecar
  result file).

## Cross-repo grounding

Single-repo (`pycadwork` only). No sibling factories.

## Open questions

(none deferred — all product decisions resolved in the grill.)

## Out of scope

- Stash, tags, rebase, cherry-pick, amend, multiple worktrees
- Auto-merge of JSONL or binary models
- Moving versioning off GitPython to libgit2 / hosted APIs
- Threading pure-git ops onto a `QThread` in the dock (noted as production
  follow-up, not this plan)
- Publishing a separate CLI for versioning verbs

## References

- `docs/versioning.md` — current public contract and limitations
- `docs/terminal.md` — `open --run-program` / `--no-gui`
- `docs/testing.md` — fake-first suite and adapter injection
- Package docstring `src/pycadwork/versioning/__init__.py`
