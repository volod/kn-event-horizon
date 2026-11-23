"""Validate reviewed local source documents with value-free diagnostics."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from kn.contracts.diagnostics import ContractError, Location
from kn.contracts.document import read_document


class ReviewDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def read_model[Model: BaseModel](path: Path, model: type[Model], location: Location = ()) -> Model:
    try:
        return model.model_validate(read_document(path))
    except ValidationError as error:
        issue = error.errors(include_input=False)[0]
        raise ContractError(
            (*location, *issue["loc"]), issue["type"], "correct the reviewed source document"
        ) from None
