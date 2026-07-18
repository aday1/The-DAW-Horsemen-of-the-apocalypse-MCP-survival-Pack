# Changelog

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
