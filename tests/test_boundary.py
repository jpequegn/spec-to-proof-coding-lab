import runpy
from pathlib import Path
from typing import Any

from spec_to_proof.boundary import write_boundary
from spec_to_proof.reference import increment_all, sort_pair


def test_reference_functions_cover_remaining_corpus() -> None:
    assert increment_all([0, 2, 5]) == [1, 3, 6]
    assert sort_pair(9, 3) == [3, 9]


def test_generated_boundary_agrees_with_all_contract_examples(tmp_path: Path) -> None:
    output = tmp_path / "boundary.py"
    contracts = write_boundary(output)
    namespace: dict[str, Any] = runpy.run_path(str(output))

    assert len(contracts) == 5
    assert namespace["verify_examples"]() == []
    assert set(namespace["CONTRACTS"]) == {
        "clamp",
        "increment-all",
        "parse-bit",
        "saturating-add",
        "sort-pair",
    }
    assert namespace["invoke"]("parse-bit", "10") is None
