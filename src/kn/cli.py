"""Command-line entrypoint for the kn operator interface."""

import argparse
import csv
import json
import logging
import os
import sys
from collections.abc import Sequence
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import cast

from jsonschema import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from kn.contracts.diagnostics import ContractError
from kn.db.rebuild import RebuildRefused
from kn.i18n import DEFAULT_LOCALE, Translator
from kn.i18n.output import render_result
from kn.i18n.parser import OperatorParser, parse_interface_options
from kn.metadata import project_info
from kn.operations import (
    contract_operation,
    database_operation,
    satcom_operation,
    source_list_operation,
)
from kn.quality.project_root import discover_project_root
from kn.semantic.seeds import import_proposals
from kn.semantic.skos import export_scheme

_LOG = logging.getLogger("kn.operator")


def build_parser(
    translator: Translator | None = None, *, json_output: bool = False
) -> argparse.ArgumentParser:
    """Build the parser using an explicit interface locale."""
    tr = translator or Translator()
    parser = OperatorParser(prog="kn", translator=tr, json_output=json_output)
    parser.add_argument("--locale", help=tr.text("cli.locale_help"))
    parser.add_argument("--json", action="store_true", help=tr.text("cli.json_help"))
    # argparse accepts a callable; its type stub requires a parser class.
    parser_class = cast(
        type[OperatorParser], partial(OperatorParser, translator=tr, json_output=json_output)
    )
    subcommands = parser.add_subparsers(
        dest="command", required=True, title=tr.text("cli.commands"), parser_class=parser_class
    )
    subcommands.add_parser("info", help=tr.text("cli.info_help"))
    contracts = subcommands.add_parser("contract", help=tr.text("cli.contract_help"))
    contracts.add_argument("action", choices=("lint", "compile"))
    contracts.add_argument("source", nargs="?", type=Path, help=tr.text("cli.contract_source_help"))
    contracts.add_argument("--output", type=Path, help=tr.text("cli.output_help"))
    contracts.add_argument("--references", type=Path, help=tr.text("cli.references_help"))
    contracts.add_argument("--check", action="store_true", help=tr.text("cli.check_help"))
    database = subcommands.add_parser("db", help=tr.text("cli.db_help"))
    database.add_argument("action", choices=("upgrade", "verify", "rebuild"))
    source = subcommands.add_parser("source", help=tr.text("cli.catalogue_help"))
    source_actions = source.add_subparsers(
        dest="action", required=True, title=tr.text("cli.commands"), parser_class=parser_class
    )
    source_actions.add_parser("list", help=tr.text("cli.source_list_help"))
    space = subcommands.add_parser("space", help=tr.text("cli.space_help"))
    datasets = space.add_subparsers(
        dest="dataset", required=True, title=tr.text("cli.commands"), parser_class=parser_class
    )
    satcom = datasets.add_parser("satcom", help=tr.text("cli.satcom_help"))
    satcom.add_argument("action", choices=("validate", "import"))
    satcom.add_argument("source", type=Path, help=tr.text("cli.source_help"))
    satcom.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("DATA_DIR", ".data")),
        help=tr.text("cli.data_dir_help"),
    )
    vocabulary = subcommands.add_parser("vocabulary", help=tr.text("cli.vocabulary_help"))
    actions = vocabulary.add_subparsers(
        dest="action", required=True, title=tr.text("cli.commands"), parser_class=parser_class
    )
    proposals = actions.add_parser("import-proposals", help=tr.text("cli.seed_import_help"))
    proposals.add_argument("--check", action="store_true", help=tr.text("cli.seed_check_help"))
    export = actions.add_parser("export", help=tr.text("cli.skos_export_help"))
    export.add_argument(
        "--format", choices=("skos",), required=True, help=tr.text("cli.skos_format_help")
    )
    export.add_argument("--scheme", required=True, help=tr.text("cli.skos_scheme_help"))
    for action in (proposals, export):
        action.add_argument(
            "--data-dir",
            type=Path,
            default=Path(os.environ.get("DATA_DIR", ".data")),
            help=tr.text("cli.data_dir_help"),
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command, keeping JSON keys and error codes independent of locale."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    arguments = list(sys.argv[1:] if argv is None else argv)
    selected, remaining = parse_interface_options(
        arguments, os.environ.get("KN_LOCALE", DEFAULT_LOCALE)
    )
    try:
        translator = Translator(selected.locale)
    except ValueError:
        _report_error(Translator().text("cli.locale_error"), "E_LOCALE", selected.json)
        return 2
    args = build_parser(translator, json_output=selected.json).parse_args(remaining)
    try:
        result = _run(args)
    except SQLAlchemyError:
        _report_error(translator.text("cli.database_error"), "E_DATABASE", selected.json)
        return 1
    except RebuildRefused:
        _report_error(translator.text("cli.rebuild_refused"), "E_INPUT", selected.json)
        return 1
    except ContractError as error:
        diagnostic = error.diagnostic()
        message = translator.text("cli.contract_diagnostic", **diagnostic)
        _report_error(message, "E_CONTRACT", selected.json, diagnostic)
        return 1
    except ValidationError as error:
        path = ".".join(map(str, error.absolute_path))
        _report_error(
            translator.text("cli.validation_error", path=path), "E_CONTRACT", selected.json
        )
        return 1
    except (ValueError, OSError, UnicodeError, csv.Error):
        _report_error(translator.text("cli.input_error"), "E_INPUT", selected.json)
        return 1
    output = (
        json.dumps(result, ensure_ascii=True, sort_keys=True)
        if selected.json
        else render_result(translator, args.command, result)
    )
    _LOG.info("%s", output)
    return 0


def _report_error(
    message: str, code: str, json_output: bool, diagnostic: dict[str, str] | None = None
) -> None:
    error = {"code": code, **(diagnostic or {})}
    _LOG.error("%s", json.dumps({"error": error}, ensure_ascii=True) if json_output else message)


def _run(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "info":
        return asdict(project_info())
    if args.command == "contract":
        return contract_operation(
            args.action, args.output, args.check, args.source, args.references
        )
    if args.command == "db":
        return database_operation(args.action)
    if args.command == "source":
        return source_list_operation()
    if args.command == "vocabulary":
        if args.action == "export":
            return export_scheme(args.scheme, args.data_dir)
        return import_proposals(discover_project_root(), args.data_dir, check=args.check)
    return satcom_operation(args.action, args.source, args.data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
