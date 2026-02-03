from unittest.mock import patch, MagicMock
from jmcp.tools import code_search


def test_code_search_git_not_found():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = code_search.execute("some_func")
        assert "Error: git command not found" in result


def test_code_search_no_matches():
    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stdout = ""

    with patch("subprocess.run", return_value=mock_run):
        result = code_search.execute("missing_func")
        assert "No symbol named 'missing_func' found" in result


def test_code_search_success():
    mock_run = MagicMock()
    mock_run.returncode = 0
    # Simulate git grep -W output
    # format: file:line:content
    mock_run.stdout = """file.py:10:def target_func():
file.py-11-    print("hello")
file.py-12-    return True
"""

    with patch("subprocess.run", return_value=mock_run):
        result = code_search.execute("target_func")
        assert "File: file.py:10" in result
        assert "def target_func():" in result
        assert 'print("hello")' in result
