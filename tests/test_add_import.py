import textwrap

import pytest

from jmcp.tools.add_import import (
    _add_imports_to_source,
    _parse_import_statement,
    _resolve_file_patterns,
    execute,
)


class TestParseImportStatement:
    def test_simple_import(self):
        entries = _parse_import_statement("import sys")
        assert entries == [{"module": "sys", "obj": None, "asname": None, "relative": 0}]

    def test_dotted_import(self):
        entries = _parse_import_statement("import os.path")
        assert entries == [{"module": "os.path", "obj": None, "asname": None, "relative": 0}]

    def test_from_import(self):
        entries = _parse_import_statement("from os.path import join")
        assert entries == [{"module": "os.path", "obj": "join", "asname": None, "relative": 0}]

    def test_from_import_multiple(self):
        entries = _parse_import_statement("from os.path import join, exists")
        assert len(entries) == 2
        assert entries[0]["obj"] == "join"
        assert entries[1]["obj"] == "exists"
        assert all(e["module"] == "os.path" for e in entries)

    def test_import_with_alias(self):
        entries = _parse_import_statement("import numpy as np")
        assert entries == [{"module": "numpy", "obj": None, "asname": "np", "relative": 0}]

    def test_from_import_with_alias(self):
        entries = _parse_import_statement("from collections import defaultdict as dd")
        assert entries == [
            {"module": "collections", "obj": "defaultdict", "asname": "dd", "relative": 0}
        ]

    def test_relative_import(self):
        entries = _parse_import_statement("from ..core import base")
        assert entries == [{"module": "core", "obj": "base", "asname": None, "relative": 2}]

    def test_relative_import_dot_only(self):
        entries = _parse_import_statement("from . import utils")
        assert entries == [{"module": "", "obj": "utils", "asname": None, "relative": 1}]

    def test_star_import_rejected(self):
        with pytest.raises(ValueError, match="Star imports not supported"):
            _parse_import_statement("from os import *")

    def test_invalid_syntax(self):
        with pytest.raises(ValueError, match="Invalid import statement"):
            _parse_import_statement("def foo(:")

    def test_non_import_statement(self):
        with pytest.raises(ValueError, match="Not an import statement"):
            _parse_import_statement("this is not python")

    def test_not_an_import(self):
        with pytest.raises(ValueError, match="Not an import statement"):
            _parse_import_statement("x = 1")


class TestAddImportsToSource:
    def test_adds_simple_import(self):
        source = "x = 1\n"
        entries = [{"module": "sys", "obj": None, "asname": None, "relative": 0}]
        result = _add_imports_to_source(source, entries)
        assert "import sys" in result
        assert "x = 1" in result

    def test_adds_from_import(self):
        source = "x = 1\n"
        entries = [{"module": "os.path", "obj": "join", "asname": None, "relative": 0}]
        result = _add_imports_to_source(source, entries)
        assert "from os.path import join" in result

    def test_skips_existing_import(self):
        source = "import sys\n\nx = 1\n"
        entries = [{"module": "sys", "obj": None, "asname": None, "relative": 0}]
        result = _add_imports_to_source(source, entries)
        assert result == source

    def test_multiple_imports(self):
        source = "x = 1\n"
        entries = [
            {"module": "sys", "obj": None, "asname": None, "relative": 0},
            {"module": "os.path", "obj": "join", "asname": None, "relative": 0},
        ]
        result = _add_imports_to_source(source, entries)
        assert "import sys" in result
        assert "from os.path import join" in result

    def test_preserves_existing_code(self):
        source = textwrap.dedent("""\
            import os

            def foo():
                return os.getcwd()
        """)
        entries = [{"module": "sys", "obj": None, "asname": None, "relative": 0}]
        result = _add_imports_to_source(source, entries)
        assert "import os" in result
        assert "import sys" in result
        assert "def foo():" in result
        assert "return os.getcwd()" in result


