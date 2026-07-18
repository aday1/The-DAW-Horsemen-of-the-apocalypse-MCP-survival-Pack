# Bitwig MCP — one shared server for ALL clients

## Why
`bitwig_mcp_server` speaks **MCP over stdio**, so every client (Claude CLI/Code,
Cursor, Cowork, Claude Desktop) used to launch its **own** copy. Each copy binds
**UDP 9001** to hear Bitwig's OSC replies — but only ONE process can own that
port, and Bitwig's DrivenByMoss "Open Sound Control" controller only replies to
one host:port. So whoever grabbed 9001 first worked; everyone else timed out
("6 processes, only one holds 9001"). Retrying can't fix a structural clash.

## Fix: one server, many clients
`server/serve_sse.py` runs **one** `BitwigMCPServer` (the single OSC link) and
exposes it over **MCP-SSE** at `http://127.0.0.1:8080/sse`. Every client points
at that URL. One OSC socket, one Bitwig link, N clients multiplexed. A lock
serializes tool calls so two agents can't interleave one OSC round-trip.

Ports: MCP-SSE 8080 · OSC send→Bitwig 8005 · OSC recv←Bitwig 9001 · monitor 8765.

## Start it (do this ONCE)
1. `stop_bitwig_servers.bat`   — kill every leftover stdio/SSE bitwig server.
2. `run_bitwig_mcp_shared.bat` — start EXACTLY ONE shared server.
3. In Bitwig: Settings → Controllers → the DrivenByMoss/OSC controller →
   toggle OFF then ON (re-handshakes to the fresh server). Receive 8005 /
   Send 9001 / host 127.0.0.1.

Liveness: open http://127.0.0.1:8080/healthz  → `{"ok": true, ...}`.
Monitor:  http://127.0.0.1:8765

## Point each client at it
- **Claude CLI / Code** — repo `.mcp.json` `bitwig` is now:
  `{ "type": "sse", "url": "http://127.0.0.1:8080/sse" }`  → restart the client.
- **Cursor** — `.cursor/mcp.json` `bitwig` is now:
  `{ "url": "http://127.0.0.1:8080/sse" }`  → toggle it off/on in Cursor settings.
- **Cowork / Claude Desktop bridge** — change the desktop app's `bitwig`
  connector from the stdio command to the URL `http://127.0.0.1:8080/sse`.
  If that client only accepts a stdio command, use the shim:
  `npx -y mcp-remote http://127.0.0.1:8080/sse`.

## Rule for the next agent
Do NOT re-add a stdio `python -m bitwig_mcp_server` entry for a second client —
that recreates the 9001 clash. All clients share the ONE SSE server. The old
stdio launcher (`run_bitwig_mcp.bat`) is for single-client use only.

Backups of the pre-change configs: `.mcp.json.bak.presse`,
`.cursor/mcp.json.bak.presse`.
