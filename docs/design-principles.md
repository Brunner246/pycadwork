# Design principles

These run through the whole codebase and are worth knowing before you extend it:

- **Version isolation.** `pycadwork` stays agnostic of any specific cwapi3d
  version; all cwapi3d calls go through the one adapter seam. Nothing outside
  `cadwork_adapter` imports `cadwork` or a `*_controller`.
- **Uniform element API.** Aggregates return `list[Element]`. There are no
  `.beams` / `.plates` / `.drillings` accessors — a common polymorphic base plus
  `members_of(cls)` / `children_of(cls)` covers every case.
- **Cover objects link by grouping, not containment.** Members share a
  `group`/`subgroup` value; the active mode comes from
  `get_element_grouping_type()`, read at call time.
- **Builder flexibility for composites.** Composite construction (cover objects)
  offers more than one assembly strategy; no single path is forced.
- **Discovery as free functions.** Model-scan APIs such as `discover_covers` are
  module-level functions, not classmethods on a wrapper type.
- **Small surfaces via composition.** `Element` aggregates `attrs` and
  `geometry` components rather than inheriting their methods, keeping each class
  focused.