class TestResolveFilePatterns:
    def test_literal_path(self, tmp_path):
        f = tmp_path / "foo.py"
        f.write_text("x = 1\n")
        result = _resolve_file_patterns(["foo.py"], tmp_path)
        assert result == [f]

    def test_literal_path_missing(self, tmp_path):
        result = _resolve_file_patterns(["nope.py"], tmp_path)
        assert result == []

    def test_glob_pattern(self, tmp_path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        a = sub / "alpha.py"
        b = sub / "beta.py"
        a.write_text("a = 1\n")
        b.write_text("b = 2\n")
        (sub / "readme.txt").write_text("hi")
        result = _resolve_file_patterns(["pkg/*.py"], tmp_path)
        assert set(result) == {a, b}

    def test_recursive_glob(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        f = deep / "mod.py"
        f.write_text("x = 1\n")
        result = _resolve_file_patterns(["**/*.py"], tmp_path)
        assert f in result

    def test_regex_pattern(self, tmp_path):
        sub = tmp_path / "models"
        sub.mkdir()
        a = sub / "user.py"
        b = sub / "order.py"
        a.write_text("a = 1\n")
        b.write_text("b = 2\n")
        (tmp_path / "views.py").write_text("v = 1\n")
        result = _resolve_file_patterns([r"re:models/.*\.py$"], tmp_path)
        assert set(result) == {a, b}

    def test_mixed_patterns(self, tmp_path):
        f1 = tmp_path / "direct.py"
        f1.write_text("x = 1\n")
        sub = tmp_path / "pkg"
        sub.mkdir()
        f2 = sub / "mod.py"
        f2.write_text("y = 2\n")
        result = _resolve_file_patterns(["direct.py", "pkg/*.py"], tmp_path)
        assert set(result) == {f1, f2}

    def test_non_py_files_excluded_from_glob(self, tmp_path):
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "code.py").write_text("x = 1\n")
        result = _resolve_file_patterns(["*"], tmp_path)
        assert all(p.suffix == ".py" for p in result)


class TestExecute:
    def test_add_single_import_to_single_file(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1\n")
        result = execute(["import sys"], ["target.py"], root_path=tmp_path)
        assert "added imports" in result
        content = f.read_text()
        assert "import sys" in content
        assert "x = 1" in content

    def test_add_multiple_imports(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1\n")
        result = execute(
            ["import sys", "from os.path import join"],
            ["target.py"],
            root_path=tmp_path,
        )
        assert "added imports" in result
        content = f.read_text()
        assert "import sys" in content
        assert "from os.path import join" in content

    def test_add_imports_to_multiple_files(self, tmp_path):
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        a.write_text("x = 1\n")
        b.write_text("y = 2\n")
        result = execute(["import sys"], ["a.py", "b.py"], root_path=tmp_path)
        assert "a.py: added imports" in result
        assert "b.py: added imports" in result
        assert "import sys" in a.read_text()
        assert "import sys" in b.read_text()

    def test_idempotent(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("import sys\n\nx = 1\n")
        result = execute(["import sys"], ["target.py"], root_path=tmp_path)
        assert "no changes" in result
        assert f.read_text() == "import sys\n\nx = 1\n"

    def test_glob_targeting(self, tmp_path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        a = sub / "a.py"
        b = sub / "b.py"
        a.write_text("x = 1\n")
        b.write_text("y = 2\n")
        result = execute(["import sys"], ["pkg/*.py"], root_path=tmp_path)
        assert "added imports" in result
        assert "import sys" in a.read_text()
        assert "import sys" in b.read_text()

    def test_regex_targeting(self, tmp_path):
        sub = tmp_path / "models"
        sub.mkdir()
        f = sub / "user.py"
        f.write_text("x = 1\n")
        other = tmp_path / "views.py"
        other.write_text("y = 2\n")
        result = execute(
            ["import sys"],
            [r"re:models/.*\.py$"],
            root_path=tmp_path,
        )
        assert "added imports" in result
        assert "import sys" in f.read_text()
        assert "import sys" not in other.read_text()

    def test_no_files_matched(self, tmp_path):
        result = execute(["import sys"], ["nonexistent/*.py"], root_path=tmp_path)
        assert "No files matched" in result

    def test_invalid_import_string(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1\n")
        result = execute(["not valid python"], ["target.py"], root_path=tmp_path)
        assert "Error parsing import" in result

    def test_preserves_formatting(self, tmp_path):
        source = textwrap.dedent("""\
            import os

            # Important comment
            def foo():
                return os.getcwd()
        """)
        f = tmp_path / "target.py"
        f.write_text(source)
        execute(["import sys"], ["target.py"], root_path=tmp_path)
        content = f.read_text()
        assert "# Important comment" in content
        assert "def foo():" in content
        assert "return os.getcwd()" in content

    def test_from_import_with_multiple_names(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1\n")
        execute(["from os.path import join, exists"], ["target.py"], root_path=tmp_path)
        content = f.read_text()
        assert "join" in content
        assert "exists" in content

    def test_aliased_import(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1\n")
        execute(["import numpy as np"], ["target.py"], root_path=tmp_path)
        content = f.read_text()
        assert "import numpy as np" in content

    def test_unparseable_target_file(self, tmp_path):
        f = tmp_path / "broken.py"
        f.write_text("def foo(\n")
        result = execute(["import sys"], ["broken.py"], root_path=tmp_path)
        assert "parse error" in result
