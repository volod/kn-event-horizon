"""Planted catalog and interface-boundary defects must fail the CI check."""

import json
from pathlib import Path

import pytest

from kn.i18n.catalog import read_catalog
from kn.quality.catalogs import check_catalogs, main


def project(tmp_path: Path) -> Path:
    for locale in ("en", "uk"):
        folder = tmp_path / "locales" / locale
        folder.mkdir(parents=True)
        (folder / "messages.json").write_text('{"test.key": "Text {name}"}', encoding="ascii")
    source = tmp_path / "src" / "kn"
    source.mkdir(parents=True)
    (source / "cli.py").write_text('tr.text("test.key", name="value")\n', encoding="ascii")
    return tmp_path


@pytest.mark.parametrize("locale", ["en", "uk"])
def test_missing_key_fails_in_either_direction(tmp_path: Path, locale: str) -> None:
    root = project(tmp_path)
    path = root / "locales" / locale / "messages.json"
    path.write_text('{"test.other": "Other"}', encoding="ascii")
    assert any("key:" in finding for finding in check_catalogs(root))
    assert main(["--root", str(root)]) == 1


def test_matching_catalogs_and_used_keys_pass(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert check_catalogs(root) == []
    assert main(["--root", str(root)]) == 0


@pytest.mark.parametrize(
    ("content", "finding"),
    [
        ('{"test.key": "Text {wrong}"}', "placeholder mismatch"),
        ('{"test.key": ""}', "empty or invalid translation"),
        ('{"test.key": "a", "test.key": "b"}', "duplicate catalog key"),
        ('{"test.key": {"one": "{count}", "other": "{count}"}}', "invalid plural"),
        ('{"test.key": "Text {name}", "test.unused": "Unused"}', "unused key"),
    ],
)
def test_invalid_catalog_variants(tmp_path: Path, content: str, finding: str) -> None:
    root = project(tmp_path)
    (root / "locales" / "uk" / "messages.json").write_text(content, encoding="ascii")
    if finding == "unused key":
        (root / "locales" / "en" / "messages.json").write_text(content, encoding="ascii")
    assert any(finding in item for item in check_catalogs(root))


@pytest.mark.parametrize(
    "source",
    [
        '_LOG.info("Untranslated output")',
        '_LOG.error("%s", "Untranslated error")',
        'parser.add_argument("--x", help="Untranslated help")',
        'argparse.ArgumentParser(description="Untranslated description")',
        'parser.exit(2, "Untranslated error")',
        'print(f"Untranslated {value}")',
    ],
)
def test_user_facing_literals_fail(tmp_path: Path, source: str) -> None:
    root = project(tmp_path)
    (root / "src" / "kn" / "cli.py").write_text(source, encoding="ascii")
    assert any("user-facing literal" in finding for finding in check_catalogs(root))


def test_dynamic_missing_and_mixed_kind_keys_fail(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "src" / "kn" / "cli.py").write_text(
        'tr.text(key)\ntr.text("test.missing")\ntr.plural("test.key", 2)\n', encoding="ascii"
    )
    findings = check_catalogs(root)
    assert any("must be a literal" in finding for finding in findings)
    assert any("referenced key missing" in finding for finding in findings)
    assert any("message kind mismatch" in finding for finding in findings)


@pytest.mark.parametrize("text", ["{name.attr}", "{0}", "{name:10}", "{name!r}", "{"])
def test_unsafe_or_malformed_format_fields_fail(text: str) -> None:
    with pytest.raises(ValueError):
        read_catalog(json.dumps({"test.key": text}), "en")
