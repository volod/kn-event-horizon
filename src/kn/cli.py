"""Command-line entrypoint for the kn operator interface."""

import argparse
import csv
import logging
import os
from collections.abc import Sequence
from pathlib import Path

from jsonschema import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from kn.metadata import project_info
from kn.operations import contract_operation, database_operation, satcom_operation

_LOG = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser independently for tests and future subcommands."""
    parser = argparse.ArgumentParser(prog="kn")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("info", help="show the installed project identity")
    contracts = subcommands.add_parser("contract", help="validate or compile open data contracts")
    contracts.add_argument("action", choices=("lint", "compile"))
    contracts.add_argument("--output", type=Path)
    contracts.add_argument("--check", action="store_true")
    database = subcommands.add_parser("db", help="apply or verify governed schema revisions")
    database.add_argument("action", choices=("upgrade", "verify", "rebuild"))
    space = subcommands.add_parser("space", help="space-domain datasets")
    datasets = space.add_subparsers(dest="dataset", required=True)
    satcom = datasets.add_parser("satcom", help="validate or import the SATCOM example dataset")
    satcom.add_argument("action", choices=("validate", "import"))
    satcom.add_argument("source", type=Path)
    satcom.add_argument("--data-dir", type=Path, default=Path(os.environ.get("DATA_DIR", ".data")))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command and return a process status without exposing connection secrets."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    try:
        _run(args)
    except SQLAlchemyError:
        _LOG.error(
            "database operation failed; check connectivity, permissions, and schema revision"
        )
        return 1
    except ValidationError as error:
        _LOG.error("contract validation failed at %s", ".".join(map(str, error.absolute_path)))
        return 1
    except (ValueError, OSError, UnicodeError, csv.Error) as error:
        _LOG.error("%s", error)
        return 1
    return 0


def _run(args: argparse.Namespace) -> None:
    if args.command == "info":
        info = project_info()
        _LOG.info("%s %s (%s)", info.distribution, info.version, info.package)
    elif args.command == "contract":
        contract_operation(args.action, args.output, args.check)
    elif args.command == "db":
        database_operation(args.action)
    elif args.command == "space":
        satcom_operation(args.action, args.source, args.data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
