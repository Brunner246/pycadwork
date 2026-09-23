# Seed: Module README, examples, package listings

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 02
- **Type:** AFK
- **Headless:** true
- **Capstone:** false
- **Producer:** false
- **Interim:** false
- **Integration:** false
- **Lane:** L2
- **Blocked by:** 01-work-unit.md
- **Estimated size:** M
- **Priority:** High
- **Target repo:** `pycadwork`
- **Branch:** `feature/work-units-02-docs-examples`

## Source documents

- **Spec:** `docs/spec/work-units.md`
- **Research:** `docs/research/work-units.md`
- **Architecture:** `docs/architecture/work-units.md`
- **Verification:** `docs/verification/work-units.md`

## Scope (Definition of Ready)

Teach `WorkUnit` the way every other pycadwork module is taught: `docs/work.md`
(the module README), `examples/work.py` on the CI example tour, and listing
rows in `README.md`, `docs/README.md`, `docs/architecture.md` (layout table +
mermaid node), and `examples/README.md` / `examples/__init__.py` `MODULES`.

Do not add `src/pycadwork/work/README.md`.

## Spec guardrail

**In scope (verbatim):**

> `docs/work.md` is the module README: problem, `WorkUnit` tour, report, limitations (untracked, no geometry rollback, vs SQL `UnitOfWork`). `examples/work.py` with `demo_*` functions + `run()`: apply, run, rollback, undo=False, report diffs. Append `"work"` to `MODULES`. Table rows in `examples/README.md`, `README.md`, `docs/README.md`. Package-layout row + mermaid node in `docs/architecture.md`.

**Out of scope (verbatim):**

> Changing `WorkUnit` behaviour. `src/pycadwork/work/README.md`. CSV writer. Real-cadwork Ctrl+Z tutorial. Persistence `UnitOfWork` docs rewrite beyond a one-line “not this” pointer in `docs/work.md`.

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

- **Driving port(s):** existing `WorkUnit` (seed 01)
- **Driven port(s) + test double:** autouse fake via `tests/test_examples.py`
- **Deep module(s):** none new — teaching assets only
- **SOLID / cross-cutting (verbatim):** Document in `docs/work.md`, in the first screenful, that this is **not** `persistence.UnitOfWork`.
- **Out of scope (architecture §7):** all product-code expansion

If this slice needs a `[NEW]` architectural decision, STOP and run `/lp-to-architecture` first.

## Reusable building blocks

- `examples/utilities.py` — `demo_*` + `run()` shape
- `examples/__init__.py` — `MODULES` tuple (append `"work"`)
- `examples/README.md`, `docs/README.md`, `README.md` — table row pattern
- `docs/architecture.md` — mermaid + package layout table
- `docs/utilities.md` / `docs/rules.md` — module-doc tone
- Seed 01 public API — examples import only from `pycadwork`

## Touched files (predicted)

```
- docs/work.md — module README
- docs/README.md — Working with the model bullet
- docs/architecture.md — mermaid node + layout row
- README.md — documentation table row
- examples/work.py — demo_apply, demo_run, demo_rollback, demo_undo_false, demo_report
- examples/__init__.py — MODULES += "work"
- examples/README.md — table row
```

## Acceptance criteria

- [ ] `docs/work.md` exists, opens with WorkUnit vs SQL UnitOfWork, shows apply/run/rollback/undo/report
- [ ] `examples.work.run()` completes under the fake (`tests/test_examples.py -k work`)
- [ ] `"work"` is in `examples.MODULES`
- [ ] README / docs/README / examples/README / architecture layout mention `pycadwork.work`
- [ ] No `src/pycadwork/work/README.md`
- [ ] Tests with fakes from architecture §5 (example tour)
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest tests/test_examples.py tests/work/ -q`
- **Runtime exercise:** `uv run pytest tests/test_examples.py -k work` — US-6
- **Inner-loop:** `uv run pytest tests/test_examples.py -k work`
- **Graphical / Manual:** none

## First steps for this session

1. `@`-attach this seed + BOARD + Spec + architecture (+ research/verification if present).
2. Run implement — it switches to this seed’s `**Branch:**` itself.
3. You own commits and pushes on this seed branch (plugin does not push seed branches).

```
/lp-to-implement @docs/sessions/work-units/02-docs-examples.md @docs/sessions/work-units/BOARD.md @docs/spec/work-units.md @docs/architecture/work-units.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/work-units/02-docs-examples.md @docs/sessions/work-units/BOARD.md @docs/spec/work-units.md @docs/architecture/work-units.md
```
