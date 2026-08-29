"""Deterministic comparison of testing and proof evidence."""

from __future__ import annotations

import json
import platform
import random
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

from spec_to_proof.contracts import FunctionContract, load_contract_directory
from spec_to_proof.reference import FAULTY_FUNCTIONS, REFERENCE_FUNCTIONS

DEFAULT_SEED = 259
DEFAULT_FUZZ_SAMPLES = 100


@dataclass(frozen=True, slots=True)
class MethodEvidence:
    method: str
    candidate_passed: bool
    samples: int
    scope: str
    failing_inputs: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateComparison:
    fault_id: str
    contract_id: str
    witness_theorem: str
    methods: tuple[MethodEvidence, ...]

    @property
    def weak_false_negative(self) -> bool:
        non_proof = [method for method in self.methods if method.method != "lean-proof"]
        proof = next(method for method in self.methods if method.method == "lean-proof")
        return all(method.candidate_passed for method in non_proof) and not proof.candidate_passed


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    seed: int
    fuzz_samples: int
    tool_versions: dict[str, str]
    candidates: tuple[CandidateComparison, ...]

    @property
    def weak_false_negatives(self) -> int:
        return sum(candidate.weak_false_negative for candidate in self.candidates)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["weak_false_negatives"] = self.weak_false_negatives
        return payload


def _call(function: Any, input_value: Any) -> Any:
    if isinstance(input_value, list):
        return function(*input_value)
    return function(input_value)


def _example_evidence(
    contract: FunctionContract,
    candidate: Any,
) -> MethodEvidence:
    failures = tuple(
        example.input
        for example in contract.examples
        if _call(candidate, example.input) != example.output
    )
    return MethodEvidence(
        method="reviewed-examples",
        candidate_passed=not failures,
        samples=len(contract.examples),
        scope="Only examples recorded in the reviewed contract.",
        failing_inputs=failures,
    )


def _property_evidence(contract_id: str, candidate: Any) -> MethodEvidence:
    failures: list[Any] = []
    samples = 0
    if contract_id == "saturating-add":
        for left in range(6):
            for right in range(6):
                for cap in range(6):
                    samples += 1
                    if candidate(left, right, cap) > cap:
                        failures.append([left, right, cap])
    elif contract_id == "clamp":
        for value in range(6):
            for lower in range(6):
                for upper in range(lower, 6):
                    samples += 1
                    result = candidate(value, lower, upper)
                    if not lower <= result <= upper:
                        failures.append([value, lower, upper])
    else:
        for value in ("", "0", "1", "00", "01", "10", "11", "2", "x"):
            samples += 1
            result = candidate(value)
            if result is not None and result > 1:
                failures.append(value)
    return MethodEvidence(
        method="bounded-property",
        candidate_passed=not failures,
        samples=samples,
        scope=(
            "Checks the output bound only; it does not prove exact accepted input strings."
            if contract_id == "parse-bit"
            else "Exhaustive bounded-domain check of the primary safety invariant."
        ),
        failing_inputs=tuple(failures[:5]),
    )


def _fuzz_inputs(contract_id: str, randomizer: random.Random, samples: int) -> list[Any]:
    if contract_id == "saturating-add":
        inputs: list[Any] = [[8, 7, 10]]
        inputs.extend(
            [
                randomizer.randint(0, 100),
                randomizer.randint(0, 100),
                randomizer.randint(0, 100),
            ]
            for _ in range(max(0, samples - 1))
        )
        return inputs
    if contract_id == "clamp":
        inputs = [[2, 4, 9]]
        for _ in range(max(0, samples - 1)):
            lower = randomizer.randint(0, 50)
            upper = randomizer.randint(lower, 100)
            inputs.append([randomizer.randint(0, 100), lower, upper])
        return inputs

    legacy_corpus = ("", "0", "1", "00", "10", "11", "2", "x")
    return [randomizer.choice(legacy_corpus) for _ in range(samples)]


def _fuzz_evidence(
    contract_id: str,
    reference: Any,
    candidate: Any,
    *,
    seed: int,
    samples: int,
) -> MethodEvidence:
    randomizer = random.Random(f"{seed}:{contract_id}")
    inputs = _fuzz_inputs(contract_id, randomizer, samples)
    failures = tuple(
        value
        for value in inputs
        if _call(candidate, value) != _call(reference, value)
    )
    return MethodEvidence(
        method="seeded-fuzz",
        candidate_passed=not failures,
        samples=len(inputs),
        scope=(
            "Legacy parser corpus excludes the leading-zero string 01."
            if contract_id == "parse-bit"
            else f"Deterministic seed {seed} plus a known boundary seed case."
        ),
        failing_inputs=failures[:5],
    )


def run_comparison(
    contracts_directory: str | Path = "contracts",
    faults_path: str | Path = "faults/index.json",
    *,
    seed: int = DEFAULT_SEED,
    fuzz_samples: int = DEFAULT_FUZZ_SAMPLES,
) -> ComparisonReport:
    contracts = {
        contract.contract_id: contract
        for contract in load_contract_directory(contracts_directory)
    }
    faults = json.loads(Path(faults_path).read_text(encoding="utf-8"))
    comparisons: list[CandidateComparison] = []
    for fault in faults:
        contract_id = fault["contract_id"]
        contract = contracts[contract_id]
        candidate = FAULTY_FUNCTIONS[fault["fault_id"]]
        reference = REFERENCE_FUNCTIONS[contract_id]
        methods = (
            _example_evidence(contract, candidate),
            _property_evidence(contract_id, candidate),
            _fuzz_evidence(
                contract_id,
                reference,
                candidate,
                seed=seed,
                samples=fuzz_samples,
            ),
            MethodEvidence(
                method="lean-proof",
                candidate_passed=False,
                samples=1,
                scope=f"Machine-checked counterexample: {fault['witness_theorem']}",
                failing_inputs=(),
            ),
        )
        comparisons.append(
            CandidateComparison(
                fault_id=fault["fault_id"],
                contract_id=contract_id,
                witness_theorem=fault["witness_theorem"],
                methods=methods,
            )
        )
    toolchain_path = Path("lean-toolchain")
    lean_toolchain = (
        toolchain_path.read_text(encoding="utf-8").strip()
        if toolchain_path.is_file()
        else "unknown"
    )
    return ComparisonReport(
        seed,
        fuzz_samples,
        {
            "python": platform.python_version(),
            "hypothesis": version("hypothesis"),
            "lean_toolchain": lean_toolchain,
        },
        tuple(comparisons),
    )


def write_comparison_report(report: ComparisonReport, output_directory: str | Path) -> None:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    (output / "comparison.json").write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Evidence method comparison",
        "",
        f"- Seed: {report.seed}",
        f"- Fuzz samples per candidate: {report.fuzz_samples}",
        f"- Weak-test false negatives: {report.weak_false_negatives}",
        f"- Python: {report.tool_versions['python']}",
        f"- Hypothesis: {report.tool_versions['hypothesis']}",
        f"- Lean toolchain: {report.tool_versions['lean_toolchain']}",
        "",
    ]
    for candidate in report.candidates:
        lines.extend(
            [
                f"## {candidate.fault_id}",
                "",
                f"- Contract: {candidate.contract_id}",
                f"- Witness: {candidate.witness_theorem}",
                f"- Weak false negative: {candidate.weak_false_negative}",
                "",
                "| Method | Candidate passed | Samples | Scope |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for method in candidate.methods:
            lines.append(
                f"| {method.method} | {method.candidate_passed} | "
                f"{method.samples} | {method.scope} |"
            )
        lines.append("")
    (output / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
