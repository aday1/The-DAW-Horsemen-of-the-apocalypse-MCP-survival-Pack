# The DAW Horsemen of the Apocalypse MCP Pack

One repo bundling Model Context Protocol servers and bridges for **REAPER**, **Renoise**, **Bitwig**, plus notes for **Reason** (via REAPER).

| Path | What |
|------|------|
| `packages/reaper-mcp/` | TwelveTake REAPER MCP (Python + Lua bridge) |
| `packages/renoise-mcp-bridge/` | Node stdio bridge to Renoise ReMCP (HTTP) |
| `packages/bitwig-mcp-server/` | Bitwig Studio MCP (Python + OSC / DrivenByMoss) |
| `packages/reason/` | No standalone MCP — use REAPER + **Reason Rack Plugin** |

## TLDR

Read **`SETUP.txt`** (same content, plain text).

Quick checks:

- **REAPER:** run Lua bridge, then `get_project_summary` or `get_reaper_mcp_install_guide`.
- **Renoise:** start ReMCP in Renoise, then `npm install` in `renoise-mcp-bridge` and point Cursor at `node bridge.js`.
- **Bitwig:** OSC controller on, then `uv sync` in `bitwig-mcp-server` and `python -m bitwig_mcp_server` from Cursor.
- **Reason:** produce in Reason Rack on a REAPER track; automate through REAPER MCP.

## Extract to default Windows locations

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\extract_to_machine.ps1
```

Optional: `-BitwigOnly`, `-ReaperScriptsOnly`, `-WhatIf`.

## GitHub

After creating an empty repo named **`The_DAW_Horsemen_of_the_apocalypse_MCP_Pack`**:

```bash
git remote add origin https://github.com/YOUR_USER/The_DAW_Horsemen_of_the_apocalypse_MCP_Pack.git
git branch -M main
git push -u origin main
```

## Credits / upstreams

- REAPER MCP: TwelveTake fork (see `packages/reaper-mcp/README.md`).
- Bitwig MCP: based on jxstanford/bitwig-mcp-server lineage; OSC via DrivenByMoss / Bitwig Open Sound Control.
- Renoise: bridge only; Renoise-side tool is separate (ReMCP).

## License

Each package may carry its own license file (MIT, LGPL for DrivenByMoss-derived work, etc.). Respect per-folder `LICENSE` / headers.
