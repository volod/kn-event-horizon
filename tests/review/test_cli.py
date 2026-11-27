"""Golden English and stable JSON at the normal review CLI entry point."""

import json
import logging
from pathlib import Path

import pytest

from kn import cli
from kn.review import operator
from kn.review.authorization import AuthorizationError

FIXTURES = Path(__file__).parent / "fixtures" / "cli.json"


@pytest.mark.parametrize("case", json.loads(FIXTURES.read_text()), ids=lambda case: case["id"])
def test_review_cli_golden(case, monkeypatch, caplog):
    def operation(*args, **options):
        if case.get("error"):
            raise AuthorizationError("fixture")
        return case["result"]

    monkeypatch.setattr(operator, "operation", operation)
    with caplog.at_level(logging.INFO):
        code = cli.main(case["arguments"])
    assert code == case["code"]
    assert caplog.records[-1].message == case["output"]


def test_review_parser_requires_scope_and_refuses_reviewer_injection():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["review", "decide", "--reviewer", "human:fake"])
