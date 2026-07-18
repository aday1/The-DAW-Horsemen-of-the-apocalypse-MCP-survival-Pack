# Changelog

## 2.5.1 — "MSI Ship" (2026-07-18)
- **Release artifact is MSI** (`DAW-Horsemen-<ver>.msi`), not ZIP.
  WiX 7 packager: `installer/Product.wxs` + `scripts/build_msi.ps1`.
  Per-user install → `%LOCALAPPDATA%\Programs\DAW-Horsemen`, Start Menu +
  Desktop shortcuts, HKCU `Software\aday\DAW-Horsemen\InstallLocation`.
- `RELEASE.bat` uploads the MSI to GitHub Releases.
- After install: run **CARE** (Start Menu) or open **DAW Horsemen** GUI.

## 2.5.0 — "GUI Launcher" (2026-07-18)
- **`launcher_gui.py`**: Tkinter GUI — CARE / heal / update / start stacks,
  live **health pills** (Bitwig, REAPER, Renoise, SSE, ReMCP, git), scrolling
  **log**. Default entry via `launch_daw_mcp.bat` (pythonw).
- Desktop shortcut **DAW Horsemen** (+ legacy **DAW MCP Launchers**) → GUI.
- Old text menu kept as `launch_daw_mcp_cli.bat`.
- `scripts/health_status.py`: shared Python health for GUI + CLI.
- SETUP/README streamlined: GitHub clone → CARE (or GUI CARE button).

## 2.4.0 — "Out Of The Box" (2026-07-18)
- **CARE.bat = one-shot OOTB**: heal agents + DAWs, Desktop shortcut, start
  shared Bitwig SSE if down, health check. No manual MCP paste required.
- **Heal upgrades**: upsert Cursor / Claude Code `.mcp.json` + `.cursor/mcp.json`
  (jam + pack), enable Claude Code/CLI `enabledMcpjsonServers`, patch all
  Claude Desktop config locations with `mcp-remote` → `:8080/sse`.
- **Docs + showcase**: named upstream credits (TwelveTake, jxstanford,
  Jürgen Moßgraber / DrivenByMoss, kraken ReMCP); remixed `docs/index.html`
  with tracker / clip-launcher / envelope / rack primers.
- **RELEASE.bat**: maintainer ZIP + GitHub release from `git archive`.

## 2.3.0 — "CARE + X-Touch" (2026-07-18)
- **`CARE.bat`**: GitHub care package — pull if behind, always heal
  (OSC ports, DawpocalypseMCP, REAPER lua, MCP paths), Mackie template,
  desktop shortcut, health check.
- **`packages/mackie-xtouch/`**: Behringer X-Touch Bitwig template + starter
  project + SETUP. MCU lives in DawpocalypseMCP (DrivenByMoss); X-Touch is
  MIDI MCU beside MCP, not a second MCP server. REAPER uses native Mackie
  Control; Renoise has no MCU in this pack (honest).
- Launchers menu **C** = CARE; heal installs Mackie template automatically.

## 2.2.0 — "DawpocalypseMCP" (2026-07-18)
- Bitwig controller fork renamed **OSC-vaday → DawpocalypseMCP**; INSTALL/UPDATE
  heal patches extension + prefs.
- Auto-heal Bitwig OSC ports in prefs (receive **8005**, send **9001**) — fixes
  "both are 8005" which prevented the OSC server from starting.
- `scripts/heal_daw_bridges.py`: sync REAPER lua, Bitwig ext, rewrite
  `mcp.generated.json` + Claude Desktop snippet with THIS machine's paths,
  patch project `.mcp.json` / `.cursor/mcp.json`. Launchers menu **F**.

## 2.1.0 — "Generals Get a Shortcut" (2026-07-18)
- `INSTALL.bat` creates Desktop shortcut **DAW MCP Launchers**, writes
  `mcp.generated.json` with absolute paths, opens Renoise ReMCP xrnx if missing.
- New **`IDE_SETUP.txt`**: Cursor, Claude Code, Claude CLI, VS Code, Claude
  Desktop/Cowork — how to wire MCPs; Bitwig always `http://127.0.0.1:8080/sse`.
- `mcp.json.example`, `scripts/make_desktop_shortcut.ps1`,
  `scripts/write_mcp_generated.ps1`; launcher menu D/E for shortcut + IDE docs.
- SETUP.txt / README / docs showcase updated for GitHub newcomers.

## 2.0.0 — "War Never Shares a Port" (2026-07-18)
- **Shared Bitwig server**: `serve_sse.py` + `run_bitwig_mcp_shared.bat` — one
  process owns the OSC link (8005/9001), all MCP clients connect via
  HTTP-SSE `:8080/sse`. Fixes the multi-client UDP 9001 clash for good.
- Folded in the live-tested dev-box code: Bitwig settings/OSC/monitor
  (ports 8005/9001, activity dashboard, install-guide tools), Renoise
  `bridge.js` env-config, per-DAW launchers + plain-text setup guides.
- New pack tooling: `INSTALL.bat` (fresh machine), `UPDATE.bat`
  (checks GitHub + pulls), `PUBLISH.bat` (dev box push).
- Showcase page in `docs/` (GitHub Pages ready).

## 1.x
- Initial pack: REAPER, Renoise, Bitwig MCP + Reason notes, extract scripts.
