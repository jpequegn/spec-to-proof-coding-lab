import json
from pathlib import Path

import pytest

from spec_to_proof.cli import main
from spec_to_proof.contracts import ContractError, load_contract
from spec_to_proof.templates import TEMPLATES, render_spec_skeleton


def test_every_contract_has_an_exact_template() -> None:
    for path in Path("contracts").glob("*.json"):
        contract = load_contract(path)
        template = TEMPLATES[contract.contract_id]
        assert template.theorem_names == contract.theorem_names


def test_render_is_stable_and_contains_no_proof_body() -> None:
    contract = load_contract("contracts/clamp.json")

    first = render_spec_skeleton(contract)
    second = render_spec_skeleton(contract)

    assert first == second
    assert contract.contract_hash in first
    assert "def ClampContract" in first
    assert "NO PROOF BODY" in first
    assert ":= by" not in first
    assert "sorry" not in first.casefold()


def test_template_drift_fails() -> None:
    contract = load_contract("contracts/clamp.json")
    original = TEMPLATES["clamp"]
    TEMPLATES["clamp"] = type(original)(
        contract_id=original.contract_id,
        theorem_names=("SpecToProof.changed",),
        declaration=original.declaration,
    )
    try:
        with pytest.raises(ContractError) as caught:
            render_spec_skeleton(contract)
        assert caught.value.diagnostic.code == "CONTRACT_TEMPLATE_DRIFT"
    finally:
        TEMPLATES["clamp"] = original


def test_cli_lists_validates_inspects_and_renders(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["list", "--format", "json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert len(listed) == 5

    assert main(["validate"]) == 0
    assert "Validated 5 contracts" in capsys.readouterr().out

    assert main(["inspect", "parse-bit"]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["contract_id"] == "parse-bit"
    assert len(inspected["contract_hash"]) == 64

    output = tmp_path / "ClampSpec.lean"
    assert main(["render", "clamp", "--output", str(output)]) == 0
    capsys.readouterr()
    assert "def ClampContract" in output.read_text(encoding="utf-8")


def test_cli_invalid_contract_is_structured(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["render", "missing"]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["error"]["code"] == "CONTRACT_NOT_FOUND"
