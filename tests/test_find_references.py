from pathlib import Path

from jmcp.tools import find_references

FAKE_LIB = Path(__file__).parent / "src/fake_lib"


def test_find_references_runs():
    """Verify find_references tool runs without crashing."""
    nested_path = FAKE_LIB / "deep/nested.py"

    # The body of deep_func starts at line 1; the name `deep_func` is on
    # line 1, column 4.
    result = find_references.execute(
        str(nested_path), 1, 4, include_declaration=True
    )

    assert isinstance(result, str)
    assert "Error querying language server" not in result
    # Server may need indexing time; either it returns refs or "No references found".
    # Both are valid outcomes for the plumbing test.
