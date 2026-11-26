"""English argparse presentation and stable argument errors."""

import argparse
import json
from collections.abc import Sequence
from functools import partial
from typing import Any, Never

from kn.i18n import Translator


def parse_json_option(arguments: Sequence[str], translator: Translator) -> tuple[bool, list[str]]:
    """Read the global JSON flag before parsing commands so errors use the requested format."""
    parser = OperatorParser(
        prog="kn",
        translator=translator,
        include_help=False,
        json_output="--json" in arguments,
        exit_on_error=False,
    )
    parser.add_argument("--json", action="store_true")
    try:
        selected, remaining = parser.parse_known_args(arguments)
    except argparse.ArgumentError:
        parser.error("")
    return selected.json, remaining


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
        # Keep the diagnostic stable and avoid including raw argument values.
        if self.json_output:
            self.exit(2, json.dumps({"error": {"code": "E_ARGUMENTS"}}) + "\n")
        self.print_usage()
        self.exit(2, self.translator.text("cli.arguments_error", prog=self.prog) + "\n")
