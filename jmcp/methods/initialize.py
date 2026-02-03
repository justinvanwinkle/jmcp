from jmcp.server import PROTOCOL_VERSION, make_response


def handle_initialize(params, id):
    return make_response(
        id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "jmcp", "version": "0.1.0"},
        },
    )
