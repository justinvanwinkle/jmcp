from jmcp.server import TOOLS, make_response


def handle_tools_list(params, id):
    return make_response(id, {"tools": TOOLS})
