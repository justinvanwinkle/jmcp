from jmcp.server import make_response


def handle_ping(params, id):
    return make_response(id, {})
