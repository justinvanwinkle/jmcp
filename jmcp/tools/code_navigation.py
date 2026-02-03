from pathlib import Path
from urllib.parse import unquote, urlparse

from jmcp.lsp import get_client

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
        return f"Error querying language server: {e}"

    if not result:
        return "No definition found."

    # Result can be Location | Location[] | LocationLink[]
    locations = result if isinstance(result, list) else [result]

    output = []
    for loc in locations:
        # Handle LocationLink (has targetUri) vs Location (has uri)
        uri = loc.get("uri") or loc.get("targetUri")
        range_ = loc.get("range") or loc.get(
            "targetSelectionRange"
        )  # LocationLink uses targetSelectionRange for the symbol
        # Fallback for LocationLink: targetRange is the full extent, targetSelectionRange is the name
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
            # If it's a single line match, show it.
            # If it's a block, show up to 10 lines?
            # Or just show the signature?

            snippet = []
            snippet_len = end_line - start_line + 1
            if snippet_len > 20:
                # Truncate
                for i in range(start_line, start_line + 20):
                    if i < len(content):
                        snippet.append(content[i])
                snippet.append("... (truncated) ...")
            else:
                for i in range(start_line, end_line + 1):
                    if i < len(content):
                        snippet.append(content[i])

            snippet_str = "\n".join(snippet)
            output.append(
                f"### Definition at {rel_path}:{start_line + 1}\n```python\n{snippet_str}\n```"
            )

        except Exception:
            output.append(f"- {rel_path}:{start_line + 1}")

    return "\n\n".join(output)
