import json
import logging
import sys
from typing import TextIO

from jmcp.server import make_error

logger = logging.getLogger(__name__)


class MCPApp:
    def __init__(self, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout):
        self.stdin = stdin
        self.stdout = stdout

    def run(self):
        """Run the MCP server loop."""
        # Use lazy import to avoid circular dependencies if any
        from jmcp.server import handle_request

        for line in self.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                self._send(make_error(None, -32700, "Parse error"))
                continue

            if "id" not in msg:
                # Notification - ignore or handle?
                # MCP spec says we should handle notifications too usually,
                # but our current logic is request-response focused.
                continue

            try:
                # Dispatch request
                response = handle_request(msg.get("method", ""), msg.get("params"), msg["id"])
                self._send(response)
            except Exception as e:
                logger.exception("Error handling request")
                self._send(make_error(msg["id"], -32603, f"Internal error: {e!s}"))

    def _send(self, data: dict):
        try:
            # MCP stdio transport: line-delimited JSON
            json_str = json.dumps(data)
            self.stdout.write(json_str + "\n")
            self.stdout.flush()
        except Exception:
            logger.exception("Failed to write response")
