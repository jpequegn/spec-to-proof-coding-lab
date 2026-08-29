# Spec-to-Proof Coding Lab

A local learning project for turning small function contracts into Lean 4 specifications, candidate implementations, and machine-checked proofs.

## Scope

The lab uses pure toy functions and synthetic contracts. Lean owns proof verification; Python handles contract fixtures, comparison experiments, and reports. Model-assisted contract generation is intentionally absent from V1.

Proof establishes the encoded theorem. It does not establish that the theorem captures the intended real-world requirement.

## Architecture

~~~text
contract fixture -> review -> Lean specification -> implementation -> proof
       |                                                  |
       +-> Python examples, properties, and fuzzing       +-> proof receipt
~~~

## Development

Requires Lean 4.33.1 through Elan, Python 3.12, and uv.

~~~bash
lake build
uv sync --all-groups --locked --no-editable
uv run ruff check .
uv run pytest
~~~

Source project: https://github.com/jpequegn/project-ideas/issues/259
