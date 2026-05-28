import json
import logging
import subprocess
import sys
import threading
from pathlib import Path

from jmcp.once import once

logger = logging.getLogger(__name__)


class LspClient:
    def __init__(self):
        self._proc = None
        self._lock = threading.Lock()
        self._responses = {}  # id -> result (or exception)
        self._events = {}  # id -> threading.Event
        self._next_id = 1
        self._open_files = set()
        self._root = Path.cwd()
        self.start()

    def start(self):
        cmd = ["ty", "server"]
        # Use a separate process group or detach if needed?
        # For now, just simple Popen
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,  # Let stderr go to console for debugging
            bufsize=0,
        )
        if self._proc.stdout is None or self._proc.stdin is None:
            msg = "Failed to open LSP process pipes"
            raise RuntimeError(msg)

        # Start reader thread
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

        # Initialize
        root_uri = self._path_to_uri(self._root)
        self.request(
            "initialize",
            {
                "rootUri": root_uri,
                "workspaceFolders": [{"uri": root_uri, "name": self._root.name}],
                "capabilities": {},
            },
        )
        self.notify("initialized", {})

    def _path_to_uri(self, path: Path | str) -> str:
        return f"file://{Path(path).resolve()}"

    def _read_headers(self) -> dict[str, str] | None:
        headers = {}
        while True:
            line = self._proc.stdout.readline().decode("utf-8").strip()
            if not line:
                if not headers:
                    return None
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()
        return headers

    def _reader_loop(self):
        """Reads JSON-RPC messages from stdout."""
        if not self._proc or not self._proc.stdout:
            logger.error("Reader loop started without pipes")
            return

        while True:
            try:
                headers = self._read_headers()
                if headers is None:
                    return

                length = int(headers.get("Content-Length", 0))
                if length == 0:
                    continue

                body = self._proc.stdout.read(length).decode("utf-8")
                msg = json.loads(body)

                if "id" in msg:
                    req_id = msg["id"]
                    with self._lock:
                        if req_id in self._events:
                            self._responses[req_id] = msg
                            self._events[req_id].set()
                else:
                    # Notification - ignore for now (diagnostics, etc.)
                    pass

            except Exception:
                logger.exception("LSP reader error")
                break

    def send(self, payload):
        if not self._proc or not self._proc.stdin:
            msg = "LSP process not ready"
            raise RuntimeError(msg)

        body = json.dumps(payload)
        msg = f"Content-Length: {len(body)}\r\n\r\n{body}"
        with self._lock:
            self._proc.stdin.write(msg.encode("utf-8"))
            self._proc.stdin.flush()

    def request(self, method, params):
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            event = threading.Event()
            self._events[req_id] = event

        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self.send(payload)

        # Wait for response
        if not event.wait(timeout=10.0):
            # Cleanup
            with self._lock:
                del self._events[req_id]
            raise TimeoutError(f"LSP request {method} timed out")

        with self._lock:
            response = self._responses.pop(req_id)
            del self._events[req_id]

        if "error" in response:
            raise RuntimeError(f"LSP error: {response['error']}")

        return response.get("result")

    def notify(self, method, params):
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self.send(payload)

    def ensure_open(self, file_path: str):
        path = Path(file_path).resolve()
        uri = self._path_to_uri(path)

        with self._lock:
            if uri in self._open_files:
                return

        try:
            content = path.read_text()
        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}") from None

        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": 1,
                    "text": content,
                }
            },
        )

        with self._lock:
            self._open_files.add(uri)

    def goto_definition(self, file_path: str, line: int, character: int = 0):
        self.ensure_open(file_path)
        uri = self._path_to_uri(file_path)

        # LSP uses 0-based lines
        return self.request(
            "textDocument/definition",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            },
        )

    def find_references(
        self,
        file_path: str,
        line: int,
        character: int = 0,
        *,
        include_declaration: bool = False,
    ):
        self.ensure_open(file_path)
        uri = self._path_to_uri(file_path)

        # LSP uses 0-based lines
        return self.request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": include_declaration},
            },
        )


@once
def get_client() -> LspClient:
    return LspClient()
