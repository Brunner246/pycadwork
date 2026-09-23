# Seed: Cadwork run-program integration harness

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 02
- **Type:** AFK
- **Headless:** true
- **Capstone:** false
- **Producer:** true
- **Interim:** false
- **Integration:** false
- **Lane:** L1
- **Blocked by:** 01-facade-model-aware.md
- **Estimated size:** M
- **Priority:** High
- **Target repo:** `pycadwork`
- **Branch:** `feature/git-like-model-versioning-02-cadwork-it`

## Source documents

- **Spec:** `docs/spec/git-like-model-versioning.md`
- **Research:** `docs/research/git-like-model-versioning.md`
- **Architecture:** `docs/architecture/git-like-model-versioning.md`
- **Verification:** `docs/verification/git-like-model-versioning.md`

## Scope (Definition of Ready)

Build the `[NEW]` real-cadwork integration harness (verification §4): host pytest
copies `tests/fixtures/model/timber-framed-slab.3d`, writes an in-cadwork
run-program script that exercises model-aware commit → branch → edit →
`checkout` back, launches via terminal/`ProcessLauncher` (`--run-program` /
`/RUNPROGRAM`, prefer `/NO-GUI`), asserts exit code + result JSON. Skip when
`ci_start` or git unavailable (US-6).

## Spec guardrail

**In scope (verbatim):**

> Add a real-cadwork integration test that launches the fixture model via `pycadwork.terminal` (`open … --run-program …`) and proves a commit → branch → edit → switch-back loop. `pytest.mark.skipif` when `ci_start` or git/GitPython unavailable — never fail default CI for missing cadwork.

**Out of scope (verbatim):**

> Facade re-semantics (seed 01). Dock/examples/docs (seed 03). Requiring cadwork in CI. Stash/tags/rebase.

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

- **Driving port(s):** host test only; in-cadwork script uses public `ModelVersioning`
- **Driven port(s) + test double:** `ProcessLauncher` / `SubprocessLauncher` for host; real cadwork inside process (no FakeCadworkAdapter in the run-program script)
- **Deep module(s):** thin IT harness (architecture §3.3)
- **SOLID / cross-cutting:** Host never imports live model state; result sidecar JSON
- **Out of scope (architecture §7):** product CLI for versioning; QThread dock

> Producer: build `[NEW]` verification assets/tooling from verification §3/§4 only.

## Reusable building blocks

- `src/pycadwork/terminal/cli.py` / `launcher.py` / `translation.py` — open + run-program
- `tests/fixtures/model/timber-framed-slab.3d` — fixture input
- `pycadwork.versioning.is_git_available` / `find_ci_start` — skip gates
- Seed 01 API: model-aware `checkout` / `commit` / `create_branch`

## Touched files (predicted)

```
- tests/versioning/test_cadwork_run_program.py — host orchestrator + skipif
- tests/versioning/_cadwork_it_script.py (or fixtures/versioning/…) — run-program body
- tests/fixtures/ (only if a small helper asset is required; prefer tmp script write)
```

## Acceptance criteria

- [ ] Test module skips cleanly without cadwork/git (default CI green)
- [ ] With cadwork+git: launches fixture via run-program path and asserts `ok: true` result file
- [ ] Script uses model-aware defaults (no legacy checkout-then-restore teaching)
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest tests/versioning/test_cadwork_run_program.py -v`
- **Runtime exercise:** same (skip or green)
- **Inner-loop:** same
- **Graphical / Manual:** none required (prefer `--no-gui`)

## First steps for this session

1. `@`-attach this seed + BOARD + Spec + architecture (+ research/verification if present).
2. Confirm seed 01 is Done and merged/available on the feature branch tip used as base.
3. Run implement on this seed’s branch.

```
/lp-to-implement @docs/sessions/git-like-model-versioning/02-cadwork-it.md @docs/sessions/git-like-model-versioning/BOARD.md @docs/spec/git-like-model-versioning.md @docs/architecture/git-like-model-versioning.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/git-like-model-versioning/02-cadwork-it.md @docs/sessions/git-like-model-versioning/BOARD.md @docs/spec/git-like-model-versioning.md @docs/architecture/git-like-model-versioning.md
```
