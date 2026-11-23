"""Check local enablement evidence without running commands or loading source code."""

from pathlib import Path
from xml.etree import ElementTree

from kn.contracts.diagnostics import Location
from kn.contracts.document import MAX_DOCUMENT_BYTES
from kn.quality.project_root import discover_project_root
from kn.sources.config.schema import CrawlerConfigError


def _contained_file(root: Path, relative: str, location: Location) -> Path:
    try:
        path = (root / relative).resolve(strict=True)
        if path.is_relative_to(root) and path.is_file() and path.stat().st_size > 0:
            return path
    except (OSError, RuntimeError):
        pass
    raise CrawlerConfigError(location, "evidenceFile", "reference a nonempty local evidence file")


def _passing_report(report: Path) -> bool:
    try:
        with report.open("rb") as stream:
            content = stream.read(MAX_DOCUMENT_BYTES + 1)
        if len(content) > MAX_DOCUMENT_BYTES:
            return False
        xml = content.decode("utf-8")
        if "\x00" in xml or "<!DOCTYPE" in xml:
            return False
        root = ElementTree.fromstring(xml)
    except (OSError, UnicodeError, ElementTree.ParseError, ValueError):
        return False
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    if root.tag not in {"testsuites", "testsuite"} or not suites:
        return False
    return _passing_suites(root, suites)


def _passing_suites(root: ElementTree.Element, suites: list[ElementTree.Element]) -> bool:
    nonpassing = ("failure", "error", "skipped")
    if any(next(root.iter(tag), None) is not None for tag in nonpassing):
        return False
    for suite in {root, *suites}:
        if any(suite.get(name, "0") != "0" for name in ("failures", "errors", "skipped")):
            return False
        cases = suite.findall(".//testcase")
        if suite.get("tests", str(len(cases))) != str(len(cases)):
            return False
    cases = [case for suite in suites for case in suite.findall("testcase")]
    return bool(cases) and all(case.get("name", "").strip() for case in cases)


def verify_evidence(source: Path, fixtures: list[str], test_report: str) -> None:
    """Use checkout-relative evidence, or file-relative evidence for a standalone profile."""
    directory = source.absolute().parent.resolve()
    try:
        root = discover_project_root(directory)
    except FileNotFoundError:
        root = directory
    for index, fixture in enumerate(fixtures):
        _contained_file(root, fixture, ("verification", "fixtures", index))
    location = ("verification", "test_report")
    report = _contained_file(root, test_report, location)
    if not _passing_report(report):
        raise CrawlerConfigError(location, "testReport", "reference a passing JUnit XML report")
