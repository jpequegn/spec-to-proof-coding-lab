import json
from pathlib import Path

from spec_to_proof.demo import run_demo


def fake_runner(command: list[str], _root: Path) -> str:
    if command[-1] == "--version":
        return "Lean (version 4.33.1, demo fixture)"
    return ""


def test_demo_writes_complete_artifact_set(tmp_path: Path) -> None:
    root = Path.cwd()
    summary = run_demo(
        root,
        output_directory=tmp_path,
        command_runner=fake_runner,
    )

    assert summary == json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["contracts_validated"] == 5
    assert summary["proof_receipts_verified"] == 5
    assert summary["weak_test_false_negatives"] == 1
    assert (tmp_path / "boundary.py").is_file()
    assert (tmp_path / "comparison/comparison.json").is_file()
    assert (tmp_path / "receipts/manifest.json").is_file()
