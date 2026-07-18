# The DAW Horsemen of the Apocalypse — MCP Survival Pack

Four DAWs. One repo. Your AI rides them all.

**Out of the box (any machine):**

```bat
git clone https://github.com/aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack.git DAW-Horsemen
cd DAW-Horsemen
CARE.bat
```

`CARE.bat` is the whole setup: pull if behind, heal Bitwig/REAPER/Renoise +
Mackie template, rewrite **Cursor / Claude Code / Claude CLI / Claude Desktop**
MCP configs to this clone, Desktop shortcut, start shared Bitwig SSE `:8080`,
health check. Restart IDEs once. Open DAWs. Ride.

MCP servers + bridges:

| Horseman | DAW | Path | Rides on |
|---|---|---|---|
| Death | REAPER | `packages/reaper-mcp/` | Python + Lua bridge |
| War | Bitwig | `packages/bitwig-mcp-server/` | Python + OSC (DawpocalypseMCP) |
| Pestilence | Renoise | `packages/renoise-mcp-bridge/` | Node → ReMCP (HTTP) |
| Famine | Reason | `packages/reason/` | No MCP of its own — rides inside REAPER (Rack Plugin) |
| (desk) | Behringer X-Touch | `packages/mackie-xtouch/` | MCU MIDI via DawpocalypseMCP / REAPER Mackie — not a separate MCP |

**This repo is the source of truth.** Machines install from it and update from it.

Version: see `VERSION`. Showcase: `docs/index.html`. IDE detail: `IDE_SETUP.txt`.

## Install notes

`INSTALL.bat` = deps + heal (no SSE auto-start). **CARE is preferred.**

## Update (any machine)

```bat
UPDATE.bat
```

Checks GitHub, pulls if behind, refreshes deps. Or just run `CARE.bat` again.

## Launchers (DAWs + MCPs)

After install, use the Desktop shortcut or:

```bat
launch_daw_mcp.bat
```

Menu can start Bitwig / REAPER / Renoise **and** their MCP side, run a health
check (`scripts\health_check.ps1`), INSTALL, UPDATE, or CARE. Recreate the shortcut
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
Edit → test → when it's a keeper, commit and `PUBLISH.bat` / `RELEASE.bat`.
Other machines `CARE.bat` or `UPDATE.bat`. No loose copies — if it's not in the
repo, it doesn't exist.

## Per-DAW quickstarts

Plain-text walkthroughs, one per horseman: `packages/*/SETUP_*.txt` and `SETUP.txt`.

## Credits / upstreams

This pack assembles and wires other people's work. Credit belongs upstream:

### Death — REAPER MCP
- **TwelveTake Studios LLC** — [TwelveTake REAPER MCP](https://github.com/TwelveTake/reaper-mcp)
  ([twelvetake.com](https://twelvetake.com)). MIT. See `packages/reaper-mcp/LICENSE`.

### War — Bitwig MCP + OSC
- **John Stanford (jxstanford)** — [bitwig-mcp-server](https://github.com/jxstanford/bitwig-mcp-server)
  (Python MCP over OSC). MIT. See `packages/bitwig-mcp-server/LICENSE`.
- **Jürgen Moßgraber** — [DrivenByMoss](https://www.mossgrabers.de/Software/Bitwig/Bitwig.html)
  (Bitwig controller framework; Open Sound Control + MCU). The pack's
  **DawpocalypseMCP** extension is a renamed fork of that OSC surface so the
  shared MCP can talk to Bitwig. Use DrivenByMoss under its own license terms;
  download/support: [mossgrabers.de](https://www.mossgrabers.de/).

### Pestilence — Renoise
- **kraken** (`kraken@renoise.com`) — **ReMCP / Renoise MCP** tool that runs
  inside Renoise (HTTP MCP). Bundled as `com.renoise.ReMCP*.xrnx`; listed at
  [renoise.com/tools/renoise-mcp](https://www.renoise.com/tools/renoise-mcp);
  also in [renoise/tools](https://github.com/renoise/tools) (PR by **kunitoki**).
- Pack ships a thin Node **stdio bridge** (`packages/renoise-mcp-bridge/`) that
  forwards to that ReMCP HTTP endpoint — not a replacement for ReMCP itself.

### Famine — Reason
- No third-party MCP here. Reason rides as a Rack Plugin inside REAPER; credit
  for control still goes to TwelveTake's REAPER MCP above.

### Desk — Behringer X-Touch / Mackie
- MCU MIDI surface support comes from **DrivenByMoss** (MCU - Control Universal)
  in Bitwig, and REAPER's built-in Mackie Control. Templates in
  `packages/mackie-xtouch/` are pack convenience only.

### This pack
- Shared Bitwig SSE server, CARE/INSTALL/heal, launchers, IDE wiring, docs —
  **aday** (+ Claude tooling). Does not replace or relicense the upstreams.

Each package keeps its own LICENSE. Respect them.
