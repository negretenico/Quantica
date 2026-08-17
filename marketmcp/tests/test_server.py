from mcp.server import MCPServer

from run import mcp


class TestMcpServer:
    def test_server_is_mcp_instance(self):
        assert isinstance(mcp, MCPServer)

    def test_server_name(self):
        assert mcp.name == "marketmcp"
