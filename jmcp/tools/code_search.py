import re
import subprocess
from pathlib import Path

TOOL_DEF = {
    "name": "code_search",
    "description": "Search for a function or class definition by name and return its source code.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the function or class to find",
            }
        },
        "required": ["name"],
    },
}


MAX_LINES = 100


def _run_grep(name: str, cwd: Path) -> subprocess.CompletedProcess:
    cmd = [
        "git",
        "grep",
        "-n",
        "-W",
        "-I",
        "-P",
        f"^\\s*(class|def)\\s+{re.escape(name)}\\b",
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, check=False
    )


def _parse_grep_output(output: str) -> list[dict]:
    lines = output.splitlines()
    parsed_lines = []
    # Regex to parse grep output lines
    # Matches: file:123:content  or  file-123-content  or  file=123=content
    grep_line_re = re.compile(r"^(.+?)([:\-=])(\d+)\2(.*)$")

    for line in lines:
        if line == "--":
            continue

        m = grep_line_re.match(line)
        if not m:
            continue

        filename, sep, line_num, content = m.groups()
        parsed_lines.append({
            "file": filename,
            "line": int(line_num),
            "content": content,
            "is_match": (sep == ":"),
        })
    return parsed_lines


def _extract_body(parsed_lines: list[dict], start_idx: int) -> tuple[str, int]:
    """Extract code body starting at start_idx. Returns (body_str, next_idx)."""
    item = parsed_lines[start_idx]
    filename = item["file"]

    indent_match = re.match(r"^(\s*)", item["content"])
    base_indent = len(indent_match.group(1)) if indent_match else 0

    body_lines = [item["content"]]
    j = start_idx + 1

    while j < len(parsed_lines):
        next_item = parsed_lines[j]
        if next_item["file"] != filename:
            break
        if next_item["line"] != parsed_lines[j - 1]["line"] + 1:
            break

        next_content = next_item["content"]
        if not next_content.strip():
            body_lines.append(next_content)
        else:
            next_indent_match = re.match(r"^(\s*)", next_content)
            next_indent = (
                len(next_indent_match.group(1)) if next_indent_match else 0
            )
            if next_indent > base_indent:
                body_lines.append(next_content)
            else:
                break
        j += 1

    content_str = "\n".join(body_lines)
    if len(body_lines) > MAX_LINES:
        truncated_body = body_lines[:MAX_LINES]
        truncated_body.append(
            f"... (truncated {len(body_lines) - MAX_LINES} more lines) ..."
        )
        content_str = "\n".join(truncated_body)

    return content_str, j


def execute(name: str, root_path: Path | None = None) -> str:
    cwd = root_path or Path.cwd()
    try:
        result = _run_grep(name, cwd)
    except FileNotFoundError:
        return "Error: git command not found."

    if result.returncode != 0:
        if result.returncode == 1:
            return f"No symbol named '{name}' found."
        return f"git grep failed: {result.stderr}"

    parsed_lines = _parse_grep_output(result.stdout)
    results = []
    i = 0
    while i < len(parsed_lines):
        item = parsed_lines[i]

        is_target_def = False
        if item["is_match"] and re.search(
            f"^\\s*(class|def)\\s+{re.escape(name)}\\b", item["content"]
        ):
            is_target_def = True

        if is_target_def:
            content_str, _ = _extract_body(parsed_lines, i)
            # We don't advance i to next_idx because we might want to see overlaps?
            # Actually, git grep -W chunks are usually disjoint or we process them sequentially.
            # But the loop logic in original code was complex: `j` scanned forward.
            # If I return `next_idx` I can skip processing those lines?
            # Yes, usually.

            start_line = item["line"]
            filename = item["file"]
            results.append(
                f"File: {filename}:{start_line}\n```python\n{content_str}\n```"
            )
            # In original code, `i` was incremented by 1 at loop end.
            # If I extracted a body, I should probably skip it?
            # But overlapping definitions (nested functions) might be interesting?
            # But `git grep -W` gives context.
            # I'll stick to original behavior: `i += 1`.

        i += 1

    if not results:
        return f"Found matches for '{name}' but failed to extract body."

    return "\n\n".join(results)
