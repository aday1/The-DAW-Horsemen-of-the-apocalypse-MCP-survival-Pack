#!/usr/bin/env python3
"""DAW Horsemen GUI launcher — tray, health, ports, update checks, CARE/stacks."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, WORD, X, Y, BooleanVar, StringVar, Tk, ttk
from tkinter.scrolledtext import ScrolledText

PACK = Path(__file__).resolve().parent
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from health_status import (
        check_github_update,
        collect,
        format_report,
        local_version,
        ports_snapshot,
        tray_summary,
    )
except ImportError:
    collect = None  # type: ignore
    format_report = None  # type: ignore
    check_github_update = None  # type: ignore
    ports_snapshot = None  # type: ignore
    tray_summary = None  # type: ignore
    local_version = lambda pack=None: "?"  # type: ignore

BG = "#0e090c"
PANEL = "#161016"
BONE = "#ece2cf"
ASH = "#9a8f96"
GOLD = "#d4a017"
OK = "#6fbf6a"
BAD = "#d12b3f"
IDLE = "#8a7f8a"

_TRAY = None  # pystray.Icon | None


def _no_window_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _python() -> str:
    return sys.executable or "python"


def _ensure_tray_deps() -> tuple[bool, str]:
    """Try import pystray+PIL; optionally pip --user once."""
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401

        return True, "ok"
    except ImportError:
        pass
    try:
        subprocess.check_call(
            [_python(), "-m", "pip", "install", "--user", "-q", "pystray", "pillow"],
            creationflags=_no_window_flags(),
            timeout=120,
        )
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401

        return True, "installed"
    except Exception as e:
        return False, str(e)[:120]


def _make_tray_image(status: str = "ok"):
    """64x64 blood-circle icon; ring color = health."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill = (209, 43, 63, 255)
    ring = (111, 191, 106, 255) if status == "ok" else (
        (212, 160, 23, 255) if status == "warn" else (209, 43, 63, 255)
    )
    d.ellipse([4, 4, 60, 60], fill=fill, outline=ring, width=4)
    d.rectangle([28, 18, 36, 46], fill=(236, 226, 207, 255))
    d.rectangle([20, 28, 44, 36], fill=(236, 226, 207, 255))
    return img


class LauncherApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("DAW Horsemen — Launcher")
        self.root.geometry("1000x720")
        self.root.minsize(860, 600)
        self.root.configure(bg=BG)

        self.log_q: queue.Queue = queue.Queue()
        self.busy = BooleanVar(value=False)
        self._tray_icon = None
        self._tray_thread: threading.Thread | None = None
        self._last_upd: dict | None = None
        self._quit_requested = False
        self._tray_tip = "DAW Horsemen"

        self.status_vars: dict[str, StringVar] = {
            "Bitwig": StringVar(value="..."),
            "REAPER": StringVar(value="..."),
            "Renoise": StringVar(value="..."),
            "SSE :8080": StringVar(value="..."),
            "ReMCP :19714": StringVar(value="..."),
            "Update": StringVar(value="..."),
        }
        self.port_vars: dict[str, StringVar] = {
            "SSE :8080": StringVar(value="..."),
            "OSC :8005": StringVar(value="..."),
            "OSC :9001": StringVar(value="..."),
            "mon :8765": StringVar(value="..."),
            "ReMCP :19714": StringVar(value="..."),
        }
        self._pill_labels: dict[str, ttk.Label] = {}
        self._port_labels: dict[str, ttk.Label] = {}

        self._build_style()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Unmap>", self._on_unmap)
        self.root.after(80, self._start_tray)
        self.root.after(150, self.refresh_health)
        self.root.after(200, self._drain_log)
        self.root.after(250, self.check_update)
        self.root.after(10000, self._auto_health)
        self.root.after(15 * 60 * 1000, self._auto_update)

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=BONE, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=BONE, font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=ASH, font=("Segoe UI", 9))
        style.configure("Pill.TLabel", background=PANEL, foreground=ASH, font=("Consolas", 9), padding=6)
        style.configure("TButton", font=("Segoe UI", 9), padding=6)
        style.configure("TLabelframe", background=PANEL, foreground=BONE)
        style.configure("TLabelframe.Label", background=PANEL, foreground=GOLD, font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, style="TFrame")
        top.pack(fill=X, padx=14, pady=(12, 6))
        ttk.Label(top, text="DAW HORSEMEN", style="Title.TLabel").pack(anchor="w")
        ver = local_version(PACK)
        ttk.Label(
            top,
            text=f"v{ver}  ·  tray: close/minimise hides here  ·  Bitwig SSE http://127.0.0.1:8080/sse",
            style="Sub.TLabel",
        ).pack(anchor="w")
        ttk.Label(top, text=f"pack: {PACK}", style="Sub.TLabel").pack(anchor="w")

        pills = ttk.LabelFrame(self.root, text=" HEALTH ", style="TLabelframe")
        pills.pack(fill=X, padx=14, pady=6)
        row = ttk.Frame(pills, style="Panel.TFrame")
        row.pack(fill=X, padx=8, pady=8)
        for key, var in self.status_vars.items():
            cell = ttk.Frame(row, style="Panel.TFrame")
            cell.pack(side=LEFT, padx=4)
            ttk.Label(cell, text=key, style="Sub.TLabel").pack(anchor="w")
            lab = ttk.Label(cell, textvariable=var, style="Pill.TLabel", width=12)
            lab.pack(anchor="w")
            self._pill_labels[key] = lab

        ports = ttk.LabelFrame(self.root, text=" PORTS ", style="TLabelframe")
        ports.pack(fill=X, padx=14, pady=4)
        prow = ttk.Frame(ports, style="Panel.TFrame")
        prow.pack(fill=X, padx=8, pady=8)
        for key, var in self.port_vars.items():
            cell = ttk.Frame(prow, style="Panel.TFrame")
            cell.pack(side=LEFT, padx=4)
            ttk.Label(cell, text=key, style="Sub.TLabel").pack(anchor="w")
            lab = ttk.Label(cell, textvariable=var, style="Pill.TLabel", width=10)
            lab.pack(anchor="w")
            self._port_labels[key] = lab
        ttk.Label(
            ports,
            text="OSC 8005/9001 = UDP (Bitwig DrivenByMoss). Free while Bitwig off is normal.",
            style="Sub.TLabel",
        ).pack(anchor="w", padx=10, pady=(0, 6))

        acts = ttk.Frame(self.root, style="TFrame")
        acts.pack(fill=X, padx=14, pady=4)

        left = ttk.LabelFrame(acts, text=" SETUP / UPDATE ", style="TLabelframe")
        left.pack(side=LEFT, fill=Y, padx=(0, 8))
        for text, cmd in (
            ("CARE — update + heal + SSE", self.do_care),
            ("Heal bridges / agents only", self.do_heal),
            ("UPDATE from GitHub (git)", self.do_update),
            ("Check GitHub release", self.check_update),
            ("Open latest release page", self.open_latest_release),
            ("INSTALL (deps + heal)", self.do_install),
            ("Refresh health now", self.refresh_health),
            ("Hide to tray", self.hide_to_tray),
        ):
            ttk.Button(left, text=text, command=cmd).pack(fill=X, padx=8, pady=3)

        mid = ttk.LabelFrame(acts, text=" START ", style="TLabelframe")
        mid.pack(side=LEFT, fill=Y, padx=8)
        for text, cmd in (
            ("ALL DAWs + MCPs", lambda: self.do_stack("all")),
            ("Bitwig + shared SSE", lambda: self.do_stack("bitwig")),
            ("REAPER + bridge", lambda: self.do_stack("reaper")),
            ("Renoise + ReMCP", lambda: self.do_stack("renoise")),
            ("Shared SSE only", self.do_sse_only),
            ("Stop Bitwig MCP procs", self.do_stop_bitwig_mcp),
        ):
            ttk.Button(mid, text=text, command=cmd).pack(fill=X, padx=8, pady=3)

        right = ttk.LabelFrame(acts, text=" DOCS ", style="TLabelframe")
        right.pack(side=LEFT, fill=Y, padx=8)
        for text, cmd in (
            ("Open showcase page", self.open_showcase),
            ("IDE setup guide", lambda: self.open_file(PACK / "IDE_SETUP.txt")),
            ("SETUP (GitHub OOTB)", lambda: self.open_file(PACK / "SETUP.txt")),
            ("Mackie / X-Touch note", lambda: self.open_file(PACK / "packages" / "mackie-xtouch" / "SETUP_MACKIE.txt")),
            ("Recreate Desktop shortcut", self.do_shortcut),
            ("Quit Horsemen", self.quit_app),
            ("Old CLI menu", self.open_cli_menu),
        ):
            ttk.Button(right, text=text, command=cmd).pack(fill=X, padx=8, pady=3)

        logf = ttk.LabelFrame(self.root, text=" LOG ", style="TLabelframe")
        logf.pack(fill=BOTH, expand=True, padx=14, pady=(6, 12))
        self.log = ScrolledText(
            logf,
            wrap=WORD,
            height=16,
            bg="#0a0709",
            fg=BONE,
            insertbackground=BONE,
            font=("Consolas", 9),
            relief="flat",
            borderwidth=0,
        )
        self.log.pack(fill=BOTH, expand=True, padx=6, pady=6)
        self.log.tag_configure("ok", foreground=OK)
        self.log.tag_configure("bad", foreground=BAD)
        self.log.tag_configure("info", foreground=ASH)
        self.log.tag_configure("head", foreground=GOLD)
        self.log_msg(
            "GUI ready. Close or minimise → system tray. Double-click tray icon to restore.\n",
            "head",
        )

    # --- log helpers (avoid shadowing ScrolledText.log) ---
    def log_msg(self, msg: str, tag: str | None = None) -> None:
        self.log_q.put((msg if msg.endswith("\n") else msg + "\n", tag))

    def _drain_log(self) -> None:
        try:
            while True:
                msg, tag = self.log_q.get_nowait()
                self.log.insert(END, msg, tag)
                self.log.see(END)
        except queue.Empty:
            pass
        self.root.after(150, self._drain_log)

    def _set_pill(self, store: dict[str, ttk.Label], key: str, var: StringVar, ok: bool | None, text: str) -> None:
        var.set(text)
        lab = store[key]
        if ok is True:
            lab.configure(foreground=OK)
        elif ok is False:
            lab.configure(foreground=BAD)
        else:
            lab.configure(foreground=IDLE)

    # --- tray ---
    def _start_tray(self) -> None:
        ok, detail = _ensure_tray_deps()
        if not ok:
            self.log_msg(f"Tray deps missing ({detail}). pip install pystray pillow", "bad")
            return
        if detail == "installed":
            self.log_msg("Installed pystray + pillow for system tray.", "ok")

        import pystray
        from pystray import MenuItem as Item

        def show(icon=None, item=None) -> None:
            self.root.after(0, self.show_from_tray)

        def hide(icon=None, item=None) -> None:
            self.root.after(0, self.hide_to_tray)

        def refresh(icon=None, item=None) -> None:
            self.root.after(0, self.refresh_health)

        def care(icon=None, item=None) -> None:
            self.root.after(0, self.do_care)

        def upd(icon=None, item=None) -> None:
            self.root.after(0, self.check_update)

        def sse(icon=None, item=None) -> None:
            self.root.after(0, self.do_sse_only)

        def quit_(icon=None, item=None) -> None:
            self.root.after(0, self.quit_app)

        menu = pystray.Menu(
            Item("Show launcher", show, default=True),
            Item("Hide to tray", hide),
            pystray.Menu.SEPARATOR,
            Item("Refresh health", refresh),
            Item("Check for update", upd),
            Item("CARE (heal + SSE)", care),
            Item("Start shared SSE", sse),
            pystray.Menu.SEPARATOR,
            Item("Quit", quit_),
        )
        self._tray_icon = pystray.Icon(
            "daw_horsemen",
            _make_tray_image("ok"),
            self._tray_tip,
            menu,
        )
        self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        self._tray_thread.start()
        self.log_msg("System tray active. Close window = hide to tray (Quit from tray menu to exit).", "ok")

    def _update_tray(self, tip: str, status: str = "ok") -> None:
        self._tray_tip = tip
        icon = self._tray_icon
        if not icon:
            return
        try:
            icon.title = tip
            icon.icon = _make_tray_image(status)
        except Exception:
            pass

    def hide_to_tray(self) -> None:
        self.root.withdraw()
        self.log_msg("Hidden to tray.", "info")

    def show_from_tray(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_unmap(self, event) -> None:
        # minimise → tray (ignore child widget unmaps)
        if event.widget is not self.root:
            return
        if self._quit_requested:
            return
        try:
            if self.root.state() == "iconic":
                self.root.after(50, self.hide_to_tray)
        except Exception:
            pass

    def _on_close(self) -> None:
        if self._tray_icon is not None:
            self.hide_to_tray()
        else:
            self.quit_app()

    def quit_app(self) -> None:
        self._quit_requested = True
        icon = self._tray_icon
        self._tray_icon = None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
        self.root.destroy()

    # --- health / ports / update ---
    def refresh_health(self) -> None:
        if collect is None:
            self.log_msg("health_status.py missing", "bad")
            return

        def work() -> None:
            self.log_msg("--- health ---", "head")
            try:
                rep = collect(PACK)
                text = format_report(rep)
                for line in text.splitlines():
                    tag = "ok" if "OK " in line else ("bad" if "BAD" in line else "info")
                    if line.startswith("==") or line.startswith("RESULT"):
                        tag = "head"
                    self.log_msg(line, tag)

                by = {c.name: c for c in rep.checks}
                mapping = [
                    ("Bitwig", "Bitwig"),
                    ("REAPER", "REAPER"),
                    ("Renoise", "Renoise"),
                    ("SSE :8080", "Bitwig shared SSE :8080"),
                    ("ReMCP :19714", "Renoise ReMCP :19714"),
                ]
                for pill, cname in mapping:
                    c = by.get(cname)
                    if not c:
                        self.root.after(
                            0,
                            lambda p=pill: self._set_pill(
                                self._pill_labels, p, self.status_vars[p], None, "?"
                            ),
                        )
                        continue
                    label = "UP" if c.ok else "DOWN"
                    if cname in ("Bitwig", "REAPER", "Renoise") and not c.ok:
                        label = "off"
                    self.root.after(
                        0,
                        lambda p=pill, o=c.ok, t=label: self._set_pill(
                            self._pill_labels, p, self.status_vars[p], o, t
                        ),
                    )

                # ports row
                if ports_snapshot:
                    snap = ports_snapshot()
                    port_map = {
                        "SSE :8080": "SSE :8080",
                        "OSC recv :8005": "OSC :8005",
                        "OSC send :9001": "OSC :9001",
                        "monitor :8765": "mon :8765",
                        "ReMCP :19714": "ReMCP :19714",
                    }
                    for p in snap:
                        gui_key = port_map.get(p["name"])
                        if not gui_key or gui_key not in self.port_vars:
                            continue
                        txt = "UP" if p["ok"] else ("free" if "OSC" in gui_key else "DOWN")
                        # OSC free = idle (normal); OSC bound = ok
                        if "OSC" in gui_key:
                            ok_flag: bool | None = True if p["ok"] else None
                        else:
                            ok_flag = bool(p["ok"])
                        self.root.after(
                            0,
                            lambda k=gui_key, o=ok_flag, t=txt: self._set_pill(
                                self._port_labels, k, self.port_vars[k], o, t
                            ),
                        )

                upd = self._last_upd
                if check_github_update:
                    # reuse last if fresh; else leave Update pill to check_update
                    pass
                tip = tray_summary(rep, upd) if tray_summary else "DAW Horsemen"
                status = "ok" if rep.fail_count == 0 else "bad"
                if upd and upd.get("available"):
                    status = "warn"
                self.root.after(0, lambda: self._update_tray(tip, status))
            except Exception as e:
                self.log_msg(f"health failed: {e}", "bad")

        threading.Thread(target=work, daemon=True).start()

    def _auto_health(self) -> None:
        if not self.busy.get():
            self.refresh_health()
        self.root.after(12000, self._auto_health)

    def _auto_update(self) -> None:
        if not self.busy.get():
            self.check_update(silent=True)
        self.root.after(15 * 60 * 1000, self._auto_update)

    def check_update(self, silent: bool = False) -> None:
        if check_github_update is None:
            return

        def work() -> None:
            if not silent:
                self.log_msg("--- update check ---", "head")
            try:
                upd = check_github_update(PACK)
                self._last_upd = upd
                if not silent:
                    tag = "bad" if upd.get("available") else ("ok" if upd.get("ok") else "info")
                    self.log_msg(upd.get("detail", ""), tag)
                    if upd.get("msi_url"):
                        self.log_msg(f"MSI: {upd['msi_url']}", "info")
                if upd.get("available"):
                    self.root.after(
                        0,
                        lambda: self._set_pill(
                            self._pill_labels,
                            "Update",
                            self.status_vars["Update"],
                            False,
                            f"→{upd.get('remote')}",
                        ),
                    )
                    self.root.after(
                        0,
                        lambda: self._update_tray(
                            f"UPDATE {upd.get('local')}->{upd.get('remote')}", "warn"
                        ),
                    )
                elif upd.get("ok"):
                    self.root.after(
                        0,
                        lambda: self._set_pill(
                            self._pill_labels,
                            "Update",
                            self.status_vars["Update"],
                            True,
                            "current",
                        ),
                    )
                else:
                    self.root.after(
                        0,
                        lambda: self._set_pill(
                            self._pill_labels,
                            "Update",
                            self.status_vars["Update"],
                            None,
                            "?",
                        ),
                    )
            except Exception as e:
                if not silent:
                    self.log_msg(f"update check failed: {e}", "bad")

        threading.Thread(target=work, daemon=True).start()

    def open_latest_release(self) -> None:
        url = "https://github.com/aday1/The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack/releases/latest"
        if self._last_upd and self._last_upd.get("url"):
            url = self._last_upd["url"]
        self.log_msg(f"Open {url}", "head")
        webbrowser.open(url)

    def _run_cmd(
        self,
        title: str,
        args: list[str],
        *,
        cwd: Path | None = None,
        env: dict | None = None,
        shell: bool = False,
    ) -> None:
        if self.busy.get():
            self.log_msg("Busy — wait for current job.", "bad")
            return
        self.busy.set(True)
        self.log_msg(f">>> {title}", "head")
        self.log_msg(" ".join(args) if isinstance(args, list) else str(args), "info")

        def work() -> None:
            try:
                e = os.environ.copy()
                if env:
                    e.update(env)
                e["CARE_NOPAUSE"] = "1"
                e["PYTHONUNBUFFERED"] = "1"
                proc = subprocess.Popen(
                    args,
                    cwd=str(cwd or PACK),
                    env=e,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    shell=shell,
                    creationflags=_no_window_flags() if not shell else 0,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.log_msg(line.rstrip("\n"), "info")
                rc = proc.wait()
                self.log_msg(f"<<< exit {rc}", "ok" if rc == 0 else "bad")
            except Exception as ex:
                self.log_msg(f"FAILED: {ex}", "bad")
            finally:
                self.busy.set(False)
                self.root.after(400, self.refresh_health)
                self.root.after(600, self.check_update)

        threading.Thread(target=work, daemon=True).start()

    def do_care(self) -> None:
        self._run_cmd("CARE (GitHub update + heal + SSE)", ["cmd", "/c", "CARE.bat"], env={"CARE_NOPAUSE": "1"})

    def do_heal(self) -> None:
        self._run_cmd("HEAL", [_python(), str(SCRIPTS / "heal_daw_bridges.py")])

    def do_update(self) -> None:
        if not (PACK / ".git").exists():
            self.log_msg("No .git (MSI install). Use Check GitHub release / Open latest release / reinstall MSI.", "info")
            self.open_latest_release()
            return
        cmd = (
            "git fetch origin main && git pull --ff-only origin main && "
            f'"{_python()}" scripts\\heal_daw_bridges.py'
        )
        self._run_cmd("UPDATE (git pull + heal)", ["cmd", "/c", cmd])

    def do_install(self) -> None:
        cmd = (
            f'"{_python()}" -m pip install --user -q -r packages\\reaper-mcp\\requirements.txt && '
            f'"{_python()}" -m pip install --user -q mcp[cli] python-osc pydantic pydantic-settings uvicorn starlette anyio pystray pillow && '
            "pushd packages\\renoise-mcp-bridge && call npm install --silent && popd && "
            f'"{_python()}" scripts\\heal_daw_bridges.py && '
            f'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\make_desktop_shortcut.ps1 -PackRoot "{PACK}"'
        )
        self._run_cmd("INSTALL (deps + heal + shortcut)", ["cmd", "/c", cmd])

    def do_stack(self, target: str) -> None:
        ps1 = SCRIPTS / "start_stack.ps1"
        self._run_cmd(
            f"Start stack: {target}",
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1),
                "-Target",
                target,
            ],
        )

    def do_sse_only(self) -> None:
        self._run_cmd(
            "Ensure shared SSE",
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPTS / "ensure_shared_sse.ps1"),
                str(PACK),
            ],
        )

    def do_stop_bitwig_mcp(self) -> None:
        self._run_cmd(
            "Stop Bitwig MCP",
            ["cmd", "/c", "packages\\bitwig-mcp-server\\stop_bitwig_servers.bat"],
        )

    def do_shortcut(self) -> None:
        self._run_cmd(
            "Desktop shortcut",
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPTS / "make_desktop_shortcut.ps1"),
                "-PackRoot",
                str(PACK),
            ],
        )

    def open_showcase(self) -> None:
        path = PACK / "docs" / "index.html"
        self.log_msg(f"Opening showcase: {path}", "head")
        webbrowser.open(path.as_uri())

    def open_file(self, path: Path) -> None:
        if not path.is_file():
            self.log_msg(f"Missing: {path}", "bad")
            return
        self.log_msg(f"Open {path.name}", "info")
        os.startfile(str(path))  # type: ignore[attr-defined]

    def open_cli_menu(self) -> None:
        cli = PACK / "launch_daw_mcp_cli.bat"
        if cli.is_file():
            subprocess.Popen(["cmd", "/c", "start", "DAW Horsemen CLI", str(cli)], cwd=str(PACK))
            self.log_msg("Opened CLI menu window", "info")
        else:
            self.log_msg("CLI bat missing", "bad")

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    if "--cli" in sys.argv:
        cli = PACK / "launch_daw_mcp_cli.bat"
        if cli.is_file():
            os.system(f'cmd /c "{cli}"')
            return 0
    # optional: start hidden if --tray
    app = LauncherApp()
    if "--tray" in sys.argv:
        app.root.after(400, app.hide_to_tray)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
