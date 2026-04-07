"""
Static REAPER MCP installation text (no bridge call).
"""

from __future__ import annotations


def render_reaper_install_guide(section: str) -> str:
    s = (section or "full").strip().lower().replace("-", "_")
    if s not in ("full", "reaper_bridge", "python", "cursor", "http", "verify", "dashboard"):
        s = "full"

    parts = {
        "reaper_bridge": _REAPER_BRIDGE,
        "python": _PYTHON,
        "cursor": _CURSOR,
        "http": _HTTP,
        "verify": _VERIFY,
        "dashboard": _DASHBOARD,
    }

    if s == "full":
        return "\n\n".join([_INTRO, *parts.values()])
    return "\n\n".join([_INTRO, parts[s]])


_INTRO = """## TwelveTake REAPER MCP -- install overview

1. Copy `reaper_mcp_bridge.lua` into your REAPER Scripts folder and run it once from the Actions list.
2. Install Python deps (`pip install -r requirements.txt` or `pip install mcp httpx`).
3. Point Cursor (or Claude Desktop) at `reaper_mcp_server.py` with `python`.
4. Default control is **file-based** (`REAPER_COMM_MODE=file`); optional HTTP mode uses `REAPER_HOST` / `REAPER_PORT`.
5. Optional: `REAPER_MCP_DASHBOARD=1` for http://127.0.0.1:3847/
6. Use MCP tool `get_project_summary` or run `test_connection.py` to verify."""

_REAPER_BRIDGE = """## REAPER bridge script

1. Copy `reaper_mcp_bridge.lua` to:
   - Windows: `%APPDATA%\\REAPER\\Scripts\\`
   - macOS: `~/Library/Application Support/REAPER/Scripts/`
   - Linux: `~/.config/REAPER/Scripts/`
2. REAPER: **Actions → Show action list → Load ReaScript** → select the file → **Run**.
3. You should see a console message that the bridge started. The server writes JSON under `%APPDATA%\\REAPER\\Scripts\\mcp_bridge_data` (override with `REAPER_BRIDGE_DIR`)."""

_PYTHON = """## Python / venv

From the `twelvetake-reaper-mcp` folder:

  pip install -r requirements.txt

Smoke test:

  python reaper_mcp_server.py

(Exact entry depends on your layout; Cursor usually runs `python path/to/reaper_mcp_server.py`.)"""

_CURSOR = """## Cursor MCP configuration

Example (edit paths):

  "reaper": {
    "command": "python",
    "args": ["C:\\\\path\\\\to\\\\twelvetake-reaper-mcp\\\\reaper_mcp_server.py"],
    "env": {
      "REAPER_COMM_MODE": "file",
      "REAPER_MCP_DASHBOARD": "1"
    }
  }

Use a venv interpreter if you prefer:

  "command": "C:\\\\path\\\\to\\\\.venv\\\\Scripts\\\\python.exe",
  "args": ["C:\\\\path\\\\to\\\\reaper_mcp_server.py"]

Optional:

- `REAPER_BRIDGE_DIR` -- bridge data directory
- `REAPER_COMM_MODE` -- `file` (default), `http`, or `auto`
- `REAPER_HOST` / `REAPER_PORT` -- HTTP bridge (see HTTP section)"""

_HTTP = """## HTTP bridge mode (optional)

If you run an HTTP bridge inside REAPER on port 9000, set:

  REAPER_COMM_MODE=http
  REAPER_HOST=127.0.0.1
  REAPER_PORT=9000

`auto` tries HTTP first and falls back to file mode."""

_VERIFY = """## Verify

- Run `python test_connection.py` from the repo (with REAPER + bridge running).
- Or call MCP `get_project_summary` and confirm track data looks like your session."""

_DASHBOARD = """## Dashboard

Set `REAPER_MCP_DASHBOARD=1` on the MCP process. Open http://127.0.0.1:3847/ for reference and live tool activity (`/api/reference`, `/api/events`)."""
