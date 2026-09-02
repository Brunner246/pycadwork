"""Stdlib parser for the v1 Gherkin dialect.

Supports Feature, Background, Scenario, Scenario Outline, Examples tables,
Given/When/Then/And/But, and ``#`` comments. Tags, doc strings, ``language:``,
and ``Rule:`` raise :class:`GherkinError` with a line number.
"""

from __future__ import annotations

import re

from pycadwork.gherkin.ast import Feature, Scenario, Step
from pycadwork.gherkin.report import GherkinError

_LANGUAGE = re.compile(r"^\s*#?\s*language\s*:", re.IGNORECASE)
_UNSUPPORTED_KEYWORD = re.compile(r"^([A-Z][A-Za-z ]*):")

_STEP_PREFIXES = (
    ("Given ", "Given"),
    ("When ", "When"),
    ("Then ", "Then"),
    ("And ", "And"),
    ("But ", "But"),
)

# Longest keyword first so "Scenario Outline:" wins over "Scenario:".
_BLOCK_PREFIXES = (
    ("Scenario Outline:", "outline"),
    ("Background:", "background"),
    ("Examples:", "examples"),
    ("Scenario:", "scenario"),
    ("Feature:", "feature"),
    ("Rule:", "rule"),
)


def parse(text: str) -> Feature:
    """Parse feature text into an expanded :class:`Feature`."""
    return _Parser(text).parse()


class _Parser:
    def __init__(self, text: str) -> None:
        self.lines = text.lstrip("\ufeff").splitlines()
        self.title = ""
        self.description: list[str] = []
        self.background: list[Step] = []
        self.drafts: list[_Draft] = []
        self._current: _Draft | None = None
        self._in_examples = False
        self._seen_feature = False
        self._seen_scenario = False
        self._in_background = False

    def parse(self) -> Feature:
        if not self.lines:
            raise GherkinError("line 1: expected Feature:")
        for lineno, raw in enumerate(self.lines, start=1):
            self._feed(lineno, raw)
        self._finish_draft()
        if not self._seen_feature:
            raise GherkinError("line 1: expected Feature:")
        scenarios = tuple(
            scenario for draft in self.drafts for scenario in draft.expand(self.background)
        )
        return Feature(
            title=self.title,
            scenarios=scenarios,
            description="\n".join(self.description).strip(),
        )

    def _feed(self, lineno: int, raw: str) -> None:
        if _LANGUAGE.match(raw):
            raise GherkinError(f"line {lineno}: language: header is not supported")
        if '"""' in raw:
            raise GherkinError(f"line {lineno}: doc strings are not supported")
        stripped = _strip_comment(raw).strip()
        if not stripped:
            return
        if stripped.startswith("@"):
            raise GherkinError(f"line {lineno}: tags are not supported")
        if stripped.startswith("*"):
            raise GherkinError(f"line {lineno}: unsupported keyword '*'")

        for prefix, kind in _BLOCK_PREFIXES:
            if stripped.startswith(prefix):
                rest = stripped[len(prefix) :].strip()
                self._block(lineno, kind, rest)
                return

        for prefix, keyword in _STEP_PREFIXES:
            if stripped.startswith(prefix):
                rest = stripped[len(prefix) :].strip()
                self._step(lineno, keyword, rest)
                return

        if stripped.startswith("|"):
            self._table_row(lineno, stripped)
            return

        extra = _UNSUPPORTED_KEYWORD.match(stripped)
        if extra is not None:
            raise GherkinError(f"line {lineno}: unsupported keyword {extra.group(1)!r}")

        if self._in_background or self._current is not None:
            raise GherkinError(f"line {lineno}: expected a step, got {stripped!r}")
        if self._seen_feature:
            self.description.append(stripped)
            return
        raise GherkinError(f"line {lineno}: expected Feature:")

    def _block(self, lineno: int, kind: str, rest: str) -> None:
        if kind == "rule":
            raise GherkinError(f"line {lineno}: Rule: blocks are not supported")
        if kind == "feature":
            if self._seen_feature:
                raise GherkinError(f"line {lineno}: multiple Feature: blocks")
            self._seen_feature = True
            self.title = rest
            return
        if not self._seen_feature:
            raise GherkinError(f"line {lineno}: expected Feature:")
        if kind == "background":
            if self._seen_scenario:
                raise GherkinError(f"line {lineno}: Background must precede scenarios")
            self._finish_draft()
            self._in_background = True
            self._in_examples = False
            return
        if kind == "examples":
            if self._current is None or not self._current.is_outline:
                raise GherkinError(f"line {lineno}: Examples: is only valid in a Scenario Outline")
            self._in_background = False
            self._in_examples = True
            return
        # scenario / outline
        self._finish_draft()
        self._in_background = False
        self._in_examples = False
        self._seen_scenario = True
        self._current = _Draft(name=rest, line=lineno, is_outline=(kind == "outline"))

    def _step(self, lineno: int, keyword: str, text: str) -> None:
        if self._in_examples:
            raise GherkinError(f"line {lineno}: step is not valid inside Examples")
        target = self._step_target(lineno)
        if keyword in ("And", "But"):
            if not target:
                raise GherkinError(f"line {lineno}: {keyword} without a previous step")
            kind = target[-1].kind
        else:
            kind = keyword
        target.append(Step(kind=kind, text=text, line=lineno, keyword=keyword))

    def _step_target(self, lineno: int) -> list[Step]:
        if self._in_background:
            return self.background
        if self._current is not None:
            return self._current.steps
        raise GherkinError(f"line {lineno}: step outside Scenario or Background")

    def _table_row(self, lineno: int, stripped: str) -> None:
        if not self._in_examples or self._current is None:
            raise GherkinError(f"line {lineno}: table row outside Examples")
        cells = _cells(stripped)
        if self._current.headers is None:
            self._current.headers = cells
            return
        if len(cells) != len(self._current.headers):
            raise GherkinError(
                f"line {lineno}: Examples row has {len(cells)} cells, "
                f"expected {len(self._current.headers)}"
            )
        self._current.rows.append(cells)

    def _finish_draft(self) -> None:
        if self._current is None:
            return
        if self._current.is_outline and self._current.headers is None:
            raise GherkinError(f"line {self._current.line}: Scenario Outline is missing Examples")
        self.drafts.append(self._current)
        self._current = None
        self._in_examples = False


