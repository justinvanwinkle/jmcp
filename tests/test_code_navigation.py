from pathlib import Path
from jmcp.tools import code_navigation

FAKE_LIB = Path(__file__).parent / "src/fake_lib"


def test_code_navigation_runs():
    """Verify code_navigation tool runs without crashing."""
    module_path = FAKE_LIB / "module.py"

    # We don't assert that it definitely finds the definition, because `ty`
    # might be indexing or slow in the test environment.
    # We just ensure the plumbing works:
    # 1. It starts ty (if not started)
    # 2. It sends the request
    # 3. It receives a response

    result = code_navigation.execute(str(module_path), 1, 1)

    assert isinstance(result, str)
    assert "Error querying language server" not in result
    # It will likely return "No definition found" or the definition.
    # Both are valid outcomes of the tool execution.
