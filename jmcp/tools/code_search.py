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
            },
        },
        "required": ["name"],
    },
}


MAX_LINES = 100


def execute(name: str) -> str:
    # 1. Run git grep
    # We use -P for PCRE to support \b and \s reliably
    # -n for line numbers
    # -W for function context
    # -I to ignore binary files
    try:
        cmd = [
            "git",
            "grep",
            "-n",
            "-W",
            "-I",
            "-P",
            f"^\\s*(class|def)\\s+{re.escape(name)}\\b",
        ]
        # We run inside the current working directory
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd(), check=False)
    except FileNotFoundError:
        return "Error: git command not found."

    if result.returncode != 0:
        # returncode 1 means no matches found
        if result.returncode == 1:
            return f"No symbol named '{name}' found."
        return f"git grep failed: {result.stderr}"

    output = result.stdout

    # 2. Parse output
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
        parsed_lines.append(
            {
                "file": filename,
                "line": int(line_num),
                "content": content,
                "is_match": (sep == ":"),
            }
        )

    # Now find the definitions requested
    results = []

    i = 0
    while i < len(parsed_lines):
        item = parsed_lines[i]

        # Check if this line is a definition match for our target
        is_target_def = False
        if item["is_match"]:
            if re.search(f"^\\s*(class|def)\\s+{re.escape(name)}\\b", item["content"]):
                is_target_def = True

        if is_target_def:
            # Found a start!
            start_line = item["line"]
            filename = item["file"]

            # Determine indentation
            indent_match = re.match(r"^(\s*)", item["content"])
            base_indent = len(indent_match.group(1)) if indent_match else 0

            body_lines = [item["content"]]

            # Scan forward
            j = i + 1
            while j < len(parsed_lines):
                next_item = parsed_lines[j]

                # Must be same file
                if next_item["file"] != filename:
                    break

                # Must be sequential lines (allow skipping if line numbers are contiguous)
                if next_item["line"] != parsed_lines[j - 1]["line"] + 1:
                    break

                # Check indentation
                next_content = next_item["content"]
                if not next_content.strip():
                    # Empty line, include it
                    body_lines.append(next_content)
                else:
                    next_indent_match = re.match(r"^(\s*)", next_content)
                    next_indent = len(next_indent_match.group(1)) if next_indent_match else 0

                    if next_indent > base_indent:
                        body_lines.append(next_content)
                    else:
                        # Indentation dropped back -> end of block
                        break
                j += 1

            # Check length
            content_str = "\n".join(body_lines)
            if len(body_lines) > 100:
                truncated_body = body_lines[:100]
                truncated_body.append(f"... (truncated {len(body_lines) - 100} more lines) ...")
                content_str = "\n".join(truncated_body)

            results.append(f"File: {filename}:{start_line}\n```python\n{content_str}\n```")

        i += 1

    if not results:
        # Fallback: maybe git grep found it but our parser missed it?
        # Or maybe the regex match was fuzzy?
        # If git grep returned 0, we should have found something.
        # But maybe we filtered it out?
        return f"Found matches for '{name}' but failed to extract body."

    return "\n\n".join(results)
