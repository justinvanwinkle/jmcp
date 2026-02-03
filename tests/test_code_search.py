from pathlib import Path
from jmcp.tools import code_search

# Path to fake lib
FAKE_LIB = Path(__file__).parent / "src"


def test_code_search_hello():
    result = code_search.execute("hello", root_path=FAKE_LIB)
    assert "File: fake_lib/module.py" in result
    assert "def hello(name):" in result
    assert 'print(f"Hello {name}")' in result


def test_code_search_class():
    result = code_search.execute("Greeter", root_path=FAKE_LIB)
    assert "class Greeter:" in result
    assert "def greet(self):" in result


def test_code_search_method():
    # git grep -W might return the class containing the method
    result = code_search.execute("greet", root_path=FAKE_LIB)
    # It should find Greeter.greet
    assert "def greet(self):" in result


def test_code_search_deep():
    result = code_search.execute("deep_func", root_path=FAKE_LIB)
    assert "fake_lib/deep/nested.py" in result
    assert "def deep_func():" in result


def test_code_search_missing():
    result = code_search.execute("missing_thing", root_path=FAKE_LIB)
    assert "No symbol named 'missing_thing' found" in result
