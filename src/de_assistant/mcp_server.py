"""MCP server exposing the six tools to any MCP client (Claude Desktop, Claude Code, ...).

  claude mcp add de-assistant -- /path/to/.venv/bin/python -m de_assistant.mcp_server
"""
from mcp.server.mcpserver import MCPServer

from .tools import TOOLS

mcp = MCPServer("de-assistant", instructions="Tools for a crypto market data pipeline: docs search, "
                "table metadata, PII scan, lineage, run status and a guarded trigger.")
for fn in TOOLS.values():
    mcp.add_tool(fn)

if __name__ == "__main__":
    mcp.run()
