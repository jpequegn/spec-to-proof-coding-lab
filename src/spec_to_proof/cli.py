"""Contract review and specification rendering CLI."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from spec_to_proof.comparison import run_comparison, write_comparison_report
from spec_to_proof.contracts import (
    ContractDiagnostic,
    ContractError,
    FunctionContract,
    load_contract_directory,
)
from spec_to_proof.receipts import (
    ReceiptError,
    generate_receipts,
    verify_receipts,
    write_receipts,
)
from spec_to_proof.templates import render_spec_skeleton


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spec-to-proof",
        description="Review contracts and machine-checked proof evidence.",
    )
    parser.add_argument(
        "--contracts",
        type=Path,
        default=Path("contracts"),
        help="Directory containing versioned JSON contracts",
    )
    commands = parser.add_subparsers(dest="command")

    list_command = commands.add_parser("list", help="List reviewed contracts")
    list_command.add_argument("--format", choices=("text", "json"), default="text")

    commands.add_parser("validate", help="Validate every contract")

    inspect = commands.add_parser("inspect", help="Inspect one canonical contract")
    inspect.add_argument("contract_id")

    render = commands.add_parser("render", help="Render a Lean proposition skeleton")
    render.add_argument("contract_id")
    render.add_argument("--output", type=Path)

    compare = commands.add_parser("compare", help="Compare test and proof evidence")
    compare.add_argument("--faults", type=Path, default=Path("faults/index.json"))
    compare.add_argument("--output", type=Path, default=Path("artifacts/comparison"))
    compare.add_argument("--seed", type=int, default=259)
    compare.add_argument("--samples", type=int, default=100)

    receipts = commands.add_parser("receipts", help="Generate or verify proof receipts")
    receipt_commands = receipts.add_subparsers(dest="receipt_command", required=True)
    generate = receipt_commands.add_parser("generate", help="Generate proof receipts")
    generate.add_argument("--output", type=Path, default=Path("artifacts/receipts"))
    generate.add_argument("--lake", default="lake")
    verify = receipt_commands.add_parser("verify", help="Verify proof receipts")
    verify.add_argument("--receipts", type=Path, default=Path("artifacts/receipts"))
    verify.add_argument("--lake", default="lake")
    return parser


def _find_contract(
    contracts: tuple[FunctionContract, ...],
    contract_id: str,
) -> FunctionContract:
    for contract in contracts:
        if contract.contract_id == contract_id:
            return contract
    raise ContractError(
        ContractDiagnostic(
            code="CONTRACT_NOT_FOUND",
            message=f"Unknown contract: {contract_id}",
            contract_id=contract_id,
        )
    )


def _run(args: argparse.Namespace) -> int:
    if args.command is None:
        build_parser().print_help()
        return 0

    if args.command == "compare":
        report = run_comparison(
            args.contracts,
            args.faults,
            seed=args.seed,
            fuzz_samples=args.samples,
        )
        write_comparison_report(report, args.output)
        print(
            f"Compared {len(report.candidates)} candidates; "
            f"weak-test false negatives: {report.weak_false_negatives}; "
            f"report: {args.output}"
        )
        return 0

    if args.command == "receipts":
        if args.receipt_command == "generate":
            receipts = generate_receipts(
                contracts_directory=args.contracts,
                lake=args.lake,
            )
            write_receipts(receipts, args.output)
            print(f"Generated {len(receipts)} verified receipts in {args.output}")
        else:
            receipts = verify_receipts(
                receipts_directory=args.receipts,
                lake=args.lake,
            )
            print(f"Verified {len(receipts)} proof receipts")
        return 0

    contracts = load_contract_directory(args.contracts)
    if args.command == "list":
        payload = [
            {
                "contract_id": contract.contract_id,
                "title": contract.title,
                "contract_hash": contract.contract_hash,
            }
            for contract in contracts
        ]
        if args.format == "json":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for item in payload:
                print(f"{item['contract_id']}\t{item['contract_hash']}\t{item['title']}")
        return 0

    if args.command == "validate":
        print(f"Validated {len(contracts)} contracts")
        return 0

    contract = _find_contract(contracts, args.contract_id)
    if args.command == "inspect":
        payload = contract.as_dict()
        payload["contract_hash"] = contract.contract_hash
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    rendered = render_spec_skeleton(contract)
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except ContractError as exc:
        print(
            json.dumps({"error": exc.diagnostic.as_dict()}, sort_keys=True),
            file=sys.stderr,
        )
        return 2
    except ReceiptError as exc:
        error = {"error": {"code": "RECEIPT_INVALID", "message": str(exc)}}
        print(json.dumps(error), file=sys.stderr)
        return 2
    except OSError as exc:
        diagnostic = ContractDiagnostic(
            code="IO_ERROR",
            message=str(exc),
            source=str(exc.filename) if exc.filename else None,
        )
        print(json.dumps({"error": diagnostic.as_dict()}, sort_keys=True), file=sys.stderr)
        return 2
