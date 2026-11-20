"""Keep the closed-research register structurally sound and consistent with the forward plan."""

import argparse
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from agent_py.quality.plan_integrity import PLAN_DOC
from agent_py.quality.plan_model import read_tasks
from agent_py.quality.project_root import discover_project_root

_LOG = logging.getLogger(__name__)

REGISTER_DOC = Path("docs/impl/future-research.md")
REQUIRED_PARTS = ("Question", "Answer", "Reopening condition", "Do not re-run")

_REQUIRED_KEYS = tuple(part.lower() for part in REQUIRED_PARTS)
_TASK_ID = r"`([a-z0-9][a-z0-9-]*)`"
_TASK_IDS = re.compile(rf"{_TASK_ID}(?:,\s*{_TASK_ID})*")
_CLOSED_QUESTION = re.compile(rf"^## {_TASK_ID} -- \S")
_PART = re.compile(r"^### (?P<title>.+?)\s*$")
_REOPENING = re.compile(r"^- Reopening task:\s*(?P<value>.*?)\s*$")


@dataclass(slots=True)
class ClosedQuestion:
    """One `##` register section and the structure a parser can see in it."""

    line: int
    identifier: str | None
    parts: list[str] = field(default_factory=list)
    filled_parts: set[int] = field(default_factory=set)
    reopening: list[tuple[int, str]] = field(default_factory=list)

    def read_line(self, number: int, line: str, *, structural: bool) -> None:
        """Record a part heading, part content, or reopening-task line."""
        part = _PART.match(line) if structural else None
        if part:
            self.parts.append(part.group("title"))
            return
        if line.strip() and self.parts:
            self.filled_parts.add(len(self.parts) - 1)
        reopening = _REOPENING.match(line) if structural else None
        if reopening:
            self.reopening.append((number, reopening.group("value")))


def read_register(register: Path) -> list[ClosedQuestion]:
    """Read `##` sections in order, ignoring the header and fenced examples."""
    sections: list[ClosedQuestion] = []
    fenced = False
    for number, line in enumerate(register.read_text(encoding="utf-8").splitlines(), 1):
        fence = line.lstrip().startswith("```")
        structural = not (fenced or fence)
        fenced = fenced != fence
        if structural and line.startswith("## "):
            matched = _CLOSED_QUESTION.match(line)
            sections.append(ClosedQuestion(number, matched.group(1) if matched else None))
        elif sections:
            sections[-1].read_line(number, line, structural=structural)
    return sections


def _part_findings(where: str, section: ClosedQuestion) -> list[str]:
    keys = [title.lower() for title in section.parts]
    if [key for key in keys if key in _REQUIRED_KEYS] != list(_REQUIRED_KEYS):
        expected = ", ".join(REQUIRED_PARTS)
        return [f"{where}: needs `###` parts {expected} once each in order; found {section.parts}"]
    return [
        f"{where}: part '{section.parts[index]}' is empty"
        for index, key in enumerate(keys)
        if key in _REQUIRED_KEYS and index not in section.filled_parts
    ]


def _reopening_findings(section: ClosedQuestion, open_ids: set[str]) -> list[str]:
    findings: list[str] = []
    for number, value in section.reopening:
        where = f"{REGISTER_DOC}:{number}"
        if not _TASK_IDS.fullmatch(value):
            findings.append(
                f"{where}: Reopening task must list comma-separated backticked task IDs"
            )
        findings.extend(
            f"{where}: reopening task `{identifier}` is not an open task in {PLAN_DOC}"
            for identifier in re.findall(_TASK_ID, value)
            if identifier not in open_ids
        )
    return findings


def _section_findings(section: ClosedQuestion, open_ids: set[str], seen: set[str]) -> list[str]:
    where = f"{REGISTER_DOC}:{section.line}"
    if section.identifier is None:
        return [f"{where}: section heading must read '## `task-id` -- question'"]
    where = f"{where}: `{section.identifier}`"
    findings: list[str] = []
    if section.identifier in seen:
        findings.append(f"{where}: closed question is listed twice")
    seen.add(section.identifier)
    if section.identifier in open_ids:
        findings.append(
            f"{where}: still an open task in {PLAN_DOC}; close it or remove the section"
        )
    return findings + _part_findings(where, section) + _reopening_findings(section, open_ids)


def register_findings(project_root: Path) -> list[str]:
    """Return every structural or plan disagreement in the closed-research register."""
    missing = [path for path in (PLAN_DOC, REGISTER_DOC) if not (project_root / path).is_file()]
    if missing:
        return [f"missing required document: {path}" for path in missing]
    open_ids = {task.identifier for task in read_tasks(project_root / PLAN_DOC)}
    seen: set[str] = set()
    return [
        finding
        for section in read_register(project_root / REGISTER_DOC)
        for finding in _section_findings(section, open_ids, seen)
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the closed-research register gate."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="check the closed-research register")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else discover_project_root()
    findings = register_findings(root)
    for finding in findings:
        _LOG.error("ERROR: %s", finding)
    _LOG.info("[research-register] %d finding(s)", len(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
