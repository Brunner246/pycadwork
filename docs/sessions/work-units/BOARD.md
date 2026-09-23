# Session Board: pycadwork — Work units for bulk live-model mutations

**Source Spec:** `docs/spec/work-units.md`
**Source research:** `docs/research/work-units.md`
**Source architecture:** `docs/architecture/work-units.md`
**Source verification:** `docs/verification/work-units.md`
**Target repo:** `pycadwork`
**Human reviewers:** `n/a`
**Human signature:** `n/a`
**Target branch:** `feature/work-units` — plan-wide feature branch; created and **pushed to origin** by `/lp-to-session-seeds`. Per-seed work branches are each seed’s `**Branch:**` (user-confirmed, local only until you push).
**Source bugs:** `n/a`

## Kanban policies

- **WIP limit:** 1 (default)
- **Pull rule:** only pull a card whose `Blocked by` is empty/None AND lane WIP < limit
- **Definition of Ready:** seed complete, blockers Done
- **Definition of Done:** Acceptance criteria + Verification green, including **Runtime exercise**

## Lanes

- **L1:** [01-work-unit]
- **L2:** [02-docs-examples]
- **Lf1:** [03-capstone] — dedicated final lane for capstone

## Dependency graph

```mermaid
graph LR
  01[01-work-unit] --> 02[02-docs-examples]
  01 --> 03[03-capstone]
  02 --> 03
```

## Conflict-risk matrix

| Seed A | Seed B | Overlapping paths | Resolution |
|--------|--------|-------------------|------------|
| 01 | 02 | none expected (`src/` + `tests/work/` vs `docs/` + `examples/`) | serialise anyway — 02 is `Blocked by` 01 so examples import a real `WorkUnit` |
| 01 | 03 | n/a (capstone has no predicted paths) | capstone after 01 |
| 02 | 03 | n/a | capstone after 02 |

## Cards

| ID | Title | Type | Headless | Lane | Blocked by | Arch footprint | Status |
|----|-------|------|----------|------|------------|----------------|--------|
| 01 | WorkUnit + undo seam + unit tests | AFK | true | L1 | None — Ready | WorkUnit, report DTOs, ElementsAdapter undo, FakeState | Done |
| 02 | Module README, examples, package listings | AFK | true | L2 | 01-work-unit.md | docs/work.md, examples/work.py, README tables | Done |
| 03 | Capstone verification | AFK | true | Lf1 | 01-work-unit.md, 02-docs-examples.md | Verification-only | Done |

Status ∈ {Backlog, Ready, In Progress, Done}.

## Revision log

(append-only; used by `/lp-revise`)

<!-- entries -->
- 2026-08-31 capstone: GREEN — `uv run pytest tests/work/ tests/test_examples.py tests/test_public_surface.py tests/test_isolation.py -q` 37 passed; full suite `uv run pytest -q` 952 passed, 1 skipped (pre-existing skipif, not work-units). Fast-forwarded `feature/work-units-03-capstone` onto seed 02 (`d579898`) so 01+02 were on the seed branch. Residual: seed 02 commit message claims `docs/work.md` but the file was never added; it exists untracked and `README.md` already links to it. Pytest does not assert file presence, so this did not block GREEN. Not local-fixable as a test failure; user should add `docs/work.md` when committing.
