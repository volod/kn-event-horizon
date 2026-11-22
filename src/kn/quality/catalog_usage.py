"""Static message-key usage and literal checks at the operator boundary."""

import ast
from pathlib import Path

_RENDER_METHODS = {"text", "plural"}
_LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}
_COPY_KEYWORDS = {"help", "description", "epilog", "title"}


def _method(call: ast.Call) -> str:
    return call.func.attr if isinstance(call.func, ast.Attribute) else ""


def _literal(value: ast.expr) -> bool:
    if isinstance(value, ast.Constant):
        return isinstance(value.value, str) and bool(value.value.strip()) and value.value != "%s"
    if isinstance(value, ast.BinOp):
        return _literal(value.left) or _literal(value.right)
    return isinstance(value, ast.JoinedStr)


def inspect_source(path: Path, *, operator: bool) -> tuple[dict[str, str], list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    used: dict[str, str] = {}
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        method = _method(node)
        if method in _RENDER_METHODS and _translation_receiver(node):
            _key_usage(node, method, used, findings)
        if operator and _has_literal(node, method):
            findings.append(f"line {node.lineno}: user-facing literal")
    return used, findings


def _translation_receiver(node: ast.Call) -> bool:
    assert isinstance(node.func, ast.Attribute)
    receiver = node.func.value
    if isinstance(receiver, ast.Name):
        return receiver.id not in {"sa", "sqlalchemy", "connection"}
    return isinstance(receiver, (ast.Attribute, ast.Call))


def _key_usage(node: ast.Call, method: str, used: dict[str, str], findings: list[str]) -> None:
    key = node.args[0] if node.args else None
    if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
        findings.append(f"line {node.lineno}: message key must be a literal")
        return
    previous = used.get(key.value)
    if previous is not None and previous != method:
        findings.append(f"line {node.lineno}: mixed message kind: {key.value}")
    used[key.value] = method


def _has_literal(node: ast.Call, method: str) -> bool:
    if any(item.arg in _COPY_KEYWORDS and _literal(item.value) for item in node.keywords):
        return True
    if method in _LOG_METHODS:
        return any(_literal(arg) for arg in node.args)
    if method in {"exit", "error", "write", "print"} or (
        isinstance(node.func, ast.Name) and node.func.id == "print"
    ):
        return any(_literal(arg) for arg in node.args)
    return False
