"""Tamper-evident receipts for Lean proof evidence."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from spec_to_proof.contracts import FunctionContract, load_contract_directory

RECEIPT_VERSION = "1.0"
SOURCE_MODULES = {
    "saturating-add": "SpecToProof/Arithmetic.lean",
    "clamp": "SpecToProof/Arithmetic.lean",
    "increment-all": "SpecToProof/Lists.lean",
    "sort-pair": "SpecToProof/Ordering.lean",
    "parse-bit": "SpecToProof/Parsing.lean",
}


class ReceiptError(Exception):
    """Raised when receipt generation or verification cannot be trusted."""


CommandRunner = Callable[[list[str], Path], str]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(encoded)


def _run_command(command: list[str], project_root: Path) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise ReceiptError(f"command failed: {' '.join(command)}: {detail.strip()}") from exc
    return result.stdout.strip()


@dataclass(frozen=True, slots=True)
class ProofReceipt:
    receipt_version: str
    contract_id: str
    contract_path: str
    contract_hash: str
    contract_source_hash: str
    theorem_names: tuple[str, ...]
    source_hashes: dict[str, str]
    proof_status: str
    lean_toolchain: str
    lean_version: str
    unresolved_assumptions: tuple[str, ...]
    non_goals: tuple[str, ...]

    def unsigned_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_digest(self) -> str:
        return _canonical_hash(self.unsigned_dict())

    def as_dict(self) -> dict[str, Any]:
        payload = self.unsigned_dict()
        payload["receipt_digest"] = self.receipt_digest
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProofReceipt:
        digest = payload.get("receipt_digest")
        unsigned = {key: value for key, value in payload.items() if key != "receipt_digest"}
        try:
            unsigned["theorem_names"] = tuple(unsigned["theorem_names"])
            unsigned["unresolved_assumptions"] = tuple(unsigned["unresolved_assumptions"])
            unsigned["non_goals"] = tuple(unsigned["non_goals"])
            receipt = cls(**unsigned)
        except (KeyError, TypeError) as exc:
            raise ReceiptError(f"invalid receipt structure: {exc}") from exc
        if digest != receipt.receipt_digest:
            raise ReceiptError(f"receipt digest mismatch: {receipt.contract_id}")
        return receipt


def _assumptions(contract: FunctionContract) -> tuple[str, ...]:
    assumptions = [
        "The pinned Lean compiler, kernel, and trusted platform execute correctly.",
        "The receipt covers the named Lean definitions only; runtime implementations "
        "require a separate equivalence check.",
    ]
    assumptions.extend(
        f"Contract precondition: {condition}"
        for condition in contract.preconditions
        if not condition.casefold().startswith("none:")
    )
    return tuple(assumptions)


def _source_paths(contract: FunctionContract) -> tuple[str, ...]:
    try:
        module = SOURCE_MODULES[contract.contract_id]
    except KeyError as exc:
        raise ReceiptError(f"no Lean source mapping for {contract.contract_id}") from exc
    return (module, "SpecToProof.lean")


def _check_theorem_declarations(
    contract: FunctionContract,
    project_root: Path,
) -> None:
    source = (project_root / SOURCE_MODULES[contract.contract_id]).read_text(encoding="utf-8")
    for qualified_name in contract.theorem_names:
        theorem_name = qualified_name.rsplit(".", 1)[-1]
        pattern = rf"(?m)^\s*(?:theorem|lemma)\s+{re.escape(theorem_name)}\b"
        if re.search(pattern, source) is None:
            module = SOURCE_MODULES[contract.contract_id]
            raise ReceiptError(
                f"theorem {qualified_name} is not declared in {module}"
            )


def _check_theorems_with_lean(
    theorem_names: tuple[str, ...],
    project_root: Path,
    lake: str,
    command_runner: CommandRunner,
) -> None:
    checks = "import SpecToProof\n\n" + "\n".join(
        f"#check {theorem_name}" for theorem_name in theorem_names
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lean", encoding="utf-8") as handle:
        handle.write(checks)
        handle.flush()
        command_runner([lake, "env", "lean", handle.name], project_root)


def generate_receipts(
    project_root: str | Path = ".",
    *,
    contracts_directory: str | Path = "contracts",
    lake: str = "lake",
    command_runner: CommandRunner = _run_command,
) -> tuple[ProofReceipt, ...]:
    root = Path(project_root).resolve()
    contracts_path = root / contracts_directory
    contracts = load_contract_directory(contracts_path)
    command_runner([lake, "build"], root)
    lean_version = command_runner([lake, "env", "lean", "--version"], root)
    lean_toolchain = (root / "lean-toolchain").read_text(encoding="utf-8").strip()
    receipts: list[ProofReceipt] = []
    for contract in contracts:
        _check_theorem_declarations(contract, root)
        _check_theorems_with_lean(contract.theorem_names, root, lake, command_runner)
        contract_path = contracts_path / f"{contract.contract_id}.json"
        source_hashes = {
            path: _sha256_file(root / path) for path in _source_paths(contract)
        }
        receipts.append(
            ProofReceipt(
                receipt_version=RECEIPT_VERSION,
                contract_id=contract.contract_id,
                contract_path=str(contract_path.relative_to(root)),
                contract_hash=contract.contract_hash,
                contract_source_hash=_sha256_file(contract_path),
                theorem_names=contract.theorem_names,
                source_hashes=source_hashes,
                proof_status="verified",
                lean_toolchain=lean_toolchain,
                lean_version=lean_version,
                unresolved_assumptions=_assumptions(contract),
                non_goals=contract.non_goals,
            )
        )
    return tuple(receipts)


def _render_receipt(receipt: ProofReceipt) -> str:
    lines = [
        f"# Proof receipt: {receipt.contract_id}",
        "",
        f"- Status: {receipt.proof_status}",
        f"- Receipt digest: `{receipt.receipt_digest}`",
        f"- Contract hash: `{receipt.contract_hash}`",
        f"- Contract source hash: `{receipt.contract_source_hash}`",
        f"- Lean toolchain: `{receipt.lean_toolchain}`",
        f"- Lean version: `{receipt.lean_version}`",
        "",
        "## Checked Theorems",
        "",
        *(f"- `{name}`" for name in receipt.theorem_names),
        "",
        "## Source Hashes",
        "",
        *(
            f"- `{path}`: `{receipt.source_hashes[path]}`"
            for path in sorted(receipt.source_hashes)
        ),
        "",
        "## Unresolved Assumptions",
        "",
        *(f"- {assumption}" for assumption in receipt.unresolved_assumptions),
        "",
        "## Explicit Non-Goals",
        "",
        *(f"- {non_goal}" for non_goal in receipt.non_goals),
        "",
    ]
    return "\n".join(lines)


def _render_manifest(receipts: tuple[ProofReceipt, ...]) -> str:
    lines = ["# Proof receipt manifest", ""]
    lines.extend(
        f"- [{receipt.contract_id}]({receipt.contract_id}.md): verified"
        for receipt in receipts
    )
    return "\n".join(lines) + "\n"


def write_receipts(receipts: tuple[ProofReceipt, ...], output_directory: str | Path) -> None:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "receipt_version": RECEIPT_VERSION,
        "receipts": [receipt.as_dict() for receipt in receipts],
    }
    manifest["manifest_digest"] = _canonical_hash(manifest)
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for receipt in receipts:
        (output / f"{receipt.contract_id}.json").write_text(
            json.dumps(receipt.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output / f"{receipt.contract_id}.md").write_text(
            _render_receipt(receipt),
            encoding="utf-8",
        )
    (output / "manifest.md").write_text(_render_manifest(receipts), encoding="utf-8")


def verify_receipts(
    project_root: str | Path = ".",
    *,
    receipts_directory: str | Path = "artifacts/receipts",
    lake: str = "lake",
    command_runner: CommandRunner = _run_command,
) -> tuple[ProofReceipt, ...]:
    root = Path(project_root).resolve()
    directory = root / receipts_directory
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    manifest_digest = manifest.pop("manifest_digest", None)
    if manifest_digest != _canonical_hash(manifest):
        raise ReceiptError("manifest digest mismatch")
    receipts = tuple(ProofReceipt.from_dict(payload) for payload in manifest["receipts"])
    lean_toolchain = (root / "lean-toolchain").read_text(encoding="utf-8").strip()
    if any(receipt.lean_toolchain != lean_toolchain for receipt in receipts):
        raise ReceiptError("Lean toolchain metadata is stale")
    contracts = {
        contract.contract_id: contract
        for contract in load_contract_directory(root / "contracts")
    }
    receipt_ids = [receipt.contract_id for receipt in receipts]
    if len(receipt_ids) != len(set(receipt_ids)) or set(receipt_ids) != set(contracts):
        raise ReceiptError("receipt set does not match the reviewed contract set")
    if (directory / "manifest.md").read_text(encoding="utf-8") != _render_manifest(receipts):
        raise ReceiptError("Markdown manifest changed")
    for receipt in receipts:
        receipt_path = directory / f"{receipt.contract_id}.json"
        individual = ProofReceipt.from_dict(
            json.loads(receipt_path.read_text(encoding="utf-8"))
        )
        if individual != receipt:
            raise ReceiptError(f"individual receipt changed: {receipt.contract_id}")
        markdown = (directory / f"{receipt.contract_id}.md").read_text(encoding="utf-8")
        if markdown != _render_receipt(receipt):
            raise ReceiptError(f"receipt Markdown changed: {receipt.contract_id}")
        contract = contracts.get(receipt.contract_id)
        if contract is None or contract.contract_hash != receipt.contract_hash:
            raise ReceiptError(f"contract changed: {receipt.contract_id}")
        if _sha256_file(root / receipt.contract_path) != receipt.contract_source_hash:
            raise ReceiptError(f"contract source changed: {receipt.contract_id}")
        for path, expected_hash in receipt.source_hashes.items():
            if _sha256_file(root / path) != expected_hash:
                raise ReceiptError(f"Lean source changed: {path}")
        if contract.theorem_names != receipt.theorem_names:
            raise ReceiptError(f"theorem list changed: {receipt.contract_id}")
        _check_theorem_declarations(contract, root)
    command_runner([lake, "build"], root)
    lean_version = command_runner([lake, "env", "lean", "--version"], root)
    if any(receipt.lean_version != lean_version for receipt in receipts):
        raise ReceiptError("Lean compiler metadata is stale")
    for receipt in receipts:
        _check_theorems_with_lean(receipt.theorem_names, root, lake, command_runner)
    return receipts
