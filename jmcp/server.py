PROTOCOL_VERSION = "2025-03-26"

TOOLS = [
    {
        "name": "hello",
        "description": "Say hello",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to greet"},
            },
            "required": ["name"],
        },
    },
]


def handle_tool_call(name, arguments):
    match name:
        case "hello":
            return f"Hello, {arguments['name']}!"
        case _:
            raise ValueError(f"Unknown tool: {name}")


def make_response(id, result):
    return {"jsonrpc": "2.0", "id": id, "result": result}


def make_error(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def handle_request(method, params, id):
    match method:
        case "initialize":
            return make_response(
                id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "jmcp", "version": "0.1.0"},
                },
            )

        case "ping":
            return make_response(id, {})

        case "tools/list":
            return make_response(id, {"tools": TOOLS})

        case "tools/call":
            name = params["name"]
            arguments = params.get("arguments", {})
            try:
                text = handle_tool_call(name, arguments)
                return make_response(
                    id,
                    {
                        "content": [{"type": "text", "text": text}],
                    },
                )
            except Exception as e:  # noqa: BLE001
                return make_response(
                    id,
                    {
                        "content": [{"type": "text", "text": str(e)}],
                        "isError": True,
                    },
                )

        case _:
            return make_error(id, -32601, f"Method not found: {method}")
