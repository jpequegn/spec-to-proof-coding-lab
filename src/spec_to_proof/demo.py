"""End-to-end lab demonstration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spec_to_proof.boundary import write_boundary
from spec_to_proof.comparison import run_comparison, write_comparison_report
from spec_to_proof.receipts import CommandRunner, _run_command, generate_receipts, write_receipts


def run_demo(
    project_root: str | Path = ".",
    *,
    output_directory: str | Path = "artifacts/demo",
    lake: str = "lake",
    command_runner: CommandRunner = _run_command,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    output = root / output_directory
    contracts = write_boundary(output / "boundary.py", root / "contracts")
    comparison = run_comparison(root / "contracts", root / "faults/index.json")
    write_comparison_report(comparison, output / "comparison")
    receipts = generate_receipts(root, lake=lake, command_runner=command_runner)
    write_receipts(receipts, output / "receipts")
    summary = {
        "contracts_validated": len(contracts),
        "proof_receipts_verified": len(receipts),
        "faulty_candidates_compared": len(comparison.candidates),
        "weak_test_false_negatives": comparison.weak_false_negatives,
        "artifacts": {
            "boundary": "boundary.py",
            "comparison": "comparison/comparison.md",
            "receipts": "receipts/manifest.md",
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
