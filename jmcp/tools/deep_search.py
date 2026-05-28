import io
import keyword
import logging
import re
import tokenize
from pathlib import Path
from urllib.parse import unquote, urlparse

from jmcp.tools.code_search import MAX_LINES, _extract_body, _parse_grep_output, _run_grep

logger = logging.getLogger(__name__)

TOOL_DEF = {
    "name": "deep_search",
    "description": (
        "Search for a function or class by name, then resolve all symbols "
        "used in its body to their definitions via the language server."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the function or class to find",
            },
        },
        "required": ["name"],
    },
}

SKIP_NAMES = frozenset({"self", "cls", "True", "False", "None"})


def _uri_to_path(uri: str) -> Path:
    return Path(unquote(urlparse(uri).path))


def _find_definitions(name: str, cwd: Path) -> list[dict]:
    result = _run_grep(name, cwd)
    if result.returncode != 0:
        return []
    parsed = _parse_grep_output(result.stdout)
    defs = []
    i = 0
    while i < len(parsed):
        item = parsed[i]
        if item["is_match"] and re.search(
            rf"^\s*(class|def)\s+{re.escape(name)}\b", item["content"]
        ):
            body, _ = _extract_body(parsed, i)
            defs.append(
                {
                    "file": item["file"],
                    "line": item["line"],
                    "body": body,
                }
            )
        i += 1
    return defs


def _tokenize_names(source: str) -> list[tuple[str, int, int]]:
    """Extract (name, 1-based line, 0-based col) for non-keyword NAME tokens."""
    results = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if (
                tok.type == tokenize.NAME
                and not keyword.iskeyword(tok.string)
                and tok.string not in SKIP_NAMES
            ):
                results.append((tok.string, tok.start[0], tok.start[1]))
    except tokenize.TokenError:
        pass
    return results


def _read_definition_body(path: Path, start_line: int) -> str:
    """Read an indentation-scoped block starting at start_line (0-based)."""
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return ""

    if start_line >= len(lines):
        return ""

    first_line = lines[start_line]
    indent_match = re.match(r"^(\s*)", first_line)
    base_indent = len(indent_match.group(1)) if indent_match else 0

    body = [first_line]
    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            body.append(line)
            continue
        m = re.match(r"^(\s*)", line)
        line_indent = len(m.group(1)) if m else 0
        if line_indent > base_indent:
            body.append(line)
        else:
            break

    if len(body) > MAX_LINES:
        body = body[:MAX_LINES]
        body.append(f"... (truncated {len(body) - MAX_LINES} more lines) ...")

    return "\n".join(body)


def _resolve_location(loc: dict) -> tuple[Path, int, int] | None:
    uri = loc.get("uri") or loc.get("targetUri")
    range_ = loc.get("range") or loc.get("targetSelectionRange") or loc.get("targetRange")
    if not uri or not range_:
        return None
    return _uri_to_path(uri), range_["start"]["line"], range_["end"]["line"]


def _collect_resolved_definitions(
    client,
    names: list[tuple[str, int, int]],
    name: str,
    file_path: str,
    start_line: int,
    body_line_count: int,
    project_root: Path,
    cwd: Path,
) -> list[str]:
    seen = set()
    resolved = []

    for tok_name, tok_line, tok_col in names:
        if tok_name == name:
            continue

        # tok_line is 1-based within the snippet, start_line is 1-based in file
        lsp_line = start_line + tok_line - 2  # to 0-based

        try:
            result = client.goto_definition(file_path, lsp_line, tok_col)
        except TimeoutError, RuntimeError, ValueError:
            continue

        if not result:
            continue

        for loc in result if isinstance(result, list) else [result]:
            formatted = _format_resolved_location(
                loc, file_path, start_line, body_line_count, project_root, cwd, seen
            )
            if formatted:
                resolved.append(formatted)

    return resolved


def _format_resolved_location(
    loc: dict,
    file_path: str,
    start_line: int,
    body_line_count: int,
    project_root: Path,
    cwd: Path,
    seen: set,
) -> str | None:
    resolved = _resolve_location(loc)
    if resolved is None:
        return None

    path, def_start, _def_end = resolved
    key = (str(path), def_start)
    if key in seen:
        return None
    seen.add(key)

    # Skip definitions inside the searched function itself
    abs_file = Path(file_path).resolve()
    func_start_0 = start_line - 1
    if path == abs_file and func_start_0 <= def_start < func_start_0 + body_line_count:
        return None

    # Skip definitions outside the project (stdlib, site-packages)
    try:
        path.relative_to(project_root)
    except ValueError:
        return None

    try:
        rel_path = path.relative_to(cwd)
    except ValueError:
        rel_path = path

    snippet = _read_definition_body(path, def_start)
    if not snippet:
        return None

    return f"File: {rel_path}:{def_start + 1}\n```python\n{snippet}\n```"


def execute(name: str, root_path: Path | None = None) -> str:
    from jmcp.lsp import get_client

    cwd = root_path or Path.cwd()
    defs = _find_definitions(name, cwd)
    if not defs:
        return f"No symbol named '{name}' found."

    defn = defs[0]
    file_path = defn["file"]
    start_line = defn["line"]
    body = defn["body"]
    body_line_count = body.count("\n") + 1

    output = [f"File: {file_path}:{start_line}\n```python\n{body}\n```"]

    client = get_client()
    names = _tokenize_names(body)
    resolved = _collect_resolved_definitions(
        client, names, name, file_path, start_line, body_line_count, cwd.resolve(), cwd
    )
    output.extend(resolved)
    return "\n\n".join(output)
