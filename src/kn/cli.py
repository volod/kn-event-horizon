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
from typing import Any, cast

from jsonschema import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from kn.archive.config import INDEX_VARIABLE, ROOT_VARIABLE
from kn.archive.model import ArchiveError
from kn.contracts.diagnostics import ContractError
from kn.db.rebuild import RebuildRefused
from kn.evidence.ranking import DEFAULT_AUDIENCE, Audience
from kn.i18n import Translator
from kn.i18n.output import render_result
from kn.i18n.parser import OperatorParser, parse_json_option
from kn.identity import operator
from kn.identity.journal import Journal
from kn.identity.lifecycle_reviews import Change, Reclassification, ReviewDetails
from kn.identity.model import Assignment, Merge, Restore, Retire, SourceKey, Split
from kn.identity.queries import inspect
from kn.metadata import project_info
from kn.operations import (
    contract_operation,
    database_operation,
    lineage_operation,
    raw_reindex_operation,
    raw_verify_operation,
    satcom_operation,
    source_list_operation,
)
from kn.quality.project_root import discover_project_root
from kn.review import operator as review_operator
from kn.review.model import Target
from kn.review.queue_model import domain_name
from kn.semantic.seeds import import_proposals
from kn.semantic.skos import export_scheme
from kn.sources.config import source_validate_operation
from kn.sources.config.schema import CrawlerConfigError

_LOG = logging.getLogger("kn.operator")


def build_parser(
    translator: Translator | None = None, *, json_output: bool = False
) -> argparse.ArgumentParser:
    """Build the English operator parser."""
    tr = translator or Translator()
    parser = OperatorParser(prog="kn", translator=tr, json_output=json_output)
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
    identity = subcommands.add_parser("identity", help=tr.text("cli.identity_help"))
    _identity_arguments(identity, parser_class, tr)
    review = subcommands.add_parser("review", help=tr.text("cli.review_help"))
    _review_arguments(review, parser_class, tr)
    lineage = subcommands.add_parser("lineage", help=tr.text("cli.lineage_help"))
    lineage.add_argument(
        "reference", metavar="REFERENCE", help=tr.text("cli.lineage_reference_help")
    )
    lineage.add_argument("--field", metavar="FIELD_ID", help=tr.text("cli.lineage_field_help"))
    lineage.add_argument(
        "--audience", default=DEFAULT_AUDIENCE, help=tr.text("cli.lineage_audience_help")
    )
    lineage.add_argument(
        "--permit", action="append", metavar="RIGHTS", help=tr.text("cli.lineage_permit_help")
    )
    lineage.add_argument("--data-dir", type=Path, help=tr.text("cli.data_dir_help"))
    source = subcommands.add_parser("source", help=tr.text("cli.catalogue_help"))
    source_actions = source.add_subparsers(
        dest="action", required=True, title=tr.text("cli.commands"), parser_class=parser_class
    )
    source_actions.add_parser("list", help=tr.text("cli.source_list_help"))
    validate_source = source_actions.add_parser(
        "validate", help=tr.text("cli.source_validate_help")
    )
    validate_source.add_argument("source", type=Path, help=tr.text("cli.source_config_help"))
    raw = subcommands.add_parser("raw", help=tr.text("cli.raw_help"))
    raw_actions = raw.add_subparsers(dest="action", required=True, parser_class=parser_class)
    raw_actions.add_parser("verify", help=tr.text("cli.raw_verify_help"))
    reindex = raw_actions.add_parser("reindex", help=tr.text("cli.raw_reindex_help"))
    reindex.add_argument("--domain", help=tr.text("cli.raw_domain_help"))
    reindex.add_argument("--source", help=tr.text("cli.raw_source_help"))
    reindex.add_argument("--since", help=tr.text("cli.raw_since_help"))
    reindex.add_argument("--before", help=tr.text("cli.raw_before_help"))
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


