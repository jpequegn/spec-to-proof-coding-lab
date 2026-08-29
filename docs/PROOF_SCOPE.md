# Proof Scope

## What Is Proved

- Saturating addition equals `min (left + right) cap` and never exceeds the cap.
- Clamp respects its lower bound, respects its upper bound when the interval is valid, and
  preserves values already inside the interval.
- Increment-all equals mapping addition by one and preserves list length.
- Sort-pair returns an ordered pair with the same sum.
- Parse-bit accepts zero and one and never returns a value above one.
- Three concrete faulty candidates have machine-checked defect witnesses.

## What Remains Assumed

- The pinned Lean compiler, kernel, operating environment, and hardware execute correctly.
- Contract preconditions hold when a theorem requires them, notably `lower <= upper` for clamp.
- Human-readable requirements were translated into the intended formal statements.
- Python and Lean implementations correspond; V1 checks shared examples but does not prove
  cross-language equivalence.

## What Is Not Proved

- The contracts are adequate for a production requirement.
- Examples or properties are exhaustive.
- Receipt hashes provide authorship or resistance to a party that can rewrite all artifacts.
- Performance, side-channel behavior, machine-integer overflow, or foreign-runtime behavior.

Proof correctness and specification adequacy are different review gates. A theorem may be
perfectly proved and still encode the wrong requirement. Contract review therefore remains a
required step before proof evidence is accepted.
