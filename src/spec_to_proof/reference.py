"""Python reference and intentionally faulty implementations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def saturating_add(left: int, right: int, cap: int) -> int:
    return min(left + right, cap)


def faulty_saturating_add(left: int, right: int, cap: int) -> int:
    return min(left + right, cap + 1)


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def faulty_clamp(value: int, lower: int, upper: int) -> int:
    return min(value, upper)


def parse_bit(value: str) -> int | None:
    if value == "0":
        return 0
    if value == "1":
        return 1
    return None


def faulty_parse_bit(value: str) -> int | None:
    if value == "01":
        return 1
    return parse_bit(value)


ReferenceFunction = Callable[..., Any]

REFERENCE_FUNCTIONS: dict[str, ReferenceFunction] = {
    "saturating-add": saturating_add,
    "clamp": clamp,
    "parse-bit": parse_bit,
}

FAULTY_FUNCTIONS: dict[str, ReferenceFunction] = {
    "saturating-add-off-by-one": faulty_saturating_add,
    "clamp-missing-lower-bound": faulty_clamp,
    "parse-bit-leading-zero": faulty_parse_bit,
}
