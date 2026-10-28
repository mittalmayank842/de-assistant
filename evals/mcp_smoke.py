"""Start the MCP server over stdio, list its tools and call two of them."""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "de_assistant.mcp_server"],
                                   env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            print("tools:", [t.name for t in tools])
            res = await s.call_tool("trace_lineage", {"table": "platinum.movers"})
            print("trace_lineage ->", res.content[0].text[:300])
            res = await s.call_tool("search_docs", {"query": "what to do on HTTP 429", "k": 1})
            print("search_docs ->", json.loads(res.content[0].text)["section"] if res.content else None)


asyncio.run(main())
