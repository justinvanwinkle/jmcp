import json
import sys

from jmcp.server import handle_request, make_error


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(make_error(None, -32700, "Parse error")) + "\n")
            sys.stdout.flush()
            continue

        if "id" not in msg:
            continue

        response = handle_request(msg.get("method", ""), msg.get("params"), msg["id"])
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
