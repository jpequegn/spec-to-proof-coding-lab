import copy
import json
from pathlib import Path

import pytest

from spec_to_proof.contracts import (
    ContractError,
    contract_from_dict,
    load_contract,
    load_contract_directory,
)

CONTRACTS = Path("contracts")


def test_five_contracts_validate_with_unique_hashes() -> None:
    contracts = load_contract_directory(CONTRACTS)

    assert len(contracts) == 5
    assert len({contract.contract_hash for contract in contracts}) == 5
    assert all(contract.theorem_names for contract in contracts)


def test_contract_hash_ignores_json_key_order(tmp_path: Path) -> None:
    source = CONTRACTS / "clamp.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    reversed_data = dict(reversed(list(data.items())))
    reordered = tmp_path / "reordered.json"
    reordered.write_text(json.dumps(reversed_data), encoding="utf-8")

    assert load_contract(source).contract_hash == load_contract(reordered).contract_hash


def _valid_data() -> dict[str, object]:
    return json.loads((CONTRACTS / "clamp.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda data: data.update(schema_version="2.0"), "CONTRACT_SCHEMA_VERSION"),
        (lambda data: data.update(postconditions=["true"]), "CONTRACT_VACUOUS"),
        (
            lambda data: data.update(ambiguity_notes=["unresolved: inclusive upper bound"]),
            "CONTRACT_AMBIGUOUS",
        ),
        (lambda data: data.update(invariants=[]), "CONTRACT_INVALID"),
        (lambda data: data.update(non_goals=[]), "CONTRACT_INVALID"),
        (lambda data: data.update(theorem_names=["Other.theorem"]), "CONTRACT_INVALID"),
    ],
)
def test_underspecified_contracts_fail(
    mutate: object,
    code: str,
) -> None:
    data = _valid_data()
    mutate(data)  # type: ignore[operator]
    with pytest.raises(ContractError) as caught:
        contract_from_dict(data)
    assert caught.value.diagnostic.code == code


def test_contradictory_examples_fail() -> None:
    data = copy.deepcopy(_valid_data())
    data["examples"].append({"input": [5, 0, 10], "output": 9})  # type: ignore[union-attr]

    with pytest.raises(ContractError) as caught:
        contract_from_dict(data)

    assert caught.value.diagnostic.code == "CONTRACT_CONTRADICTORY"


def test_malformed_json_has_source_diagnostic(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text("{bad", encoding="utf-8")

    with pytest.raises(ContractError) as caught:
        load_contract(source)

    assert caught.value.diagnostic.code == "CONTRACT_JSON_ERROR"
    assert caught.value.diagnostic.source == str(source)
