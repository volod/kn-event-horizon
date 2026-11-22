"""ASCII catalog sources compiled by Babel into strict GNU gettext catalogs."""

import json
import re
from collections.abc import Iterable
from gettext import GNUTranslations
from importlib.resources import files
from io import BytesIO
from string import Formatter

from babel import Locale
from babel.core import UnknownLocaleError
from babel.messages.catalog import Catalog
from babel.messages.mofile import write_mo

CatalogValue = str | dict[str, str]
_KEY = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+")
_FIELD = re.compile(r"[a-z][a-z0-9_]*")


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate catalog key: {key}")
        result[key] = value
    return result


def placeholders(text: str) -> set[str]:
    """Only named fields are allowed; attribute access and format specs are refused."""
    result = set()
    for _, field, spec, conversion in Formatter().parse(text):
        if field is not None:
            if not _FIELD.fullmatch(field) or spec or conversion:
                raise ValueError(f"invalid catalog placeholder: {field}")
            result.add(field)
    return result


def categories(locale: str) -> set[str]:
    return set(Locale.parse(locale, sep="-").plural_form.tags) | {"other"}


def read_catalog(source: str, locale: str) -> dict[str, CatalogValue]:
    """Validate shape, CLDR categories, nonempty translations, and interpolation fields."""
    raw = json.loads(source, object_pairs_hook=_unique_pairs)
    if not isinstance(raw, dict) or not raw:
        raise ValueError("catalog must be a nonempty object")
    result: dict[str, CatalogValue] = {}
    for key, value in raw.items():
        if not _KEY.fullmatch(key):
            raise ValueError(f"invalid catalog key: {key}")
        result[key] = _validate_value(key, value, locale)
    return result


def _validate_value(key: str, value: object, locale: str) -> CatalogValue:
    if isinstance(value, str):
        variants = [value]
    elif isinstance(value, dict) and set(value) == categories(locale):
        variants = list(value.values())
    else:
        raise ValueError(f"invalid plural categories or message: {key}")
    fields = []
    for text in variants:
        if not isinstance(text, str) or not text.strip() or "\x00" in text:
            raise ValueError(f"empty or invalid translation: {key}")
        fields.append(placeholders(text))
    if any(field != fields[0] for field in fields):
        raise ValueError(f"plural placeholder mismatch: {key}")
    if isinstance(value, dict):
        if "count" not in fields[0]:
            raise ValueError(f"plural message needs count: {key}")
        return {category: str(text) for category, text in value.items()}
    assert isinstance(value, str)
    return value


def catalog_fields(value: CatalogValue) -> set[str]:
    return placeholders(value if isinstance(value, str) else value["other"])


def compare_catalogs(
    reference: dict[str, CatalogValue], candidate: dict[str, CatalogValue]
) -> Iterable[str]:
    for key in sorted(reference.keys() - candidate.keys()):
        yield f"missing key: {key}"
    for key in sorted(candidate.keys() - reference.keys()):
        yield f"extra key: {key}"
    for key in sorted(reference.keys() & candidate.keys()):
        if isinstance(reference[key], str) != isinstance(candidate[key], str):
            yield f"message kind mismatch: {key}"
        if catalog_fields(reference[key]) != catalog_fields(candidate[key]):
            yield f"placeholder mismatch: {key}"


def load_catalog(locale: str) -> dict[str, CatalogValue]:
    # Validate before joining an operator-provided locale to a resource path.
    try:
        Locale.parse(locale, sep="-")
    except (ValueError, UnknownLocaleError) as error:
        raise ValueError(f"unsupported interface locale: {locale}") from error
    resource = files("kn.i18n.locales").joinpath(locale, "messages.json")
    if not resource.is_file():
        raise ValueError(f"unsupported interface locale: {locale}")
    return read_catalog(resource.read_text(encoding="ascii"), locale)


def compile_catalog(messages: dict[str, CatalogValue], locale: str) -> GNUTranslations:
    """Use gettext contexts for CLDR categories, including fractional 'other' forms."""
    catalog = Catalog(locale=locale, charset="utf-8", fuzzy=False)
    for key, value in messages.items():
        if isinstance(value, str):
            catalog.add(key, value)
        else:
            for category, text in value.items():
                catalog.add(key, text, context=category)
    output = BytesIO()
    write_mo(output, catalog)
    output.seek(0)
    return GNUTranslations(output)
