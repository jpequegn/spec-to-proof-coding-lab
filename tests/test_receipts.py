import json
import shutil
from pathlib import Path

import pytest

from spec_to_proof.receipts import (
    ReceiptError,
    generate_receipts,
    verify_receipts,
    write_receipts,
)


def fake_runner(command: list[str], _root: Path) -> str:
    if command[-1] == "--version":
        return "Lean (version 4.33.1, test fixture)"
    return ""


def copy_project_inputs(destination: Path) -> None:
    root = Path.cwd()
    shutil.copytree(root / "contracts", destination / "contracts")
    shutil.copytree(root / "SpecToProof", destination / "SpecToProof")
    shutil.copy(root / "SpecToProof.lean", destination / "SpecToProof.lean")
    shutil.copy(root / "lean-toolchain", destination / "lean-toolchain")


def test_generates_receipt_for_every_contract(tmp_path: Path) -> None:
    copy_project_inputs(tmp_path)
    receipts = generate_receipts(tmp_path, command_runner=fake_runner)
    write_receipts(receipts, tmp_path / "artifacts/receipts")

    manifest = json.loads(
        (tmp_path / "artifacts/receipts/manifest.json").read_text(encoding="utf-8")
    )
    assert len(receipts) == 5
    assert len(manifest["receipts"]) == 5
    assert all(receipt.proof_status == "verified" for receipt in receipts)
    assert all(receipt.unresolved_assumptions for receipt in receipts)
    assert (tmp_path / "artifacts/receipts/parse-bit.md").is_file()


def test_verifies_untampered_receipts(tmp_path: Path) -> None:
    copy_project_inputs(tmp_path)
    receipts = generate_receipts(tmp_path, command_runner=fake_runner)
    write_receipts(receipts, tmp_path / "artifacts/receipts")

    verified = verify_receipts(tmp_path, command_runner=fake_runner)
    assert [receipt.contract_id for receipt in verified] == [
        receipt.contract_id for receipt in receipts
    ]


@pytest.mark.parametrize(
    ("relative_path", "suffix", "message"),
    [
        ("contracts/clamp.json", "\n", "contract source changed"),
        ("SpecToProof/Arithmetic.lean", "\n-- changed\n", "Lean source changed"),
    ],
)
def test_tampering_invalidates_receipts(
    tmp_path: Path,
    relative_path: str,
    suffix: str,
    message: str,
) -> None:
    copy_project_inputs(tmp_path)
    receipts = generate_receipts(tmp_path, command_runner=fake_runner)
    write_receipts(receipts, tmp_path / "artifacts/receipts")
    target = tmp_path / relative_path
    target.write_text(target.read_text(encoding="utf-8") + suffix, encoding="utf-8")

    with pytest.raises(ReceiptError, match=message):
        verify_receipts(tmp_path, command_runner=fake_runner)


def test_receipt_digest_detects_report_tampering(tmp_path: Path) -> None:
    copy_project_inputs(tmp_path)
    receipts = generate_receipts(tmp_path, command_runner=fake_runner)
    write_receipts(receipts, tmp_path / "artifacts/receipts")
    manifest_path = tmp_path / "artifacts/receipts/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["receipts"][0]["proof_status"] = "unverified"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReceiptError, match="manifest digest mismatch"):
        verify_receipts(tmp_path, command_runner=fake_runner)


def test_individual_markdown_tampering_is_detected(tmp_path: Path) -> None:
    copy_project_inputs(tmp_path)
    receipts = generate_receipts(tmp_path, command_runner=fake_runner)
    write_receipts(receipts, tmp_path / "artifacts/receipts")
    markdown = tmp_path / "artifacts/receipts/clamp.md"
    markdown.write_text("changed\n", encoding="utf-8")

    with pytest.raises(ReceiptError, match="receipt Markdown changed"):
        verify_receipts(tmp_path, command_runner=fake_runner)


def test_stale_compiler_metadata_is_detected(tmp_path: Path) -> None:
    copy_project_inputs(tmp_path)
    receipts = generate_receipts(tmp_path, command_runner=fake_runner)
    write_receipts(receipts, tmp_path / "artifacts/receipts")

    def changed_runner(command: list[str], _root: Path) -> str:
        if command[-1] == "--version":
            return "Lean (version 4.34.0, changed fixture)"
        return ""

    with pytest.raises(ReceiptError, match="compiler metadata is stale"):
        verify_receipts(tmp_path, command_runner=changed_runner)
