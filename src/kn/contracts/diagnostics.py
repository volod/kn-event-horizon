"""Stable, value-free contract diagnostics for operators and machine consumers."""

import json
from typing import Any

from jsonschema import ValidationError

type Location = tuple[str | int, ...]


class ContractError(ValueError):
    """A rejected contract with a location and a safe explanation of the violated rule."""

    def __init__(self, path: Location, rule: str, hint: str) -> None:
        self.path = "$" + "".join(
            "/" + str(part).replace("~", "~0").replace("/", "~1") for part in path
        )
        self.rule = rule
        self.hint = hint
        super().__init__(f"{self.path}: {rule}: {hint}")

    def diagnostic(self) -> dict[str, str]:
        return {"path": self.path, "rule": self.rule, "hint": self.hint}


def schema_error(error: ValidationError, prefix: Location = ()) -> ContractError:
    """Use schema constraints, never rejected values, in the diagnostic."""
    rule = str(error.validator)
    constraint: Any = error.validator_value
    hints = {
        "required": "include required properties",
        "additionalProperties": "remove unrecognized properties",
        "unevaluatedProperties": "remove unrecognized properties",
    }
    hint = hints.get(rule, f"satisfy {rule} {json.dumps(constraint, ensure_ascii=True)}")
    if rule == "required":
        instance = error.instance
        assert isinstance(instance, dict)
        missing = [name for name in constraint if name not in instance]
        hint += ": " + ", ".join(missing)
    return ContractError(prefix + tuple(error.absolute_path), rule, hint)
