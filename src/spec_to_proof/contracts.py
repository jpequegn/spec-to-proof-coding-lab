"""Versioned function contracts and validation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
_THEOREM_PATTERN = re.compile(r"^SpecToProof\.[A-Za-z][A-Za-z0-9_]*$")
_VACUOUS_CLAIMS = {"true", "always true", "result = result", "output = output"}


@dataclass(frozen=True, slots=True)
class ContractDiagnostic:
    code: str
    message: str
    contract_id: str | None = None
    field: str | None = None
    source: str | None = None

    def as_dict(self) -> dict[str, str]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value is not None
        }


class ContractError(Exception):
    def __init__(self, diagnostic: ContractDiagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


@dataclass(frozen=True, slots=True)
class ContractExample:
    input: Any
    output: Any


@dataclass(frozen=True, slots=True)
class FunctionContract:
    schema_version: str
    contract_id: str
    title: str
    summary: str
    input_type: str
    output_type: str
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    invariants: tuple[str, ...]
    examples: tuple[ContractExample, ...]
    non_goals: tuple[str, ...]
    ambiguity_notes: tuple[str, ...]
    theorem_names: tuple[str, ...]

    @property
    def contract_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_id": self.contract_id,
            "title": self.title,
            "summary": self.summary,
            "input_type": self.input_type,
            "output_type": self.output_type,
            "preconditions": list(self.preconditions),
            "postconditions": list(self.postconditions),
            "invariants": list(self.invariants),
            "examples": [asdict(example) for example in self.examples],
            "non_goals": list(self.non_goals),
            "ambiguity_notes": list(self.ambiguity_notes),
            "theorem_names": list(self.theorem_names),
        }


def _fail(
    code: str,
    message: str,
    *,
    contract_id: str | None = None,
    field: str | None = None,
    source: str | None = None,
) -> None:
    raise ContractError(
        ContractDiagnostic(
            code=code,
            message=message,
            contract_id=contract_id,
            field=field,
            source=source,
        )
    )


def _required_string(data: dict[str, Any], field: str, contract_id: str | None) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        _fail(
            "CONTRACT_INVALID",
            f"{field} must be a non-empty string",
            contract_id=contract_id,
            field=field,
        )
    return value.strip()


def _string_list(
    data: dict[str, Any],
    field: str,
    contract_id: str,
) -> tuple[str, ...]:
    value = data.get(field)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        _fail(
            "CONTRACT_INVALID",
            f"{field} must be a non-empty list of strings",
            contract_id=contract_id,
            field=field,
        )
    return tuple(item.strip() for item in value)


def contract_from_dict(data: dict[str, Any]) -> FunctionContract:
    raw_id = data.get("contract_id")
    contract_id = raw_id.strip() if isinstance(raw_id, str) and raw_id.strip() else None
    if data.get("schema_version") != SCHEMA_VERSION:
        _fail(
            "CONTRACT_SCHEMA_VERSION",
            f"schema_version must be {SCHEMA_VERSION}",
            contract_id=contract_id,
            field="schema_version",
        )
    if contract_id is None:
        _fail("CONTRACT_INVALID", "contract_id must be a non-empty string", field="contract_id")

    examples_data = data.get("examples")
    if not isinstance(examples_data, list) or len(examples_data) < 2:
        _fail(
            "CONTRACT_INVALID",
            "examples must contain at least two cases",
            contract_id=contract_id,
            field="examples",
        )
    examples: list[ContractExample] = []
    seen: dict[str, str] = {}
    for index, item in enumerate(examples_data):
        if not isinstance(item, dict) or set(item) != {"input", "output"}:
            _fail(
                "CONTRACT_INVALID",
                f"example {index} must contain only input and output",
                contract_id=contract_id,
                field="examples",
            )
        input_key = json.dumps(item["input"], sort_keys=True, separators=(",", ":"))
        output_key = json.dumps(item["output"], sort_keys=True, separators=(",", ":"))
        previous = seen.get(input_key)
        if previous is not None and previous != output_key:
            _fail(
                "CONTRACT_CONTRADICTORY",
                f"examples assign different outputs to input {input_key}",
                contract_id=contract_id,
                field="examples",
            )
        seen[input_key] = output_key
        examples.append(ContractExample(input=item["input"], output=item["output"]))

    postconditions = _string_list(data, "postconditions", contract_id)
    if any(claim.casefold() in _VACUOUS_CLAIMS for claim in postconditions):
        _fail(
            "CONTRACT_VACUOUS",
            "postconditions contain a trivially true claim",
            contract_id=contract_id,
            field="postconditions",
        )

    ambiguity_notes = _string_list(data, "ambiguity_notes", contract_id)
    unresolved = [note for note in ambiguity_notes if not note.casefold().startswith("resolved:")]
    if unresolved:
        _fail(
            "CONTRACT_AMBIGUOUS",
            "all ambiguity notes must record an explicit resolution",
            contract_id=contract_id,
            field="ambiguity_notes",
        )

    theorem_names = _string_list(data, "theorem_names", contract_id)
    if any(_THEOREM_PATTERN.fullmatch(name) is None for name in theorem_names):
        _fail(
            "CONTRACT_INVALID",
            "theorem_names must use the SpecToProof namespace",
            contract_id=contract_id,
            field="theorem_names",
        )

    return FunctionContract(
        schema_version=SCHEMA_VERSION,
        contract_id=contract_id,
        title=_required_string(data, "title", contract_id),
        summary=_required_string(data, "summary", contract_id),
        input_type=_required_string(data, "input_type", contract_id),
        output_type=_required_string(data, "output_type", contract_id),
        preconditions=_string_list(data, "preconditions", contract_id),
        postconditions=postconditions,
        invariants=_string_list(data, "invariants", contract_id),
        examples=tuple(examples),
        non_goals=_string_list(data, "non_goals", contract_id),
        ambiguity_notes=ambiguity_notes,
        theorem_names=theorem_names,
    )


def load_contract(path: str | Path) -> FunctionContract:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("CONTRACT_JSON_ERROR", str(exc), source=str(source))
    if not isinstance(data, dict):
        _fail("CONTRACT_INVALID", "contract root must be a JSON object", source=str(source))
    try:
        return contract_from_dict(data)
    except ContractError as exc:
        diagnostic = exc.diagnostic
        raise ContractError(
            ContractDiagnostic(
                code=diagnostic.code,
                message=diagnostic.message,
                contract_id=diagnostic.contract_id,
                field=diagnostic.field,
                source=str(source),
            )
        ) from exc


def load_contract_directory(path: str | Path) -> tuple[FunctionContract, ...]:
    directory = Path(path)
    contracts = tuple(load_contract(item) for item in sorted(directory.glob("*.json")))
    if not contracts:
        _fail(
            "CONTRACT_INVALID",
            "contract directory contains no JSON contracts",
            source=str(directory),
        )
    ids = [contract.contract_id for contract in contracts]
    if len(ids) != len(set(ids)):
        _fail(
            "CONTRACT_CONTRADICTORY",
            "contract IDs must be unique",
            source=str(directory),
        )
    return contracts
