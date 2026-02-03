import json
import io
from unittest.mock import MagicMock, patch
from jmcp.app import MCPApp


def test_app_run_basic():
    # Simulate stdin
    input_data = '{"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}\n'
    stdin = io.StringIO(input_data)
    stdout = io.StringIO()

    app = MCPApp(stdin, stdout)
    app.run()

    # Check output
    output = stdout.getvalue()
    response = json.loads(output)
    assert response["id"] == 1
    assert response["result"] == {}


def test_app_json_error():
    stdin = io.StringIO("not json\n")
    stdout = io.StringIO()

    app = MCPApp(stdin, stdout)
    app.run()

    output = stdout.getvalue()
    response = json.loads(output)
    assert "error" in response
    assert response["error"]["code"] == -32700


def test_app_exception_handling():
    # Simulate a request that causes internal error (e.g. by mocking handler)
    input_data = '{"jsonrpc": "2.0", "id": 1, "method": "crash", "params": {}}\n'
    stdin = io.StringIO(input_data)
    stdout = io.StringIO()

    with patch("jmcp.server.handle_request", side_effect=ValueError("Boom")):
        app = MCPApp(stdin, stdout)
        app.run()

    output = stdout.getvalue()
    response = json.loads(output)
    assert "error" in response
    assert response["error"]["code"] == -32603
    assert "Internal error: Boom" in response["error"]["message"]
