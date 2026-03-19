from jmcp.tools import add_import, code_navigation, code_search, deep_search

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
    code_navigation.TOOL_DEF,
    deep_search.TOOL_DEF,
    add_import.TOOL_DEF,
]


def handle_tool_call(name, arguments):
    match name:
        case "hello":
            return f"Hello, {arguments['name']}!"
        case "code_search":
            return code_search.execute(arguments["name"])
        case "goto_definition":
            return code_navigation.execute(
                arguments["file"], arguments["line"], arguments.get("col", 0)
            )
        case "deep_search":
            return deep_search.execute(arguments["name"])
        case "add_import":
            return add_import.execute(arguments["imports"], arguments["files"])
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
