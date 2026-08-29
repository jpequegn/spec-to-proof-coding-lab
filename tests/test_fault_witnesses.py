import json
import re
from pathlib import Path

from spec_to_proof.contracts import load_contract_directory


def _faults() -> list[dict[str, str]]:
    return json.loads(Path("faults/index.json").read_text(encoding="utf-8"))


def test_three_faults_link_to_contracts_and_witnesses() -> None:
    faults = _faults()
    contract_ids = {
        contract.contract_id for contract in load_contract_directory("contracts")
    }
    lean_source = Path("SpecToProof/Faults.lean").read_text(encoding="utf-8")

    assert len(faults) >= 3
    for fault in faults:
        assert fault["contract_id"] in contract_ids
        assert fault["status"] == "rejected"
        assert fault["violated_claim"]
        assert fault["test_gap"]
        theorem = fault["witness_theorem"].removeprefix("SpecToProof.")
        assert re.search(rf"\btheorem\s+{re.escape(theorem)}\b", lean_source)


def test_rejected_is_distinct_from_unproved() -> None:
    allowed_statuses = {"rejected", "unproved"}
    faults = _faults()

    assert {fault["status"] for fault in faults} <= allowed_statuses
    assert all(fault["status"] == "rejected" for fault in faults)
