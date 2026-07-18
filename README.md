# The DAW Horsemen of the Apocalypse — MCP Survival Pack

Four DAWs. One repo. Your AI rides them all.

## Out of the box

```bat
git clone https://github.com/aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack.git DAW-Horsemen
cd DAW-Horsemen
CARE.bat
```

Or open **`launch_daw_mcp.bat`** / Desktop **DAW Horsemen** → GUI → **CARE**.

That heals agents + DAWs, starts shared Bitwig SSE `:8080`, writes the Desktop
shortcut, and shows health. Restart Cursor / Claude once. Ride.

| Horseman | DAW | Path | Rides on |
|---|---|---|---|
| Death | REAPER | `packages/reaper-mcp/` | Python + Lua bridge |
| War | Bitwig | `packages/bitwig-mcp-server/` | Python + OSC (DawpocalypseMCP) |
| Pestilence | Renoise | `packages/renoise-mcp-bridge/` | Node → ReMCP (HTTP) |
| Famine | Reason | `packages/reason/` | Rack Plugin inside REAPER |
| (desk) | Behringer X-Touch | `packages/mackie-xtouch/` | MCU MIDI on **Bitwig** (default) |

Version: `VERSION`. Showcase: `docs/index.html`. Detail: `IDE_SETUP.txt` / `SETUP.txt`.

## GUI launcher (default)

- `launcher_gui.py` — tray companion: health + ports + GitHub update, CARE/stacks, live log
  (close/minimise → system tray; `--tray` starts hidden)
- `launch_daw_mcp.bat` — starts the GUI (pythonw)
- `launch_daw_mcp_cli.bat` — old text menu
- Desktop: **DAW Horsemen** (and legacy **DAW MCP Launchers**)

## Update

GUI → **UPDATE from GitHub**, or `UPDATE.bat`, or CARE again.

## Bitwig: one shared server

```bat
packages\bitwig-mcp-server\run_bitwig_mcp_shared.bat
```

Every agent: `http://127.0.0.1:8080/sse` — see `SHARED_SERVER.md` + `IDE_SETUP.txt`.

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
- Default owner: **Bitwig** via DrivenByMoss **MCU - Control Universal**
  (CARE disables REAPER Mackie so Windows MIDI does not clash). See
  `packages/mackie-xtouch/SETUP_MACKIE.txt`.

### This pack
- Shared Bitwig SSE server, CARE/INSTALL/heal, launchers, IDE wiring, docs —
  **aday** (+ Claude tooling). Does not replace or relicense the upstreams.

Each package keeps its own LICENSE. Respect them.