def _identity_arguments(
    parser: OperatorParser, parser_class: type[OperatorParser], tr: Translator
) -> None:
    parser.add_argument("--data-dir", type=Path, help=tr.text("cli.data_dir_help"))
    actions = parser.add_subparsers(
        dest="action", required=True, title=tr.text("cli.commands"), parser_class=parser_class
    )
    descriptions = {
        "show": tr.text("cli.identity_show_help"),
        "resolve": tr.text("cli.identity_resolve_help"),
        "history": tr.text("cli.identity_history_help"),
        "merge": tr.text("cli.identity_merge_help"),
        "split": tr.text("cli.identity_split_help"),
        "retire": tr.text("cli.identity_retire_help"),
        "restore": tr.text("cli.identity_restore_help"),
        "reclassify": tr.text("cli.identity_reclassify_help"),
    }
    for action, description in descriptions.items():
        command = actions.add_parser(action, help=description, description=description)
        command.add_argument("kn_id", metavar="KN_ID", help=tr.text("cli.identity_id_help"))
        if action in {"show", "resolve", "history"}:
            continue
        command.add_argument(
            "--request-id", required=True, help=tr.text("cli.identity_request_help")
        )
        command.add_argument(
            "--performed-at", required=True, help=tr.text("cli.identity_time_help")
        )
        command.add_argument("--reason", required=True, help=tr.text("cli.identity_reason_help"))
        command.add_argument(
            "--evidence", required=True, help=tr.text("cli.identity_evidence_help")
        )
        if action == "merge":
            command.add_argument("survivor", help=tr.text("cli.identity_survivor_help"))
        elif action == "split":
            command.add_argument(
                "successors", nargs="+", help=tr.text("cli.identity_successors_help")
            )
            command.add_argument(
                "--assign", action="append", default=[], help=tr.text("cli.identity_assign_help")
            )
        elif action == "reclassify":
            command.add_argument("entity_class", help=tr.text("cli.identity_class_help"))
            command.add_argument(
                "--anchor-source", required=True, help=tr.text("cli.identity_anchor_source_help")
            )
            command.add_argument(
                "--anchor-key", required=True, help=tr.text("cli.identity_anchor_key_help")
            )


def _review_arguments(
    parser: OperatorParser, parser_class: type[OperatorParser], tr: Translator
) -> None:
    actions = parser.add_subparsers(dest="action", required=True, parser_class=parser_class)
    for name in ("list", "decide", "replay"):
        command = actions.add_parser(name)
        command.add_argument("--data-dir", type=Path)
        command.add_argument("--domain", type=domain_name, default="core")
        if name == "list":
            command.add_argument("--overrides", action="store_true")
            command.add_argument(
                "--target",
                type=Path,
                help=tr.text("cli.review_target_help"),
            )
        if name == "decide":
            targets = command.add_mutually_exclusive_group(required=True)
            targets.add_argument("--item", dest="item_id")
            targets.add_argument("--target", type=Path)
            command.add_argument("--select", dest="selected")
            command.add_argument(
                "--outcome", choices=("accept", "reject", "revoke", "supersede"), required=True
            )
            for option in ("request-id", "performed-at", "reason", "evidence"):
                command.add_argument("--" + option, required=True)
            command.add_argument("--predecessor", action="append", default=[])


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command with English text or machine-readable JSON."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    arguments = list(sys.argv[1:] if argv is None else argv)
    translator = Translator()
    json_output, remaining = parse_json_option(arguments, translator)
    args = build_parser(translator, json_output=json_output).parse_args(remaining)
    try:
        result = _run(args, translator)
    except SQLAlchemyError:
        _report_error(translator.text("cli.database_error"), "E_DATABASE", json_output)
        return 1
    except RebuildRefused:
        _report_error(translator.text("cli.rebuild_refused"), "E_INPUT", json_output)
        return 1
    except ArchiveError as error:
        _report_archive_error(translator, error, json_output)
        return 1
    except operator.IdentityAuthorizationError:
        code = "E_REVIEW_AUTH" if args.command == "review" else "E_IDENTITY_AUTH"
        message = (
            translator.text("cli.review_auth_error")
            if args.command == "review"
            else translator.text("cli.identity_auth_error")
        )
        _report_error(message, code, json_output)
        return 1
    except CrawlerConfigError as error:
        diagnostic = error.diagnostic()
        message = translator.text("cli.source_config_diagnostic", **diagnostic)
        _report_error(message, "E_SOURCE_CONFIG", json_output, diagnostic)
        return 1
    except ContractError as error:
        diagnostic = error.diagnostic()
        message = translator.text("cli.contract_diagnostic", **diagnostic)
        _report_error(message, "E_CONTRACT", json_output, diagnostic)
        return 1
    except ValidationError as error:
        path = ".".join(map(str, error.absolute_path))
        _report_error(translator.text("cli.validation_error", path=path), "E_CONTRACT", json_output)
        return 1
    except (ValueError, OSError, UnicodeError, csv.Error):
        _report_error(translator.text("cli.input_error"), "E_INPUT", json_output)
        return 1
    output = (
        json.dumps(result, ensure_ascii=True, sort_keys=True)
        if json_output
        else render_result(translator, args.command, result)
    )
    _LOG.info("%s", output)
    return 0