class _Draft:
    def __init__(self, name: str, line: int, is_outline: bool) -> None:
        self.name = name
        self.line = line
        self.is_outline = is_outline
        self.steps: list[Step] = []
        self.headers: tuple[str, ...] | None = None
        self.rows: list[tuple[str, ...]] = []

    def expand(self, background: list[Step]) -> list[Scenario]:
        if not self.is_outline:
            steps = tuple(background + self.steps)
            return [Scenario(name=self.name, steps=steps, line=self.line)]
        assert self.headers is not None
        scenarios: list[Scenario] = []
        for index, row in enumerate(self.rows):
            mapping = dict(zip(self.headers, row, strict=True))
            name = _substitute(self.name, mapping)
            steps = tuple(_substitute_step(step, mapping) for step in background + self.steps)
            scenarios.append(Scenario(name=name, steps=steps, line=self.line, outline_row=index))
        return scenarios


def _strip_comment(line: str) -> str:
    in_string = False
    for index, char in enumerate(line):
        if char == '"':
            in_string = not in_string
        elif char == "#" and not in_string:
            return line[:index]
    return line


def _cells(line: str) -> tuple[str, ...]:
    raw = line.strip()
    parts = raw.split("|")
    inner = parts[1:-1] if raw.endswith("|") else parts[1:]
    return tuple(cell.strip() for cell in inner)


def _substitute(text: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        text = text.replace(f"<{key}>", value)
    return text


def _substitute_step(step: Step, mapping: dict[str, str]) -> Step:
    return Step(
        kind=step.kind,
        text=_substitute(step.text, mapping),
        line=step.line,
        keyword=step.keyword,
    )
