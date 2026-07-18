# Changelog

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
