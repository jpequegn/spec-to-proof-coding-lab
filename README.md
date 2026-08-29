# Spec-to-Proof Coding Lab

A runnable Lean 4 and Python lab for turning reviewed function contracts into
specifications, machine-checked proofs, comparison evidence, and tamper-evident receipts.

The corpus covers saturating addition, clamping, list transformation, pair ordering, and
strict binary-digit parsing. It also includes three faulty candidates with checked
counterexamples.

## Quick Start

Requires [Elan](https://github.com/leanprover/elan), Python 3.12, and
[uv](https://docs.astral.sh/uv/). The repository pins Lean 4.33.1.

```bash
uv sync --all-groups --locked --no-editable
lake build
uv run spec-to-proof demo
```

The demo validates five contracts, builds and checks their Lean theorems, compares three
faulty candidates across examples, properties, fuzzing, and proof evidence, then writes:

```text
artifacts/demo/
  boundary.py
  comparison/comparison.{json,md}
  receipts/manifest.{json,md}
  receipts/<contract>.{json,md}
  summary.json
```

Inspect or run one stage independently:

```bash
uv run spec-to-proof list
uv run spec-to-proof validate
uv run spec-to-proof inspect parse-bit
uv run spec-to-proof render parse-bit
uv run spec-to-proof compare
uv run spec-to-proof boundary
uv run spec-to-proof receipts generate
uv run spec-to-proof receipts verify
```

## What It Demonstrates

```text
reviewed JSON contract -> deterministic Lean proposition -> Lean implementation + theorem
          |                         |                              |
          +-> Python boundary       +-> review checkpoint          +-> proof receipt
          +-> examples / properties / seeded fuzzing               +-> checked witness
```

The parser experiment is the key result: its legacy examples, output-bound property, and
seeded fuzz corpus all accept a faulty leading-zero parser. Lean checks the explicit
`"01"` counterexample and rejects the candidate.

Proof correctness is not specification adequacy. Lean establishes the encoded theorem for
the Lean definition under its assumptions; it does not establish that the contract captures
the user's intent or that the generated Python boundary is equivalent to the Lean code.

See [architecture](docs/ARCHITECTURE.md), [proof scope](docs/PROOF_SCOPE.md), and
[capabilities and extensions](docs/CAPABILITIES.md).

## Release Checks

```bash
uv run ruff check .
uv run coverage run -m pytest
uv run coverage report --fail-under=85
uv build
lake build
lake env leanchecker SpecToProof
uv run spec-to-proof demo
```

Source project: https://github.com/jpequegn/project-ideas/issues/259
