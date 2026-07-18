"""
Shared HTTP/SSE transport for the Bitwig MCP server.

Runs ONE BitwigMCPServer instance -- a single OSC link to Bitwig Studio on the
configured send/receive ports -- and exposes it over MCP-SSE so that MANY MCP
clients (Claude CLI / Claude Code, Cursor, Claude Desktop + the Cowork bridge)
can all drive the SAME Bitwig at once.

This replaces the old stdio wiring, where every client spawned its own private
copy of the server and they fought over UDP 9001 (only one could bind it, so
every other client timed out). With one shared server there is exactly one OSC
socket and one Bitwig link; the clients multiplex over HTTP.

Run EXACTLY ONE of these. Kill any leftover `python -m bitwig_mcp_server`
stdio instances first (see stop_bitwig_servers.bat).

Endpoints:
    GET  /sse         MCP event stream  <-- point every client here
    POST /messages/   MCP client->server channel (used internally by /sse)
    GET  /healthz     liveness probe

Config (env, BITWIG_MCP_ prefix): BITWIG_MCP_MCP_PORT (default 8080),
BITWIG_MCP_BITWIG_SEND_PORT (8005), BITWIG_MCP_BITWIG_RECEIVE_PORT (9001),
BITWIG_MCP_MONITOR_PORT (8765).
"""

import logging

import anyio
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from mcp.server.sse import SseServerTransport
from mcp.server.transport_security import TransportSecuritySettings

from bitwig_mcp_server.mcp.server import BitwigMCPServer
from bitwig_mcp_server.settings import get_settings

logger = logging.getLogger("bitwig_mcp_server.serve_sse")


def build_app(bitwig: BitwigMCPServer) -> Starlette:
    """Wrap one BitwigMCPServer's low-level MCP server in a Starlette+SSE app.

    All connections share the single `bitwig` instance (one OSC controller), so
    a global lock serializes tool calls: two agents firing commands at the same
    moment can't interleave a single OSC request/response round-trip.
    """
    # Bound to 127.0.0.1 only; disable DNS-rebinding host checks so clients
    # using 127.0.0.1 or localhost with any port are accepted.
    sse = SseServerTransport(
        "/messages/",
        security_settings=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )

    mcp_server = bitwig.mcp_server
    init_opts = mcp_server.create_initialization_options()

    # Serialize OSC-touching tool calls across all client sessions.
    osc_lock = anyio.Lock()
    _orig_call_tool = bitwig.call_tool

    async def _serialized_call_tool(name, arguments):
        async with osc_lock:
            return await _orig_call_tool(name, arguments)

    # Re-register the wrapped handler (overrides the one set in __init__).
    mcp_server.call_tool()(_serialized_call_tool)

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await mcp_server.run(read_stream, write_stream, init_opts)
        return Response()

    async def healthz(request: Request):
        return JSONResponse({"ok": True, "server": "bitwig-mcp-sse"})

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/healthz", endpoint=healthz),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )


def main() -> int:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)

    # One instance = one OSC link + one monitor. OSC starts lazily on first tool.
    bitwig = BitwigMCPServer(settings)
    app = build_app(bitwig)

    host = settings.monitor_host  # 127.0.0.1
    port = settings.mcp_port      # 8080 by default
    logger.info(
        "Bitwig MCP SHARED server up: MCP-SSE http://%s:%d/sse | "
        "OSC send %s:%d recv :%d | monitor http://%s:%d",
        host, port, settings.bitwig_host, settings.bitwig_send_port,
        settings.bitwig_receive_port, settings.monitor_host, settings.monitor_port,
    )
    uvicorn.run(app, host=host, port=port, log_level=settings.log_level.lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
