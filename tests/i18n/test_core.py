"""Interface catalogs and data translations follow independent contracts."""

from decimal import Decimal

import pytest

from kn.i18n import Translator
from kn.i18n.data import SourceText, TextVariant, select_text


def test_interface_keys_are_strict_and_locales_do_not_leak() -> None:
    en, uk = Translator("en"), Translator("uk")
    assert en.text("cli.info", distribution="kn", version="1", package="kn") == "Project: kn 1 (kn)"
    assert uk.text("cli.info", distribution="kn", version="1", package="kn").startswith(
        "\u041f\u0440\u043e\u0454\u043a\u0442:"
    )
    with pytest.raises(ValueError, match="missing interface key"):
        uk.text("absent")
    with pytest.raises(ValueError, match="unsupported interface locale"):
        Translator("ru")
    assert en.text("cli.help") == "show this help message and exit"


@pytest.mark.parametrize(
    ("count", "category"),
    [
        (0, "many"),
        (1, "one"),
        (2, "few"),
        (5, "many"),
        (11, "many"),
        (12, "many"),
        (21, "one"),
        (22, "few"),
        (Decimal("1.5"), "other"),
        (Decimal("1.0"), "other"),
        (-2, "few"),
    ],
)
def test_ukrainian_cldr_categories(count: int | Decimal, category: str) -> None:
    assert Translator("uk").plural_category(count) == category


def test_numbers_and_plural_messages_preserve_fraction_precision() -> None:
    en, uk = Translator("en"), Translator("uk")
    assert en.number(Decimal("12345.67891")) == "12,345.67891"
    assert uk.number(Decimal("12345.67891")) == "12\u00a0345,67891"
    assert en.plural("cli.tables", 1) == "1 table"
    assert en.plural("cli.tables", 2) == "2 tables"
    assert uk.plural("cli.tables", 2) == "2 \u0442\u0430\u0431\u043b\u0438\u0446\u0456"
    assert (
        uk.plural("cli.tables", Decimal("1.5")) == "1,5 \u0442\u0430\u0431\u043b\u0438\u0446\u0456"
    )


@pytest.mark.parametrize("language", ["ru", "zh-Hans", "uk", "en", "und"])
@pytest.mark.parametrize("requested", ["en", "uk"])
def test_untranslated_originals_survive_every_interface_locale(
    language: str, requested: str
) -> None:
    original = TextVariant("\u539f\u6587\n \u0442\u0435\u043a\u0441\u0442 ", language, "raw:doc-1")
    data = SourceText(original)
    selected = select_text(data, requested)
    assert selected.variant is original
    assert selected.is_original
    assert selected.fallback == (language != requested)
    assert data.original.text == "\u539f\u6587\n \u0442\u0435\u043a\u0441\u0442 "


def test_requested_then_english_then_original_with_provenance() -> None:
    original = TextVariant("\u539f\u6587", "zh", "source:1/rev:2")
    english = TextVariant("Original", "en", "human:review-3")
    ukrainian = TextVariant(
        "\u041e\u0440\u0438\u0433\u0456\u043d\u0430\u043b", "uk", "model:4/prompt:5"
    )
    data = SourceText(original, (english, ukrainian))
    assert select_text(data, "uk").variant is ukrainian
    assert select_text(SourceText(original, (english,)), "uk").variant is english
    assert select_text(SourceText(original, (ukrainian,)), "en").variant is original
    assert data.original is original and data.translations == (english, ukrainian)


def test_original_in_requested_language_precedes_english_translation() -> None:
    original = TextVariant("\u0422\u0435\u043a\u0441\u0442", "uk", "raw:1")
    english = TextVariant("Text", "en", "human:2")
    assert select_text(SourceText(original, (english,)), "uk").variant is original
    assert select_text(SourceText(english), "uk").fallback
    tagged = TextVariant("Text", "EN-us", "raw:2")
    assert not select_text(SourceText(tagged), "en-US").fallback


def test_ambiguous_translations_and_missing_provenance_are_rejected() -> None:
    original = TextVariant("\u539f\u6587", "zh", "source:1")
    with pytest.raises(ValueError, match="duplicate language"):
        SourceText(original, (TextVariant("a", "en", "human:1"), TextVariant("b", "EN", "human:2")))
    with pytest.raises(ValueError, match="provenance"):
        TextVariant("text", "uk", "")
    with pytest.raises(ValueError, match="language tag"):
        TextVariant("text", "not a tag", "raw:1")


def test_visible_fraction_digits_agree_with_the_plural_category() -> None:
    assert Translator("uk").plural("cli.tables", Decimal("1.0")) == (
        "1,0 \u0442\u0430\u0431\u043b\u0438\u0446\u0456"
    )
    assert Translator("en").plural("cli.tables", Decimal("1.0")) == "1.0 tables"


def test_message_kind_must_match_the_rendering_method() -> None:
    translator = Translator()
    with pytest.raises(ValueError, match="needs count"):
        translator.text("cli.tables")
    with pytest.raises(ValueError, match="singular interface key"):
        translator.plural("cli.info", 2)
    with pytest.raises(ValueError, match="missing interface key"):
        translator.plural("absent", 2)


def test_blank_translations_do_not_suppress_the_original() -> None:
    original = TextVariant("\u539f\u6587", "zh", "raw:1")
    with pytest.raises(ValueError, match="blank"):
        SourceText(original, (TextVariant(" ", "en", "human:1"),))
    assert select_text(SourceText(original), "uk").variant is original
