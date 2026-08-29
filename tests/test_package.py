from spec_to_proof import __version__
from spec_to_proof.cli import main


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_empty_cli_succeeds() -> None:
    assert main([]) == 0
