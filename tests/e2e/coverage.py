"""Explicit release blockers; a successful subset must never imply full acceptance."""

from pathlib import Path

from tests.e2e.support import LOCALES, write_json

BLOCKERS = {
    "space_dashboards_and_map": "space-dashboard-bundles",
    "gdelt_dashboards": "gdelt-watch-dashboard",
    "microelectronics_dashboards": "microelectronics-comparison-dashboards",
    "browser_screenshots": "dashboards-as-code",
    "dates_units_and_missing_value_labels": "dashboards-as-code",
}


def release_report(test_exit_code: int) -> dict[str, object]:
    return {
        "locales": LOCALES,
        "test_exit_code": test_exit_code,
        "release_ready": test_exit_code == 0 and not BLOCKERS,
        "release_blockers": BLOCKERS,
        "available_scope": ["english_cli", "multilingual_text_selection", "catalogs_and_plurals"],
        "not_exercised": ["database_success_paths", "live_crawlers", "browser_rendering"],
    }


def save_report(
    directory: Path, test_exit_code: int, selected_tests: list[str], passed_tests: list[str]
) -> dict[str, object]:
    report = release_report(test_exit_code)
    report.update(selected_tests=selected_tests, passed_tests=passed_tests)
    write_json(directory / "manifest.json", report)
    return report
