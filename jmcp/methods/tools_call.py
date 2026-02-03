from jmcp.server import handle_tool_call, make_response


def handle_tools_call(params, id):
    name = params["name"]
    arguments = params.get("arguments", {})
    try:
        text = handle_tool_call(name, arguments)
        return make_response(
            id,
            {"content": [{"type": "text", "text": text}]},
        )
    except Exception as e:  # noqa: BLE001
        return make_response(
            id,
            {"content": [{"type": "text", "text": str(e)}], "isError": True},
        )