def _report_error(
    message: str, code: str, json_output: bool, diagnostic: dict[str, str] | None = None
) -> None:
    error = {"code": code, **(diagnostic or {})}
    _LOG.error("%s", json.dumps({"error": error}, ensure_ascii=True) if json_output else message)


def _report_archive_error(translator: Translator, error: ArchiveError, json_output: bool) -> None:
    details = {"reason": error.code}
    roots = {"archive_root_required": ROOT_VARIABLE, "index_root_required": INDEX_VARIABLE}
    if error.code in roots:
        details["variable"] = roots[error.code]
        message = translator.text("cli.raw_root_required", variable=details["variable"])
    else:
        message = translator.text("cli.raw_error", reason=error.code)
    _report_error(message, "E_RAW_ARCHIVE", json_output, details)


def _run(args: argparse.Namespace, translator: Translator) -> dict[str, object]:
    if args.command == "review":
        return _review(args, translator)
    if args.command == "identity":
        return _identity(args, translator)
    if args.command == "lineage":
        rights = None if args.permit is None else frozenset(args.permit)
        audience = Audience(name=args.audience, rights=rights)
        return lineage_operation(_journal(args), args.reference, args.field, audience)
    if args.command == "info":
        return asdict(project_info())
    if args.command == "contract":
        return contract_operation(
            args.action, args.output, args.check, args.source, args.references
        )
    if args.command == "db":
        return database_operation(args.action)
    if args.command == "raw":
        return _run_raw(args)
    if args.command == "source":
        if args.action == "validate":
            return source_validate_operation(args.source)
        return source_list_operation()
    if args.command == "vocabulary":
        if args.action == "export":
            return export_scheme(args.scheme, args.data_dir)
        return import_proposals(discover_project_root(), args.data_dir, check=args.check)
    return satcom_operation(args.action, args.source, args.data_dir)


def _run_raw(args: argparse.Namespace) -> dict[str, object]:
    if args.action == "reindex":
        return raw_reindex_operation(args.domain, args.source, args.since, args.before)
    return raw_verify_operation()


def _review(args: argparse.Namespace, translator: Translator) -> dict[str, object]:
    directory = _journal(args).data_dir
    options: dict[str, Any] = {}
    if args.action == "list":
        options["overrides"] = args.overrides
        options["query"] = args.target.read_text(encoding="ascii") if args.target else None
    if args.action == "decide":
        if args.selected is not None and args.item_id is None:
            raise ValueError("selection requires a queue item")
        options.update(
            item_id=args.item_id,
            selected=args.selected,
            target=Target.model_validate_json(args.target.read_text(encoding="ascii"))
            if args.target
            else None,
            details={
                "request_id": args.request_id,
                "outcome": args.outcome,
                "performed_at": args.performed_at,
                "reason": args.reason,
                "evidence": args.evidence,
                "predecessors": args.predecessor,
            },
        )
    return review_operator.operation(translator, directory, args.domain, args.action, **options)


def _journal(args: argparse.Namespace) -> Journal:
    directory = args.data_dir or Path(os.environ.get("DATA_DIR", ".data"))
    if not directory.is_absolute():
        directory = discover_project_root() / directory
    return Journal(directory)


def _identity(args: argparse.Namespace, translator: Translator) -> dict[str, object]:
    journal = _journal(args)
    if args.action in {"show", "resolve", "history"}:
        return inspect(journal, args.action, args.kn_id)
    details = ReviewDetails.model_validate(
        {
            "request_id": args.request_id,
            "performed_at": args.performed_at,
            "reason": args.reason,
            "evidence": args.evidence,
        }
    )
    return operator.apply_change(translator, journal, _identity_change(args), details)


def _identity_change(args: argparse.Namespace) -> Change:
    if args.action == "merge":
        return Merge(kn_id=args.kn_id, survivor=args.survivor)
    if args.action == "split":
        assignments = []
        for assignment in args.assign:
            item, _, successor = assignment.partition("=")
            assignments.append(Assignment(item_id=item, successor=successor))
        return Split(
            kn_id=args.kn_id, successors=tuple(args.successors), assignments=tuple(assignments)
        )
    if args.action == "reclassify":
        return Reclassification(
            kn_id=args.kn_id,
            entity_class=args.entity_class,
            anchor=SourceKey(source=args.anchor_source, key=args.anchor_key),
        )
    if args.action == "retire":
        return Retire(kn_id=args.kn_id)
    return Restore(kn_id=args.kn_id)


if __name__ == "__main__":
    raise SystemExit(main())
