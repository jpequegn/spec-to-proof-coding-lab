"""Command-line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="spec-to-proof",
        description="Review contracts and machine-checked proof evidence.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0
