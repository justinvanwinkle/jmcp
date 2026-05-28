import logging
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlparse

from jmcp.lsp import get_client

logger = logging.getLogger(__name__)
SNIPPET_MAX_LINES = 20

TOOL_DEF = {
    "name": "goto_definition",
    "description": "Find the definition of a symbol at a specific location in a file.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "file": {
                "type": "string",
                "description": "The file path containing the symbol usage",
            },
            "line": {
                "type": "integer",
                "description": "The line number (1-based) where the symbol is used",
            },
            "col": {
                "type": "integer",
                "description": "The column number (0-based) where the symbol is used (optional, defaults to 0)",
                "default": 0,
            },
        },
        "required": ["file", "line"],
    },
}


def uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    path = unquote(parsed.path)
    return Path(path)


def execute(file: str, line: int, col: int = 0) -> str:
    client = get_client()

    # LSP uses 0-based lines. User provides 1-based.
    # Convert input to 0-based.
    lsp_line = line - 1

    try:
        result = client.goto_definition(file, lsp_line, col)
    except Exception as e:
        logger.exception("Error querying language server")
        return f"Error querying language server: {e}"

    if not result:
        return "No definition found."

    # Result can be Location | Location[] | LocationLink[]
    locations = result if isinstance(result, list) else [result]

    output = []
    for loc in locations:
        # Handle LocationLink (has targetUri) vs Location (has uri)
        uri = loc.get("uri") or loc.get("targetUri")
        # LocationLink uses targetSelectionRange for the symbol
        range_ = loc.get("range") or loc.get("targetSelectionRange")
        # Fallback for LocationLink: targetRange is the full extent,
        # targetSelectionRange is the name
        if not range_ and "targetRange" in loc:
            range_ = loc["targetRange"]

        if not uri or not range_:
            continue

        path = uri_to_path(uri)
        try:
            rel_path = path.relative_to(Path.cwd())
        except ValueError:
            rel_path = path

        start_line = range_["start"]["line"]
        end_line = range_["end"]["line"]

        # Read the content if possible
        try:
            content = path.read_text().splitlines()
            # Extract relevant lines
            snippet = []
            snippet_len = end_line - start_line + 1
            if snippet_len > SNIPPET_MAX_LINES:
                # Truncate
                snippet.extend(
                    content[i]
                    for i in range(start_line, start_line + SNIPPET_MAX_LINES)
                    if i < len(content)
                )
                snippet.append("... (truncated) ...")
            else:
                snippet.extend(
                    content[i]
                    for i in range(start_line, end_line + 1)
                    if i < len(content)
                )

            snippet_str = "\n".join(snippet)
            output.append(
                f"### Definition at {rel_path}:{start_line + 1}\n```python\n{snippet_str}\n```"
            )

        except OSError:
            output.append(f"- {rel_path}:{start_line + 1}")

    return "\n\n".join(output)
