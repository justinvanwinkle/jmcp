from jmcp.server import handle_request


def test_initialize():
    response = handle_request("initialize", {}, 1)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    result = response["result"]
    assert result["protocolVersion"] == "2025-03-26"
    assert "capabilities" in result
    assert "serverInfo" in result
    assert result["serverInfo"]["name"] == "jmcp"


def test_ping():
    response = handle_request("ping", {}, 2)
    assert response["id"] == 2
    assert response["result"] == {}


def test_tools_list():
    response = handle_request("tools/list", {}, 3)
    assert response["id"] == 3
    tools = response["result"]["tools"]
    assert isinstance(tools, list)
    names = [t["name"] for t in tools]
    assert "hello" in names
    assert "code_search" in names
    assert "goto_definition" in names


def test_unknown_method():
    response = handle_request("bogus", {}, 4)
    assert "error" in response
    assert response["error"]["code"] == -32601
