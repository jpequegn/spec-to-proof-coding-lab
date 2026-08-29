"""Contract review and specification rendering CLI."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from spec_to_proof.contracts import (
    ContractDiagnostic,
    ContractError,
    FunctionContract,
    load_contract_directory,
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
    except OSError as exc:
        diagnostic = ContractDiagnostic(
            code="IO_ERROR",
            message=str(exc),
            source=str(exc.filename) if exc.filename else None,
        )
        print(json.dumps({"error": diagnostic.as_dict()}, sort_keys=True), file=sys.stderr)
        return 2
