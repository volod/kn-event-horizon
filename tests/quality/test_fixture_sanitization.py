import logging
from pathlib import Path

import pytest

from kn.quality.fixture_sanitization import main


def _fixture(root: Path, relative: str, contents: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)
    return path


@pytest.mark.parametrize(
    ("filename", "content", "rule"),
    [
        ("request.http", b"Authorization: Bearer planted-credential\n", "credential"),
        ("response.json", b'{"clientSecret": "planted-credential"}', "credential"),
        ("response.json", b'{"password": 846297}', "credential"),
        ("response.json", b'{"password":\n"planted-credential"}', "credential"),
        ("response.json", b'{"password": "%22planted-credential"}', "credential"),
        ("response.yaml", b"password:\n  planted-credential\n", "credential"),
        ("response.http", b"Authorization: [REDACTED]planted-credential\n", "credential"),
        ("response.xml", b"<password>planted-credential</password>", "credential"),
        ("response.txt", b"https://fixture:planted-credential@api.example.test/", "credential"),
        ("response.txt", b"https://api.example.test/?%61pi_key=planted-credential", "credential"),
        ("response.txt", b"-----BEGIN PRIVATE KEY-----", "credential"),
        ("response.txt", b"ghp_" + b"x" * 36, "credential"),
        ("response.json", rb'{"email":"planted\u0040fixture-check.example.com"}', "personal"),
        ("response.html", b"planted&#64;fixture-check.example.com", "personal"),
        ("response.json", b'{"phoneNumber": "+1 202 555 0107"}', "personal"),
        ("response.yaml", b"street_address: 20 Planted Fixture Lane", "personal"),
        ("response.json", b'{"fullName": "Planted Fixture Person"}', "personal"),
        (
            "response.csv",
            b'id,"phone_number",label\n1,"+1 202 555 0107","sensor, test"',
            "personal",
        ),
        ("response.tsv", b"id\tpassword\n1\tplanted-credential\n", "credential"),
    ],
)
def test_sensitive_fixture_fails_without_disclosing_the_value(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, filename: str, content: bytes, rule: str
) -> None:
    path = f"tests/sources/fixtures/nested/{filename}"
    _fixture(tmp_path, path, content)

    assert main(["--root", str(tmp_path)]) == 1
    assert caplog.messages == [f"ERROR: '{path}': {rule} pattern"]


def test_sanitized_fixture_and_config_metadata_pass(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _fixture(
        tmp_path,
        "tests/fixtures/source/config.yaml",
        b"auth_env: FIXTURE_TOKEN\nsecret_query_parameters: [access_token]\n"
        b"api_key: null\nAuthorization: '[REDACTED]'\nreviewer: fixture-maintainer\n"
        b"uri: https://api.example.test?access_token=%5BREDACTED%5D\n",
    )
    _fixture(
        tmp_path,
        "tests/sources/fixtures/data.json",
        rb'{"id": "001", "label": "\u0422\u0435\u0441\u0442", "email": "test@example.com"}',
    )
    _fixture(tmp_path, "tests/sources/fixtures/data.csv", b"id,password\n1,\n2,[REDACTED]\n")
    _fixture(tmp_path, "tests/sources/arbitrary.txt", b"Authorization: Bearer planted-credential")

    with caplog.at_level(logging.INFO):
        assert main(["--root", str(tmp_path)]) == 0
    assert caplog.messages == ["[fixture-check] 3 file(s) checked"]


@pytest.mark.parametrize(
    ("filename", "content", "rule"),
    [
        ("archive.warc", b"still a raw capture", "unsupported file type"),
        ("archive.zip", b"compressed fixture", "unsupported file type"),
        ("binary.json", b"\xff", "not UTF-8 text"),
        ("binary.txt", b"text\x00data", "not UTF-8 text"),
    ],
)
def test_unscannable_fixture_fails(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, filename: str, content: bytes, rule: str
) -> None:
    path = f"tests/fixtures/{filename}"
    _fixture(tmp_path, path, content)

    assert main(["--root", str(tmp_path)]) == 1
    assert caplog.messages == [f"ERROR: '{path}': {rule}"]


def test_fixture_size_is_bounded(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = _fixture(tmp_path, "tests/fixtures/oversized.txt", b"")
    with path.open("wb") as stream:
        stream.truncate(9 * 1024 * 1024)

    assert main(["--root", str(tmp_path)]) == 1
    assert caplog.messages == ["ERROR: 'tests/fixtures/oversized.txt': exceeds 8 MiB"]


@pytest.mark.parametrize("link", ["fixtures", "fixtures/external"])
def test_fixture_symlink_does_not_read_target(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, link: str
) -> None:
    _fixture(tmp_path, "outside-data/response.txt", b"password=planted-credential")
    path = tmp_path / "tests" / link
    path.parent.mkdir(parents=True)
    path.symlink_to(tmp_path / "outside-data", target_is_directory=True)

    assert main(["--root", str(tmp_path)]) == 1
    assert caplog.messages == [f"ERROR: 'tests/{link}': symbolic link"]


def test_redacts_a_sensitive_filename(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    _fixture(tmp_path, "tests/fixtures/planted@fixture-check.invalid.example.txt", b"safe")

    assert main(["--root", str(tmp_path)]) == 1
    assert caplog.messages == ["ERROR: <redacted fixture path>: personal pattern in path"]


def test_detects_a_missing_test_tree(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    assert main(["--root", str(tmp_path)]) == 1
    assert caplog.messages == ["ERROR: 'tests': cannot traverse fixture tree"]
