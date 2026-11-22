"""Data display never treats a missing translation as a missing interface message."""

import itertools
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from kn.i18n import Translator
from kn.i18n.data import SourceText, TextVariant, select_text
from tests.e2e.support import FIXTURES, LOCALES, write_json


@pytest.mark.parametrize("locale", LOCALES)
def test_source_text_acceptance(locale: str, e2e_artifacts: Path) -> None:
    records = json.loads((FIXTURES / "source-text.json").read_text("ascii"))
    evidence = []
    for record in records:
        source = SourceText(
            TextVariant(**record["original"]),
            tuple(TextVariant(**value) for value in record["translations"]),
        )
        before = asdict(source)
        selected = select_text(source, locale)
        expected = record["expected"][locale]
        variant = (
            source.original
            if expected == "original"
            else next(value for value in source.translations if value.language == expected)
        )
        assert selected.variant is variant, record["id"]
        assert selected.is_original == (expected == "original")
        assert selected.fallback == (variant.language.lower() != locale)
        assert asdict(source) == before
        # Round trips retain whitespace, combining characters, tags, and all provenance.
        restored = json.loads(json.dumps(before, ensure_ascii=True))
        assert restored["original"] == record["original"]
        assert restored["translations"] == record["translations"]
        evidence.append({"id": record["id"], "source": before, "selected": asdict(selected)})
    write_json(e2e_artifacts / locale / "data-selection.json", evidence)


@pytest.mark.parametrize("original_language", ["en", "uk", "ru", "zh", "ar", "und", "en-US"])
@pytest.mark.parametrize("locale", LOCALES)
def test_all_translation_subsets_and_orders(original_language: str, locale: str) -> None:
    original = TextVariant(
        "\u539f\u6587\r\n e\u0301 \u0442\u0435\u043a\u0441\u0442 ", original_language, "raw:1"
    )
    available = [
        TextVariant(f"Translated into {language}", language, f"review:{language}")
        for language in LOCALES
        if language != original_language
    ]
    for size in range(len(available) + 1):
        for translations in itertools.permutations(available, size):
            data = SourceText(original, translations)
            selected = select_text(data, locale)
            languages = {item.language: item for item in (original, *translations)}
            expected = languages.get(locale) or languages.get("en") or original
            assert selected.variant is expected
            assert data.original is original
            assert data.translations == translations
            assert selected.is_original == (expected is original)
            assert selected.fallback == (expected.language != locale)
            assert select_text(data, locale.upper()) == selected


def test_missing_data_translation_does_not_change_interface_language() -> None:
    original = TextVariant("\u539f\u6587", "zh", "raw:untranslated")
    selected = select_text(SourceText(original), "uk")
    interface = Translator("uk")
    assert selected.variant is original and selected.fallback
    assert interface.text("cli.help") != Translator("en").text("cli.help")
    with pytest.raises(ValueError, match="missing interface key"):
        interface.text("source.untranslated")


def test_later_translation_does_not_replace_the_durable_original() -> None:
    original = TextVariant(
        "\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a", "ru", "raw:doc/rev:1"
    )
    source = SourceText(original)
    english = TextVariant("Source", "en", "human:review/2")
    translated = SourceText(source.original, (english,))
    assert select_text(source, "uk").variant is original
    assert select_text(translated, "uk").variant is english
    assert source.original is translated.original is original
    assert source.translations == ()
