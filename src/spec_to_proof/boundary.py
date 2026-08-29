"""Generate a small Python boundary for the reviewed function corpus."""

from __future__ import annotations

import pprint
from pathlib import Path

from spec_to_proof.contracts import FunctionContract, load_contract_directory


def render_boundary(contracts: tuple[FunctionContract, ...]) -> str:
    metadata = {
        contract.contract_id: {
            "contract_hash": contract.contract_hash,
            "examples": [
                {"input": example.input, "output": example.output}
                for example in contract.examples
            ],
        }
        for contract in contracts
    }
    encoded_metadata = pprint.pformat(metadata, sort_dicts=True, width=100)
    return f'''"""Generated boundary for reviewed spec-to-proof contracts."""

from spec_to_proof.reference import REFERENCE_FUNCTIONS

CONTRACTS = {encoded_metadata}


def invoke(contract_id, input_value):
    function = REFERENCE_FUNCTIONS[contract_id]
    if isinstance(input_value, list) and contract_id != "increment-all":
        return function(*input_value)
    return function(input_value)


def verify_examples():
    failures = []
    for contract_id, contract in CONTRACTS.items():
        for example in contract["examples"]:
            actual = invoke(contract_id, example["input"])
            if actual != example["output"]:
                failures.append((contract_id, example["input"], actual))
    return failures
'''


def write_boundary(
    output_path: str | Path,
    contracts_directory: str | Path = "contracts",
) -> tuple[FunctionContract, ...]:
    contracts = load_contract_directory(contracts_directory)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_boundary(contracts), encoding="utf-8")
    return contracts
