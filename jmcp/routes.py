from collections.abc import Callable

from jmcp.once import once


class Routes:
    @staticmethod
    @once
    def methods() -> dict[str, Callable]:
        from jmcp.methods.initialize import handle_initialize
        from jmcp.methods.ping import handle_ping
        from jmcp.methods.tools_call import handle_tools_call
        from jmcp.methods.tools_list import handle_tools_list

        return {
            "initialize": handle_initialize,
            "ping": handle_ping,
            "tools/list": handle_tools_list,
            "tools/call": handle_tools_call,
        }
