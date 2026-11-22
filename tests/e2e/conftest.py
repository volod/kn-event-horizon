"""Optional persistent artifacts and a fail-closed full-release gate."""

from pathlib import Path

import pytest

from tests.e2e.coverage import release_report, save_report

PASSED_TESTS = pytest.StashKey[set[str]]()


class CaseResults:
    def __init__(self, passed: set[str]) -> None:
        self.passed = passed

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when == "call" and report.passed:
            self.passed.add(report.nodeid)


def pytest_configure(config: pytest.Config) -> None:
    config.stash[PASSED_TESTS] = set()
    # Register globally: this conftest's own per-test hooks only see tests/e2e descendants.
    config.pluginmanager.register(CaseResults(config.stash[PASSED_TESTS]), "bilingual-results")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--e2e-artifacts", type=Path, help="Write bilingual evidence into this directory"
    )
    parser.addoption(
        "--require-bilingual-release",
        action="store_true",
        help="Fail when any full-release operator path lacks acceptance evidence",
    )


@pytest.fixture(scope="session")
def e2e_artifacts(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return request.config.getoption("--e2e-artifacts") or tmp_path_factory.mktemp("bilingual")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    directory = session.config.getoption("--e2e-artifacts")
    report = release_report(int(exitstatus))
    if directory is not None:
        save_report(
            directory,
            int(exitstatus),
            sorted(item.nodeid for item in session.items),
            sorted(session.config.stash[PASSED_TESTS]),
        )
    if session.config.getoption("--require-bilingual-release") and not report["release_ready"]:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    directory = terminalreporter.config.getoption("--e2e-artifacts")
    if directory is not None:
        terminalreporter.write_sep("-", f"Bilingual evidence: {directory}")
        if not release_report(0)["release_ready"]:
            terminalreporter.write_line(
                "Full release acceptance remains blocked; see manifest.json."
            )
