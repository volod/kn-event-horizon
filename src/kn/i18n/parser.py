"""Localized argparse boundary without mutating argparse's process-global gettext."""

import argparse
import json
from collections.abc import Sequence
from functools import partial
from typing import Any, Never

from kn.i18n import Translator


def parse_interface_options(
    arguments: Sequence[str], default_locale: str
) -> tuple[argparse.Namespace, list[str]]:
    """Keep early argument errors in the last selected locale, including the environment."""
    parser = OperatorParser(
        prog="kn", include_help=False, json_output="--json" in arguments, exit_on_error=False
    )
    parser.add_argument("--locale", default=default_locale)
    parser.add_argument("--json", action="store_true")
    selected = argparse.Namespace(locale=default_locale)
    try:
        return parser.parse_known_args(arguments, namespace=selected)
    except argparse.ArgumentError:
        # argparse populates the namespace before a later malformed option is encountered.
        # An invalid locale has no catalog; its diagnostic uses the default interface.
        try:
            parser.translator = Translator(selected.locale)
        except ValueError:
            parser.translator = Translator()
        parser.formatter_class = partial(OperatorHelpFormatter, translator=parser.translator)
        parser.error("")


class OperatorHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog: str, translator: Translator) -> None:
        super().__init__(prog)
        self.translator = translator

    def add_usage(
        self,
        usage: str | None,
        actions: Any,
        groups: Any,
        prefix: str | None = None,
    ) -> None:
        super().add_usage(
            usage, actions, groups, self.translator.text("cli.usage") if prefix is None else prefix
        )


class OperatorParser(argparse.ArgumentParser):
    def __init__(
        self,
        *args: Any,
        translator: Translator | None = None,
        json_output: bool = False,
        include_help: bool = True,
        **kwargs: Any,
    ) -> None:
        self.translator = translator or Translator()
        self.json_output = json_output
        kwargs["add_help"] = False
        kwargs["allow_abbrev"] = False
        kwargs["formatter_class"] = partial(OperatorHelpFormatter, translator=self.translator)
        super().__init__(*args, **kwargs)
        self._positionals.title = self.translator.text("cli.arguments")
        self._optionals.title = self.translator.text("cli.options")
        if include_help:
            self.add_argument("-h", "--help", action="help", help=self.translator.text("cli.help"))

    def error(self, message: str) -> Never:
        # argparse's free-form English errors are not a stable localization interface.
        # Show localized usage and a stable code; never interpolate raw argument values.
        if self.json_output:
            self.exit(2, json.dumps({"error": {"code": "E_ARGUMENTS"}}) + "\n")
        self.print_usage()
        self.exit(2, self.translator.text("cli.arguments_error", prog=self.prog) + "\n")
