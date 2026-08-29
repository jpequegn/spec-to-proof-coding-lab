# Architecture

The lab keeps review, verification, and runtime adaptation separate.

1. `contracts/*.json` records versioned intent, examples, theorem links, assumptions, and
   non-goals. Validation rejects ambiguous, contradictory, vacuous, or malformed contracts.
2. `templates.py` deterministically renders a review skeleton. It does not generate a proof.
3. `SpecToProof/*.lean` contains the reviewed definitions, theorems, and faulty witnesses.
4. `comparison.py` evaluates intentionally faulty candidates with four independent evidence
   methods. Each method reports its own scope and result.
5. `receipts.py` rebuilds Lean, checks theorem names, hashes the contract and relevant source,
   and records assumptions and non-goals. Verification rejects stale or changed inputs.
6. `boundary.py` generates a small Python adapter with contract hashes and explicit examples.
7. `demo.py` orchestrates the complete path without hiding intermediate artifacts.

## Trust Boundaries

Lean owns theorem checking. Python owns contract parsing, experiment orchestration, hashing,
and report generation. Receipt hashes detect change but are not signatures; an authenticated
release process should sign the manifest or store it in a transparency log.

The Python boundary uses hand-reviewed reference functions. Its examples are checked against
the contract fixtures, but no theorem currently proves semantic equivalence between those
Python functions and the Lean definitions.
