# Capabilities and Extensions

## Practical Uses

- Learn the contract-to-theorem workflow on functions small enough to inspect completely.
- Compare what examples, bounded properties, seeded fuzzing, and formal proofs each establish.
- Reproduce a weak-test false negative with a deterministic parser experiment.
- Generate receipts that bind proof claims to exact contracts, Lean sources, and tool versions.
- Use the generated Python boundary as a reviewable integration example.

## Usage Pattern

1. Add or revise a contract and resolve every ambiguity note.
2. Render and review the Lean proposition skeleton.
3. Implement the Lean function and theorem without weakening the contract.
4. Add faulty candidates or mutation cases that challenge the evidence methods.
5. Run `spec-to-proof demo`, review comparison scope, and archive or sign the receipts.

## Extension Paths

- Generate Rust or WebAssembly from Lean and prove the extraction path used by production.
- Add mutation testing that automatically searches for candidates surviving the current tests.
- Sign receipt manifests with Sigstore and publish them to a transparency log.
- Attach proof receipts to CI provenance and software bills of materials.
- Add an LLM contract-drafting stage whose output cannot proceed until ambiguity and adequacy
  reviews pass.
- Build a differential semantic checker between Lean execution and a foreign-language runtime.
- Extend the corpus to state machines, parsers, authorization rules, and financial invariants.

An innovative application is a proof-carrying code review bot: generated patches would include
a narrow contract, executable examples, mutation results, and a signed receipt. Reviewers could
then distinguish specification decisions from implementation correctness in the PR itself.
