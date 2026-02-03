import subprocess
import json
import os
import sys


def send(proc, payload):
    body = json.dumps(payload)
    msg = f"Content-Length: {len(body)}\r\n\r\n{body}"
    proc.stdin.write(msg.encode())
    proc.stdin.flush()


def read(proc):
    headers = {}
    while True:
        line = proc.stdout.readline().decode().strip()
        if not line:
            break
        parts = line.split(": ", 1)
        if len(parts) == 2:
            headers[parts[0]] = parts[1]

    if "Content-Length" not in headers:
        return None

    length = int(headers["Content-Length"])
    body = proc.stdout.read(length).decode()
    return json.loads(body)


def main():
    cmd = ["uv", "run", "ty", "server"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr)

    # Initialize
    send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"rootUri": f"file://{os.getcwd()}", "capabilities": {}},
        },
    )

    print("Sent initialize")
    while True:
        msg = read(proc)
        if msg:
            print("Received:", msg)
            if msg.get("id") == 1:
                break

    # Send initialized notification
    send(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})

    # Try definition on a known file
    # jmcp/server.py line 35 (handle_request) -> routes.Routes
    # "from jmcp.routes import Routes"
    # Routes is at col 28

    send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/definition",
            "params": {
                "textDocument": {"uri": f"file://{os.getcwd()}/jmcp/server.py"},
                "position": {"line": 34, "character": 28},  # 0-indexed line 34 is line 35
            },
        },
    )

    print("Sent definition request")
    while True:
        msg = read(proc)
        if msg:
            print("Received:", msg)
            if msg.get("id") == 2:
                break

    proc.terminate()


if __name__ == "__main__":
    main()
