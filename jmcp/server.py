from jmcp.tools import code_search

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
    code_search.TOOL_DEF,
]


def handle_tool_call(name, arguments):
    match name:
        case "hello":
            return f"Hello, {arguments['name']}!"
        case "code_search":
            return code_search.execute(arguments["name"])
        case _:
            raise ValueError(f"Unknown tool: {name}")


def make_response(id, result):
    return {"jsonrpc": "2.0", "id": id, "result": result}


def make_error(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def handle_request(method, params, id):
    from jmcp.routes import Routes

    handler = Routes.methods().get(method)
    if handler is None:
        return make_error(id, -32601, f"Method not found: {method}")
    return handler(params, id)
