# 🐎 The DAW Horsemen of the Apocalypse — MCP Survival Pack

Four DAWs. One repo. Your AI rides them all.

MCP servers + bridges so Claude / Cursor / any MCP client can drive your studio:

| Horseman | DAW | Path | Rides on |
|---|---|---|---|
| Death | REAPER | `packages/reaper-mcp/` | Python + Lua bridge |
| War | Bitwig | `packages/bitwig-mcp-server/` | Python + OSC (DawpocalypseMCP) |
| Pestilence | Renoise | `packages/renoise-mcp-bridge/` | Node → ReMCP (HTTP) |
| Famine | Reason | `packages/reason/` | No MCP of its own — rides inside REAPER (Rack Plugin) |
| (desk) | Behringer X-Touch | `packages/mackie-xtouch/` | MCU MIDI via DawpocalypseMCP / REAPER Mackie — not a separate MCP |

**This repo is the source of truth.** Machines install from it and update from it.

## Install (any machine)

```bat
git clone https://github.com/aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack.git DAW-Horsemen
cd DAW-Horsemen
CARE.bat
```

`CARE.bat` is the GitHub care package: pulls if behind, **heals** Bitwig
OSC ports + **DawpocalypseMCP** extension, REAPER lua, Mackie/X-Touch
template, rewrites per-machine MCP JSON, Desktop shortcut, health check.

`INSTALL.bat` still works for a first-time deps-only path; CARE is preferred.

**Wire your IDE next:** read **`IDE_SETUP.txt`** (Cursor, Claude Code, Claude
CLI, VS Code, Claude Desktop/Cowork). Template: `mcp.json.example`.

## Update (any machine)

```bat
UPDATE.bat
```

Checks GitHub, pulls if behind, refreshes deps. That's the whole updater.

## Launchers (DAWs + MCPs)

After install, use the Desktop shortcut or:

```bat
launch_daw_mcp.bat
```

Menu can start Bitwig / REAPER / Renoise **and** their MCP side, run a health
check (`scripts\health_check.ps1`), INSTALL, or UPDATE. Recreate the shortcut
anytime: `powershell -File scripts\make_desktop_shortcut.ps1`

## Bitwig: ONE shared server, many clients

Bitwig's OSC controller talks to **one** process. Don't let every MCP client
spawn its own server — run the shared one and point everybody at it:

```bat
packages\bitwig-mcp-server\run_bitwig_mcp_shared.bat
```

Then every client (Claude CLI, Cursor, Claude Desktop/Cowork, VS Code MCP
extensions) uses: `http://127.0.0.1:8080/sse` — full story in
`packages/bitwig-mcp-server/SHARED_SERVER.md` and **`IDE_SETUP.txt`**.

**Yes — shared Bitwig MCP works across all agents on the machine** as long as
each client points at that SSE URL (not `python -m bitwig_mcp_server` stdio).
REAPER / Renoise stay stdio-per-client (no single OSC port to fight over).
## Dev flow

Dev happens in the clone (on the dev box: `E:\ChiptuneClaude\DAW-Horsemen`).
Edit → test → when it's a keeper, commit and `PUBLISH.bat`. Other machines
`UPDATE.bat`. No loose copies — if it's not in the repo, it doesn't exist.

## Per-DAW quickstarts

Plain-text walkthroughs, one per horseman: `packages/*/SETUP_*.txt` and `SETUP.txt`.

## Credits / upstreams 🙏

- **REAPER MCP** — TwelveTake lineage (see `packages/reaper-mcp/README.md` + LICENSE)
- **Bitwig MCP** — [jxstanford/bitwig-mcp-server](https://github.com/jxstanford/bitwig-mcp-server) lineage; OSC via **DrivenByMoss** by Jürgen Moßgraber
- **Renoise** — bridge only; the Renoise-side tool is **ReMCP** (separate project)
- Local additions (shared SSE server, launchers, pack tooling) by aday + Claude

Each package keeps its own LICENSE — respect them (MIT / LGPL where applicable).
