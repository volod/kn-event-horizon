"""Strict interface translation; source text uses the separate data module."""

from decimal import Decimal

from babel import Locale
from babel.numbers import format_decimal

from kn.i18n.catalog import compare_catalogs, compile_catalog, load_catalog

DEFAULT_LOCALE = "en"


class Translator:
    """An explicit locale per caller, with no process-global translation state."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        self.locale = locale
        self._messages = load_catalog(locale)
        reference = load_catalog(DEFAULT_LOCALE)
        findings = list(compare_catalogs(reference, self._messages))
        if findings:
            raise ValueError("invalid interface catalog: " + "; ".join(findings))
        self._locale = Locale.parse(locale, sep="-")
        self._gettext = compile_catalog(self._messages, locale)

    def text(self, key: str, **values: object) -> str:
        if key not in self._messages:
            raise ValueError(f"missing interface key: {key}")
        if not isinstance(self._messages[key], str):
            raise ValueError(f"plural interface key needs count: {key}")
        return self._gettext.gettext(key).format(**values)

    def plural_category(self, count: int | Decimal) -> str:
        return str(self._locale.plural_form(count))

    def number(self, value: int | Decimal) -> str:
        pattern = None
        if isinstance(value, Decimal):
            exponent = value.as_tuple().exponent
            if not isinstance(exponent, int):
                raise ValueError("number must be finite")
            if exponent < 0:
                pattern = "#,##0." + "0" * -exponent
        return format_decimal(
            value, format=pattern, locale=self._locale, decimal_quantization=False
        )

    def plural(self, key: str, count: int | Decimal, **values: object) -> str:
        if key not in self._messages:
            raise ValueError(f"missing interface key: {key}")
        if isinstance(self._messages[key], str):
            raise ValueError(f"singular interface key: {key}")
        category = self.plural_category(count)
        return self._gettext.pgettext(category, key).format(count=self.number(count), **values)
