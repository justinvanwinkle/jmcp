import re
from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor

TOOL_DEF = {
    "name": "add_import",
    "description": (
        "Add one or more import statements to one or more Python files. "
        "Files can be specified as literal paths, extended globs (e.g. 'src/**/*.py'), "
        "or regex patterns prefixed with 're:' (e.g. 're:models/.*\\.py$'). "
        "Imports are specified as Python import statement strings "
        "(e.g. 'from os.path import join', 'import sys'). "
        "Already-present imports are skipped. File contents are preserved via CST transformation."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "imports": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of Python import statements to add, e.g. "
                    "['import sys', 'from os.path import join']"
                ),
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of file targets. Each entry can be: "
                    "a literal path ('src/foo.py'), "
                    "an extended glob ('src/**/*.py'), "
                    "or a regex prefixed with 're:' ('re:.*_test\\.py$')"
                ),
            },
        },
        "required": ["imports", "files"],
    },
}

GLOB_CHARS = {"*", "?", "["}


def _is_glob(pattern: str) -> bool:
    return any(c in pattern for c in GLOB_CHARS)


def _resolve_file_patterns(patterns: list[str], cwd: Path) -> list[Path]:
    """Resolve a mix of literal paths, globs, and regex patterns to concrete file paths."""
    resolved = set()
    for pattern in patterns:
        if pattern.startswith("re:"):
            regex = re.compile(pattern[3:])
            for path in cwd.rglob("*.py"):
                rel = str(path.relative_to(cwd))
                if regex.search(rel):
                    resolved.add(path)
        elif _is_glob(pattern):
            for path in cwd.glob(pattern):
                if path.is_file() and path.suffix == ".py":
                    resolved.add(path)
        else:
            path = cwd / pattern if not Path(pattern).is_absolute() else Path(pattern)
            if path.is_file():
                resolved.add(path)
    return sorted(resolved)


def _parse_import_statement(stmt: str) -> list[dict]:
    """Parse an import statement string into dicts suitable for AddImportsVisitor.add_needed_import.

    Returns a list because 'from X import a, b' yields multiple entries.
    Each dict has keys: module, obj, asname, relative.
    """
    try:
        tree = cst.parse_module(stmt)
    except cst.ParserSyntaxError as e:
        raise ValueError(f"Invalid import statement: {stmt!r}") from e

    if len(tree.body) != 1:
        raise ValueError(f"Expected exactly one statement, got {len(tree.body)}: {stmt!r}")

    node = tree.body[0]
    if not isinstance(node, cst.SimpleStatementLine):
        raise ValueError(f"Not a simple statement: {stmt!r}")

    imp = node.body[0]
    entries = []

    if isinstance(imp, cst.Import):
        if isinstance(imp.names, cst.ImportStar):
            raise ValueError(f"Star imports not supported: {stmt!r}")
        for alias in imp.names:
            module = tree.code_for_node(alias.name).strip()
            asname = tree.code_for_node(alias.asname.name).strip() if alias.asname else None
            entries.append({"module": module, "obj": None, "asname": asname, "relative": 0})

    elif isinstance(imp, cst.ImportFrom):
        module = tree.code_for_node(imp.module).strip() if imp.module else ""
        relative = len(imp.relative) if imp.relative else 0

        if isinstance(imp.names, cst.ImportStar):
            raise ValueError(f"Star imports not supported: {stmt!r}")
        for alias in imp.names:
            obj = tree.code_for_node(alias.name).strip()
            asname = tree.code_for_node(alias.asname.name).strip() if alias.asname else None
            entries.append({"module": module, "obj": obj, "asname": asname, "relative": relative})
    else:
        raise ValueError(f"Not an import statement: {stmt!r}")

    return entries


def _add_imports_to_source(source: str, import_entries: list[dict]) -> str:
    """Add imports to source code using libcst. Returns modified source."""
    context = CodemodContext()
    for entry in import_entries:
        kwargs = {"module": entry["module"]}
        if entry["obj"]:
            kwargs["obj"] = entry["obj"]
        if entry["asname"]:
            kwargs["asname"] = entry["asname"]
        if entry["relative"]:
            kwargs["relative"] = entry["relative"]
        AddImportsVisitor.add_needed_import(context, **kwargs)

    tree = cst.parse_module(source)
    modified = tree.visit(AddImportsVisitor(context))
    return modified.code


def execute(imports: list[str], files: list[str], root_path: Path | None = None) -> str:
    cwd = root_path or Path.cwd()

    all_entries = []
    for stmt in imports:
        try:
            entries = _parse_import_statement(stmt)
        except ValueError as e:
            return f"Error parsing import: {e}"
        all_entries.extend(entries)

    if not all_entries:
        return "Error: no valid imports to add."

    resolved_files = _resolve_file_patterns(files, cwd)
    if not resolved_files:
        return f"No files matched patterns: {files}"

    results = []
    errors = []
    for path in resolved_files:
        try:
            source = path.read_text()
        except OSError as e:
            errors.append(f"{path}: read error: {e}")
            continue

        try:
            modified = _add_imports_to_source(source, all_entries)
        except cst.ParserSyntaxError as e:
            errors.append(f"{path}: parse error: {e}")
            continue

        if modified == source:
            results.append(f"{path.relative_to(cwd)}: no changes (imports already present)")
        else:
            path.write_text(modified)
            results.append(f"{path.relative_to(cwd)}: added imports")

    output = "\n".join(results)
    if errors:
        output += "\n\nErrors:\n" + "\n".join(errors)
    return output
