from jmcp.server import make_response
from jmcp.server import TOOLS


def handle_tools_list(params, id):
    return make_response(id, {"tools": TOOLS})
