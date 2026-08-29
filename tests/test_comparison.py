import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from spec_to_proof.cli import main
from spec_to_proof.comparison import run_comparison
from spec_to_proof.reference import (
    clamp,
    faulty_parse_bit,
    parse_bit,
    saturating_add,
)


@given(
    left=st.integers(min_value=0, max_value=10_000),
    right=st.integers(min_value=0, max_value=10_000),
    cap=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=100, derandomize=True)
def test_saturating_add_property(left: int, right: int, cap: int) -> None:
    result = saturating_add(left, right, cap)
    assert result <= cap
    assert result == min(left + right, cap)


@given(
    value=st.integers(min_value=0, max_value=10_000),
    bounds=st.tuples(
        st.integers(min_value=0, max_value=10_000),
        st.integers(min_value=0, max_value=10_000),
    ),
)
@settings(max_examples=100, derandomize=True)
def test_clamp_property(value: int, bounds: tuple[int, int]) -> None:
    lower, upper = sorted(bounds)
    assert lower <= clamp(value, lower, upper) <= upper


@given(st.sampled_from(["", "0", "1", "00", "10", "11", "2", "x"]))
@settings(max_examples=50, derandomize=True)
def test_weak_parser_property_misses_leading_zero(value: str) -> None:
    result = faulty_parse_bit(value)
    assert result is None or result <= 1
    assert result == parse_bit(value)


def test_formal_witness_exposes_weak_test_false_negative() -> None:
    report = run_comparison(seed=259, fuzz_samples=100)
    parser = next(
        candidate
        for candidate in report.candidates
        if candidate.fault_id == "parse-bit-leading-zero"
    )

    assert [method.candidate_passed for method in parser.methods] == [
        True,
        True,
        True,
        False,
    ]
    assert parser.weak_false_negative
    assert report.weak_false_negatives == 1


def test_comparison_is_reproducible() -> None:
    first = run_comparison(seed=259, fuzz_samples=50)
    second = run_comparison(seed=259, fuzz_samples=50)
    assert first.as_dict() == second.as_dict()


def test_cli_writes_reports(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "comparison"
    assert main(["compare", "--output", str(output)]) == 0
    assert "weak-test false negatives: 1" in capsys.readouterr().out

    payload = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
    markdown = (output / "comparison.md").read_text(encoding="utf-8")
    assert payload["weak_false_negatives"] == 1
    assert payload["tool_versions"]["lean_toolchain"] == "leanprover/lean4:v4.33.1"
    assert "parse-bit-leading-zero" in markdown
