"""Deterministic Lean proposition templates for reviewed contracts."""

from __future__ import annotations

from dataclasses import dataclass

from spec_to_proof.contracts import ContractDiagnostic, ContractError, FunctionContract


@dataclass(frozen=True, slots=True)
class SpecTemplate:
    contract_id: str
    theorem_names: tuple[str, ...]
    declaration: str


TEMPLATES = {
    "saturating-add": SpecTemplate(
        contract_id="saturating-add",
        theorem_names=(
            "SpecToProof.saturatingAdd_eq_min",
            "SpecToProof.saturatingAdd_le_cap",
        ),
        declaration="""def SaturatingAddContract
    (implementation : Nat -> Nat -> Nat -> Nat) : Prop :=
  And
    (forall left right cap,
      implementation left right cap = min (left + right) cap)
    (forall left right cap,
      implementation left right cap <= cap)""",
    ),
    "clamp": SpecTemplate(
        contract_id="clamp",
        theorem_names=(
            "SpecToProof.clamp_lower",
            "SpecToProof.clamp_upper",
            "SpecToProof.clamp_eq_self",
        ),
        declaration="""def ClampContract
    (implementation : Nat -> Nat -> Nat -> Nat) : Prop :=
  forall value lower upper,
    lower <= upper ->
    And
      (lower <= implementation value lower upper)
      (And
        (implementation value lower upper <= upper)
        (lower <= value ->
          value <= upper ->
          implementation value lower upper = value))""",
    ),
    "increment-all": SpecTemplate(
        contract_id="increment-all",
        theorem_names=(
            "SpecToProof.incrementAll_eq_map",
            "SpecToProof.incrementAll_length",
        ),
        declaration="""def IncrementAllContract
    (implementation : List Nat -> List Nat) : Prop :=
  forall values,
    And
      (implementation values = values.map (fun value => value + 1))
      ((implementation values).length = values.length)""",
    ),
    "sort-pair": SpecTemplate(
        contract_id="sort-pair",
        theorem_names=(
            "SpecToProof.sortPair_ordered",
            "SpecToProof.sortPair_sum",
        ),
        declaration="""def SortPairContract
    (implementation : Nat -> Nat -> Prod Nat Nat) : Prop :=
  forall left right,
    And
      ((implementation left right).1 <= (implementation left right).2)
      ((implementation left right).1 + (implementation left right).2 =
        left + right)""",
    ),
    "parse-bit": SpecTemplate(
        contract_id="parse-bit",
        theorem_names=(
            "SpecToProof.parseBit_zero",
            "SpecToProof.parseBit_one",
            "SpecToProof.parseBit_sound",
        ),
        declaration="""def ParseBitContract
    (implementation : String -> Option Nat) : Prop :=
  And
    (implementation "0" = some 0)
    (And
      (implementation "1" = some 1)
      (forall input value,
        implementation input = some value -> value <= 1))""",
    ),
}


def _comment_lines(label: str, values: tuple[str, ...]) -> list[str]:
    return [
        f"-- {label}: {' '.join(value.split())}"
        for value in values
    ]


def render_spec_skeleton(contract: FunctionContract) -> str:
    template = TEMPLATES.get(contract.contract_id)
    if template is None:
        raise ContractError(
            ContractDiagnostic(
                code="CONTRACT_TEMPLATE_MISSING",
                message=f"No deterministic template for {contract.contract_id}",
                contract_id=contract.contract_id,
            )
        )
    if template.theorem_names != contract.theorem_names:
        raise ContractError(
            ContractDiagnostic(
                code="CONTRACT_TEMPLATE_DRIFT",
                message="Template theorem links differ from the reviewed contract",
                contract_id=contract.contract_id,
                field="theorem_names",
            )
        )

    lines = [
        "-- GENERATED REVIEW SKELETON. NO PROOF BODY IS INCLUDED.",
        f"-- contract-id: {contract.contract_id}",
        f"-- contract-sha256: {contract.contract_hash}",
        f"-- input-type: {contract.input_type}",
        f"-- output-type: {contract.output_type}",
        *_comment_lines("precondition", contract.preconditions),
        *_comment_lines("postcondition", contract.postconditions),
        *_comment_lines("invariant", contract.invariants),
        *_comment_lines("non-goal", contract.non_goals),
        *_comment_lines("ambiguity", contract.ambiguity_notes),
        *[f"-- required-theorem: {name}" for name in contract.theorem_names],
        "",
        "namespace SpecToProof",
        "",
        template.declaration,
        "",
        "end SpecToProof",
        "",
    ]
    return "\n".join(lines)
