"""
Live activity log + optional localhost web dashboard for Reaper MCP.

Env:
  REAPER_MCP_DASHBOARD   1/true to start http://127.0.0.1:<port>/ (default off)
  REAPER_MCP_DASHBOARD_PORT  port (default 3847)
  REAPER_MCP_LOG_BRIDGE  1/true to log each REAPER bridge call (verbose)

HTTP:
  GET /                  Reference + live activity UI
  GET /api/events        JSON tail of MCP (and optional bridge) events
  GET /api/reference     JSON tool groups, flat tool list, sample prompts
"""

from __future__ import annotations

import html
import json
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

_MAX_DEQUE = 400
_MAX_ARG_JSON = 1200
_MAX_RESULT_JSON = 2500

_lock = threading.Lock()
_events: deque[dict[str, Any]] = deque(maxlen=_MAX_DEQUE)
_log_file: Path | None = None
_server_started = False
_server_lock = threading.Lock()


def _dashboard_enabled() -> bool:
    v = os.getenv("REAPER_MCP_DASHBOARD", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def bridge_log_enabled() -> bool:
    v = os.getenv("REAPER_MCP_LOG_BRIDGE", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _log_dir() -> Path:
    base = os.getenv("REAPER_MCP_LOG_DIR")
    if base:
        return Path(base)
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA", "")) / "reaper-mcp"
    return Path.home() / ".local" / "share" / "reaper-mcp"


def _ensure_log_path() -> Path:
    global _log_file
    if _log_file is None:
        d = _log_dir()
        d.mkdir(parents=True, exist_ok=True)
        _log_file = d / "activity.jsonl"
    return _log_file


def _truncate(obj: Any, limit: int) -> str:
    try:
        s = json.dumps(obj, default=str)
    except TypeError:
        s = repr(obj)
    if len(s) > limit:
        return s[: limit - 3] + "..."
    return s


def _push(event: dict[str, Any]) -> None:
    event["t"] = datetime.now(timezone.utc).isoformat()
    with _lock:
        _events.append(event)
    if _dashboard_enabled() or bridge_log_enabled():
        try:
            path = _ensure_log_path()
            line = json.dumps(event, default=str) + "\n"
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass


def log_tool_start(name: str, arguments: dict[str, Any]) -> str:
    rid = str(uuid.uuid4())[:8]
    _push(
        {
            "kind": "tool_start",
            "id": rid,
            "name": name,
            "args": _truncate(arguments, _MAX_ARG_JSON),
        }
    )
    return rid


def log_tool_end(
    rid: str,
    name: str,
    ok: bool,
    elapsed_s: float,
    result: Any = None,
    error: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "kind": "tool_end",
        "id": rid,
        "name": name,
        "ok": ok,
        "ms": round(elapsed_s * 1000, 2),
    }
    if error:
        payload["error"] = error[:800]
    elif result is not None:
        payload["result"] = _truncate(result, _MAX_RESULT_JSON)
    _push(payload)


def log_bridge_call(func: str, args: list[Any], elapsed_s: float, summary: str) -> None:
    if not bridge_log_enabled():
        return
    _push(
        {
            "kind": "bridge",
            "func": func,
            "args": _truncate(args, 600),
            "ms": round(elapsed_s * 1000, 2),
            "summary": summary[:500],
        }
    )


def get_events_tail(n: int = 200) -> list[dict[str, Any]]:
    with _lock:
        return list(_events)[-n:]


# MCP tool names grouped for the dashboard (keep in sync with reaper_mcp_server.py).
MCP_TOOL_GROUPS: dict[str, list[str]] = {
    "Setup and install": [
        "get_reaper_mcp_install_guide",
    ],
    "Project and tempo": [
        "get_project_summary",
        "get_project_length",
        "get_project_name",
        "get_project_path",
        "save_project",
        "create_project",
        "open_project",
        "set_tempo",
        "get_tempo",
        "set_time_signature",
        "get_time_signature",
        "add_marker",
        "add_region",
        "get_markers",
        "get_regions",
        "delete_marker",
        "delete_region",
        "go_to_marker",
        "go_to_region",
        "render_project",
        "render_region",
    ],
    "Transport and view": [
        "play",
        "stop",
        "pause",
        "record",
        "get_play_state",
        "get_play_position",
        "get_cursor_position",
        "set_cursor_position",
        "toggle_repeat",
        "get_repeat_state",
        "zoom_to_selection",
        "zoom_to_project",
    ],
    "Tracks": [
        "get_track_count",
        "get_track",
        "get_all_tracks",
        "get_master_track",
        "insert_track",
        "delete_track",
        "set_track_name",
        "set_track_volume",
        "set_track_pan",
        "set_track_mute",
        "set_track_solo",
        "set_track_phase",
        "set_track_width",
        "set_track_as_folder",
        "set_track_color",
        "arm_track",
        "set_track_input",
        "set_track_monitor",
        "get_track_peak",
        "select_track",
        "select_all_tracks",
        "unselect_all_tracks",
        "get_selected_tracks",
    ],
    "FX chain and parameters": [
        "track_fx_get_count",
        "track_fx_get_list",
        "track_fx_add_by_name",
        "track_fx_delete",
        "track_fx_get_name",
        "track_fx_get_enabled",
        "track_fx_set_enabled",
        "track_fx_get_num_params",
        "track_fx_get_param_name",
        "track_fx_get_param",
        "track_fx_set_param",
        "list_fx_parameters",
        "find_fx_slot_by_name",
        "find_fx_param_indices",
        "get_fx_presets",
        "get_fx_preset",
        "set_fx_preset",
        "save_fx_preset",
        "get_track_fx_chunk",
        "add_eq",
        "add_compressor",
        "add_limiter",
    ],
    "Automation (track and FX)": [
        "get_track_envelope",
        "ensure_track_envelope",
        "add_envelope_point",
        "add_envelope_points_batch",
        "get_envelope_points",
        "get_envelope_point_count",
        "delete_envelope_point",
        "clear_envelope",
        "add_fx_envelope_points_batch",
        "add_fx_envelope_points_by_param_name",
        "ensure_automation_audible",
        "set_track_automation_mode",
        "arm_track_envelope",
    ],
    "Sends buses sidechain": [
        "create_send",
        "delete_send",
        "set_send_volume",
        "get_track_num_sends",
        "set_send_dest_channels",
        "set_send_source_channels",
        "setup_sidechain_send",
        "configure_reacomp_sidechain",
        "setup_sidechain_compression",
        "create_bus",
        "add_parallel_compression",
        "add_mastering_chain",
    ],
    "MIDI": [
        "create_midi_item",
        "get_midi_item",
        "add_midi_note",
        "add_midi_notes_batch",
        "get_midi_notes",
        "delete_midi_note",
        "clear_midi_item",
        "set_midi_note_velocity",
    ],
    "Media items and audio": [
        "insert_audio_file",
        "get_track_items",
        "get_item_info",
        "set_item_position",
        "set_item_length",
        "delete_item",
        "duplicate_item",
        "split_item",
        "set_item_mute",
        "set_item_volume",
        "set_item_fade_in",
        "set_item_fade_out",
    ],
    "Editing selection time": [
        "undo",
        "redo",
        "get_undo_state",
        "select_all_items",
        "unselect_all_items",
        "get_selected_items",
        "copy_selected_items",
        "cut_selected_items",
        "paste_items",
        "delete_selected_items",
        "set_time_selection",
        "get_time_selection",
        "clear_time_selection",
    ],
    "Actions and low level": [
        "run_action",
        "run_action_by_name",
    ],
}

SAMPLE_PROMPTS: list[tuple[str, str]] = [
    (
        "Install REAPER MCP on this machine",
        "Call get_reaper_mcp_install_guide with section full. Then produce a Cursor mcp.json snippet "
        "using the user's real paths to python and reaper_mcp_server.py, and list the exact steps to run "
        "reaper_mcp_bridge.lua in REAPER once.",
    ),
    (
        "Scan session",
        "Use the reaper MCP get_project_summary and list every track with fx_names. Say which tracks look like instruments vs buses.",
    ),
    (
        "Reaktor lanes by name",
        "On the first track that has Reaktor, call find_fx_slot_by_name then list_fx_parameters for that fx_index. Pick 8 parameters whose names look musical (not Program Change). add_fx_envelope_points_batch on each with a slow sine-like ramp over the full project length. Call ensure_automation_audible first.",
    ),
    (
        "EDM four minutes",
        "Using reaper MCP: set_tempo to 150, add_marker at 0/60/120/180s for intro/build/chorus/outro, insert_track for kick bass and lead, track_fx_add_by_name ReaSynth or existing VSTs, create_midi_item per track for 240s and add_midi_notes_batch with a simple house groove and a pentatonic lead in the chorus region only.",
    ),
    (
        "Breakcore starter",
        "set_tempo 170-190. insert_track for breaks and bass. On breaks, create_midi_item with chopped amen-style pattern using add_midi_notes_batch; add parallel distortion or track_fx_add_by_name a bitcrusher. Short loop lengths and heavy sidechain from kick using setup_sidechain_compression if tracks exist.",
    ),
    (
        "Glitch automation pass",
        "Pick one track with delay or granular FX. find_fx_param_indices for wet, feedback, time, or repeat. ensure_automation_audible and add_fx_envelope_points_batch with stepped random-ish points every beat for 16 bars. If a param refuses automation, say which index failed and try another.",
    ),
    (
        "Random modulation (batch)",
        "Tell me to run python -u fx_random_envelope_points.py from the repo temp_ folder (REAPER bridge on). After that, save_project.",
    ),
    (
        "Reason rack honesty",
        "Add track_fx_add_by_name for Reason Rack Plugin on a new track, set_track_name to remind me to load Kong inside Reason, create_midi_item with drum MIDI on channel 10.",
    ),
    (
        "Ambient wash",
        "get_project_length. On a pad track, find_fx_param_indices for filter or cutoff related substrings, add_fx_envelope_points_batch with gentle slow curves. set_track_volume automation via add_envelope_points_batch on Volume if ensure_track_envelope worked.",
    ),
    (
        "Clean mix bus",
        "create_bus named Drums with source_track_indices for all drum tracks, set_send_volume appropriately. add_mastering_chain on master if not already there.",
    ),
    (
        "Random genre dice",
        "Pick a random BPM between 92 and 178 and a random genre label (techno, dnb, hip hop, idm). Apply set_tempo, insert_track x3 with matching names, and describe what MIDI patterns you would add with add_midi_notes_batch (then add a short example).",
    ),
]


def _all_tool_names() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for _cat, names in MCP_TOOL_GROUPS.items():
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
    return sorted(out)


def reference_payload() -> dict[str, Any]:
    tools = _all_tool_names()
    return {
        "tool_count": len(tools),
        "tool_groups": MCP_TOOL_GROUPS,
        "tools_flat": tools,
        "install_guide_tool": "get_reaper_mcp_install_guide",
        "install_sections": [
            "full",
            "reaper_bridge",
            "python",
            "cursor",
            "http",
            "verify",
            "dashboard",
        ],
        "sample_prompts": [{"title": a, "prompt": b} for a, b in SAMPLE_PROMPTS],
        "bridge_data_dir": os.path.expandvars(r"%APPDATA%\REAPER\Scripts\mcp_bridge_data"),
        "batch_scripts": [
            "temp_/build_edm_session.py",
            "temp_/fx_random_envelope_points.py",
            "temp_/automate_exposed_fx_lanes.py",
        ],
    }


def _render_tool_groups_html() -> str:
    blocks: list[str] = []
    for title, names in MCP_TOOL_GROUPS.items():
        lis = "".join(f"<li><code>{html.escape(n)}</code></li>" for n in names)
        blocks.append(
            f'<details class="ref-details"><summary>{html.escape(title)} '
            f'<span class="ct">({len(names)})</span></summary><ul class="tool-ul">{lis}</ul></details>'
        )
    return "\n".join(blocks)


def _render_prompts_html() -> str:
    parts: list[str] = []
    for i, (title, text) in enumerate(SAMPLE_PROMPTS):
        tid = f"p{i}"
        esc_t = html.escape(title)
        esc_p = html.escape(text)
        parts.append(
            f'<div class="prompt-card"><h4>{esc_t}</h4>'
            f'<pre class="prompt-pre" id="{tid}">{esc_p}</pre>'
            f'<button type="button" class="btn" data-copy="{tid}">Copy prompt</button></div>'
        )
    return "\n".join(parts)


def build_dashboard_html() -> str:
    nt = len(_all_tool_names())
    tools_html = _render_tool_groups_html()
    prompts_html = _render_prompts_html()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Reaper MCP</title>
  <style>
    :root {{ --bg:#0f1419; --fg:#c8d0d8; --muted:#6b7a88; --acc:#3d8fd1; --ok:#5cb85c; --err:#d9534f; --card:#151b24; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, Segoe UI, sans-serif; background: var(--bg); color: var(--fg); margin: 0; padding: 0; font-size: 14px; line-height: 1.45; }}
    code, pre {{ font-family: ui-monospace, Consolas, monospace; font-size: 12px; }}
    header {{ padding: 14px 18px; border-bottom: 1px solid #2a3440; background: #0a0e12; }}
    h1 {{ font-size: 1.15rem; font-weight: 600; margin: 0 0 4px 0; color: var(--acc); }}
    .tagline {{ color: var(--muted); font-size: 12px; max-width: 900px; }}
    nav {{ display: flex; gap: 8px; flex-wrap: wrap; padding: 10px 18px; background: #0d1118; border-bottom: 1px solid #2a3440; }}
    nav button {{ background: #1e2836; color: var(--fg); border: 1px solid #334155; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }}
    nav button.on {{ background: var(--acc); color: #0a0e12; border-color: var(--acc); font-weight: 600; }}
    section.panel {{ display: none; padding: 16px 18px 28px; max-width: 1100px; }}
    section.panel.on {{ display: block; }}
    h2 {{ font-size: 1rem; color: #e6edf3; margin: 18px 0 8px 0; }}
    h2:first-child {{ margin-top: 0; }}
    .callout {{ background: var(--card); border: 1px solid #2a3440; border-radius: 8px; padding: 12px 14px; margin: 10px 0; font-size: 13px; }}
    .callout strong {{ color: #93c5fd; }}
    ul.bullets {{ margin: 8px 0; padding-left: 1.2rem; color: #b8c4d0; }}
    .ref-details {{ margin: 6px 0; border: 1px solid #2a3440; border-radius: 6px; background: #0a0e12; }}
    .ref-details summary {{ cursor: pointer; padding: 8px 12px; font-weight: 600; color: #e6edf3; }}
    .ref-details summary:hover {{ background: #151b24; }}
    .ref-details .ct {{ color: var(--muted); font-weight: 400; }}
    ul.tool-ul {{ margin: 0; padding: 8px 12px 12px 28px; columns: 2; column-gap: 24px; }}
    @media (max-width: 720px) {{ ul.tool-ul {{ columns: 1; }} }}
    ul.tool-ul li {{ margin: 2px 0; }}
    .prompt-card {{ background: var(--card); border: 1px solid #2a3440; border-radius: 8px; padding: 12px 14px; margin: 12px 0; }}
    .prompt-card h4 {{ margin: 0 0 8px 0; font-size: 13px; color: var(--acc); }}
    .prompt-pre {{ white-space: pre-wrap; word-break: break-word; margin: 0 0 10px 0; color: #b8c4d0; max-height: 140px; overflow-y: auto; }}
    .btn {{ background: #2563eb; color: #fff; border: none; padding: 5px 12px; border-radius: 5px; cursor: pointer; font-size: 12px; }}
    .btn:hover {{ background: #1d4ed8; }}
    #log {{ white-space: pre-wrap; word-break: break-word; line-height: 1.45; max-height: calc(100vh - 220px); overflow-y: auto; border: 1px solid #2a3440; border-radius: 6px; padding: 10px; background: #0a0e12; font-family: ui-monospace, Consolas, monospace; font-size: 12px; }}
    .row {{ margin-bottom: 6px; border-left: 3px solid #2a3440; padding-left: 8px; }}
    .row.tool_start {{ border-left-color: var(--acc); }}
    .row.tool_end {{ border-left-color: var(--muted); }}
    .row.tool_end.ok {{ border-left-color: var(--ok); }}
    .row.tool_end.fail {{ border-left-color: var(--err); }}
    .row.bridge {{ border-left-color: #a855c7; }}
    .ts {{ color: var(--muted); }}
    .name {{ color: #e6edf3; font-weight: 600; }}
    .pill {{ display: inline-block; padding: 0 6px; border-radius: 4px; background: #1e2836; font-size: 11px; margin-right: 6px; }}
  </style>
</head>
<body>
  <header>
    <h1>Reaper MCP dashboard</h1>
    <p class="tagline">Reference for humans and LLMs: tools, knowledge boundaries, VST/parameter reality, and starter prompts. Live tab shows MCP tool + optional bridge traffic. JSON: <code>/api/reference</code> and <code>/api/events</code>.</p>
  </header>
  <nav>
    <button type="button" id="tab-ref" class="on">Reference</button>
    <button type="button" id="tab-log">Live activity</button>
  </nav>

  <section id="panel-ref" class="panel on">
    <div class="callout">
      <strong>Install.</strong> MCP tool <code>get_reaper_mcp_install_guide</code> (sections: full, reaper_bridge, python, cursor, http, verify, dashboard) returns Markdown and does not call REAPER. Then run the Lua bridge and <code>test_connection.py</code> or <code>get_project_summary</code>.
    </div>
    <div class="callout">
      <strong>What the model sees.</strong> Cursor exposes MCP <em>tool names + schemas + docstrings</em> from <code>reaper_mcp_server.py</code>. It does <em>not</em> magically know your preset list until it calls tools (e.g. <code>get_project_summary</code>, <code>list_fx_parameters</code>).
    </div>

    <h2>What REAPER knows (live)</h2>
    <ul class="bullets">
      <li>Whatever is in the <strong>current project</strong> when the bridge runs: tracks, items, tempo, markers, loaded FX.</li>
      <li>Bridge folder (file mode): <code>%APPDATA%\\REAPER\\Scripts\\mcp_bridge_data</code></li>
      <li>Installed plugins appear as REAPER reports them to <code>TrackFX_GetFXName</code> / Add FX dialog strings.</li>
    </ul>

    <h2>VSTs and parameters (not a fixed database)</h2>
    <div class="callout">
      <strong>No built-in VST encyclopedia.</strong> Plugin names and parameter lists come from the host at runtime.
      Use <code>track_fx_get_list</code>, <code>list_fx_parameters</code>, <code>find_fx_param_indices</code>.
      Many indices exist for <code>TrackFX_GetParam</code> but <strong>cannot be automated</strong> until <code>GetFXEnvelope</code> succeeds (e.g. many Reaktor slots). Prefer probing with <code>add_fx_envelope_points_batch</code> or scripts in <code>temp_/</code>.
    </div>

    <h2>Operations you can drive</h2>
    <ul class="bullets">
      <li>Project layout, tempo, markers, regions, render.</li>
      <li>Tracks, mixer, sends, folders, sidechain helpers.</li>
      <li>Full FX chain: add/remove, presets, parameters, <strong>FX automation</strong> (per-param envelopes).</li>
      <li>Track envelopes Volume/Pan via name.</li>
      <li>MIDI and audio items, fades, split, duplicate.</li>
      <li>Transport, selection, undo, arbitrary <code>Main_OnCommand</code> via <code>run_action</code>.</li>
    </ul>

    <h2>MCP tools ({nt} listed)</h2>
    <p class="tagline" style="margin-bottom:10px">Grouped names match the TwelveTake fork. Enable dashboard with <code>REAPER_MCP_DASHBOARD=1</code> in the MCP server env.</p>
    {tools_html}

    <h2>Batch scripts (same bridge, no MCP round-trip)</h2>
    <ul class="bullets">
      <li><code>temp_/build_edm_session.py</code> &mdash; tempo, Reason/Reaktor sketch, MIDI, submix bus.</li>
      <li><code>temp_/fx_random_envelope_points.py</code> &mdash; dense random/sine/saw/noise-style FX automation.</li>
      <li><code>temp_/automate_exposed_fx_lanes.py</code> &mdash; only automatable params, small budgets.</li>
    </ul>

    <h2>Starter prompts</h2>
    <p class="tagline">Copy into Cursor chat with the reaper MCP enabled. Edit track indices and plugin names to match your session.</p>
    {prompts_html}
  </section>

  <section id="panel-log" class="panel">
    <p class="tagline" style="margin-bottom:10px">Polling <code>/api/events</code> every 400ms. Set <code>REAPER_MCP_LOG_BRIDGE=1</code> for per-call Lua bridge lines.</p>
    <div id="log"></div>
  </section>

  <script>
    const logEl = document.getElementById('log');
    let lastStamp = '';
    document.getElementById('tab-ref').onclick = function() {{
      document.getElementById('tab-ref').classList.add('on');
      document.getElementById('tab-log').classList.remove('on');
      document.getElementById('panel-ref').classList.add('on');
      document.getElementById('panel-log').classList.remove('on');
    }};
    document.getElementById('tab-log').onclick = function() {{
      document.getElementById('tab-log').classList.add('on');
      document.getElementById('tab-ref').classList.remove('on');
      document.getElementById('panel-log').classList.add('on');
      document.getElementById('panel-ref').classList.remove('on');
    }};
    document.querySelectorAll('[data-copy]').forEach(function(btn) {{
      btn.onclick = function() {{
        const id = btn.getAttribute('data-copy');
        const el = document.getElementById(id);
        if (el) navigator.clipboard.writeText(el.textContent || '');
      }};
    }});
    function esc(s) {{
      const d = document.createElement('div');
      d.textContent = s;
      return d.innerHTML;
    }}
    function render(ev) {{
      const k = ev.kind || '';
      let cls = 'row ' + k;
      if (k === 'tool_end') cls += ev.ok ? ' ok' : ' fail';
      let line = '<span class="ts">' + esc(ev.t || '') + '</span> ';
      line += '<span class="pill">' + esc(k) + '</span>';
      if (ev.name) line += '<span class="name">' + esc(ev.name) + '</span> ';
      if (ev.id) line += '<span class="pill">id:' + esc(ev.id) + '</span> ';
      if (ev.ms != null) line += '<span class="pill">' + esc(String(ev.ms)) + ' ms</span> ';
      if (ev.args) line += '\\n  args: ' + esc(typeof ev.args === 'string' ? ev.args : JSON.stringify(ev.args));
      if (ev.result) line += '\\n  out: ' + esc(typeof ev.result === 'string' ? ev.result : JSON.stringify(ev.result));
      if (ev.error) line += '\\n  <span style="color:#f88">' + esc(ev.error) + '</span>';
      if (ev.func) line += '<span class="name">' + esc(ev.func) + '</span> ';
      if (ev.summary) line += '\\n  ' + esc(ev.summary);
      return '<div class="' + cls + '">' + line + '</div>';
    }}
    async function poll() {{
      try {{
        const r = await fetch('/api/events');
        const data = await r.json();
        if (!data.events || !data.events.length) return;
        const tail = data.events.slice(-12);
        const stamp = data.events.length + '|' + tail.map(function(e) {{
          return (e.t||'') + '\\t' + (e.kind||'') + '\\t' + (e.id||'') + '\\t' + (e.name||'');
        }}).join('\\n');
        if (stamp === lastStamp) return;
        lastStamp = stamp;
        logEl.innerHTML = data.events.map(render).join('');
        logEl.scrollTop = logEl.scrollHeight;
      }} catch (e) {{}}
    }}
    setInterval(poll, 400);
    poll();
  </script>
</body>
</html>
"""


_INDEX_HTML = build_dashboard_html()


class _DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_INDEX_HTML.encode("utf-8"))
        elif self.path.startswith("/api/events"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            body = json.dumps({"events": get_events_tail(300)}, default=str)
            self.wfile.write(body.encode("utf-8"))
        elif self.path.startswith("/api/reference"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(json.dumps(reference_payload(), indent=2).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def start_dashboard_background() -> None:
    global _server_started
    if not _dashboard_enabled():
        return
    with _server_lock:
        if _server_started:
            return
        base = int(os.getenv("REAPER_MCP_DASHBOARD_PORT", "3847"))
        httpd: HTTPServer | None = None
        chosen = base
        for i in range(12):
            try:
                chosen = base + i
                httpd = HTTPServer(("127.0.0.1", chosen), _DashboardHandler)
                break
            except OSError:
                continue
        if httpd is None:
            return

        def run() -> None:
            httpd.serve_forever()

        t = threading.Thread(target=run, name="reaper-mcp-dashboard", daemon=True)
        t.start()
        _server_started = True
        _push(
            {
                "kind": "meta",
                "message": f"dashboard http://127.0.0.1:{chosen}/",
            }
        )


def maybe_autostart_dashboard() -> None:
    try:
        start_dashboard_background()
    except Exception:
        pass
