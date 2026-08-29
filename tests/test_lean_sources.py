import re
from pathlib import Path

from spec_to_proof.contracts import load_contract_directory

LEAN_SOURCES = tuple(sorted(Path("SpecToProof").glob("*.lean")))
FORBIDDEN = re.compile(r"\b(sorry|admit|axiom|unsafe)\b")


def test_lean_corpus_has_no_proof_escape_hatches() -> None:
    violations = {
        str(path): FORBIDDEN.findall(path.read_text(encoding="utf-8"))
        for path in LEAN_SOURCES
        if FORBIDDEN.search(path.read_text(encoding="utf-8"))
    }
    assert violations == {}


def test_every_contract_theorem_is_declared() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in LEAN_SOURCES)
    missing = []
    for contract in load_contract_directory("contracts"):
        for theorem_name in contract.theorem_names:
            declaration = theorem_name.removeprefix("SpecToProof.")
            if re.search(rf"\btheorem\s+{re.escape(declaration)}\b", source) is None:
                missing.append(theorem_name)
    assert missing == []


def test_corpus_spans_required_domains() -> None:
    names = {path.name for path in LEAN_SOURCES}
    assert {"Arithmetic.lean", "Lists.lean", "Ordering.lean", "Parsing.lean"} <= names
