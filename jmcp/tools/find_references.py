import logging
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlparse

from jmcp.lsp import get_client

logger = logging.getLogger(__name__)

TOOL_DEF = {
    "name": "find_references",
    "description": (
        "Find all references (call sites and usages) of the symbol at a "
        "specific location in a file, project-wide. Use this for reverse "
        "lookups: 'where is X called from?'. Provide the location of the "
        "symbol's definition or one of its usages."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "file": {
                "type": "string",
                "description": "The file path containing the symbol",
            },
            "line": {
                "type": "integer",
                "description": "The line number (1-based) where the symbol appears",
            },
            "col": {
                "type": "integer",
                "description": "The column number (0-based) where the symbol appears (defaults to 0)",
                "default": 0,
            },
            "include_declaration": {
                "type": "boolean",
                "description": "If true, the symbol's own definition is included in results.",
                "default": False,
            },
        },
        "required": ["file", "line"],
    },
}


def uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    return Path(unquote(parsed.path))


def execute(
    file: str, line: int, col: int = 0, *, include_declaration: bool = False
) -> str:
    client = get_client()

    # LSP uses 0-based lines. User provides 1-based.
    lsp_line = line - 1

    try:
        result = client.find_references(
            file, lsp_line, col, include_declaration=include_declaration
        )
    except Exception as e:
        logger.exception("Error querying language server")
        return f"Error querying language server: {e}"

    if not result:
        return "No references found."

    # Cache file reads
    file_cache: dict[Path, list[str]] = {}

    def get_line(path: Path, lineno_0: int) -> str:
        if path not in file_cache:
            try:
                file_cache[path] = path.read_text().splitlines()
            except OSError:
                file_cache[path] = []
        lines = file_cache[path]
        if 0 <= lineno_0 < len(lines):
            return lines[lineno_0]
        return ""

    # Group by file for cleaner output
    by_file: dict[Path, list[tuple[int, str]]] = {}
    for loc in result:
        uri = loc.get("uri")
        range_ = loc.get("range")
        if not uri or not range_:
            continue
        path = uri_to_path(uri)
        try:
            rel = path.relative_to(Path.cwd())
        except ValueError:
            rel = path
        lineno_0 = range_["start"]["line"]
        content = get_line(path, lineno_0).rstrip()
        by_file.setdefault(rel, []).append((lineno_0 + 1, content))

    output_lines = [f"Found {len(result)} reference(s):"]
    for rel in sorted(by_file):
        output_lines.append(f"\n### {rel}")
        for lineno_1, content in sorted(by_file[rel]):
            output_lines.append(f"  {lineno_1}: {content}")

    return "\n".join(output_lines)
