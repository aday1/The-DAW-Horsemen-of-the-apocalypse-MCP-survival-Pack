#!/usr/bin/env python3
"""DAW Horsemen GUI launcher — health, CARE/update, start stacks, live log."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, WORD, X, Y, BooleanVar, StringVar, Tk, ttk
from tkinter.scrolledtext import ScrolledText

PACK = Path(__file__).resolve().parent
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from health_status import collect, format_report
except ImportError:
    collect = None  # type: ignore
    format_report = None  # type: ignore

# Horsemen palette (no emoji)
BG = "#0e090c"
PANEL = "#161016"
EDGE = "#3a2834"
BONE = "#ece2cf"
ASH = "#9a8f96"
BLOOD = "#d12b3f"
GOLD = "#d4a017"
OK = "#6fbf6a"
BAD = "#d12b3f"
IDLE = "#8a7f8a"


def _no_window_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _python() -> str:
    return sys.executable or "python"


class LauncherApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("DAW Horsemen — Launcher")
        self.root.geometry("980x680")
        self.root.minsize(820, 560)
        self.root.configure(bg=BG)

        self.log_q: queue.Queue[str] = queue.Queue()
        self.busy = BooleanVar(value=False)
        self.status_vars: dict[str, StringVar] = {
            "Bitwig": StringVar(value="…"),
            "REAPER": StringVar(value="…"),
            "Renoise": StringVar(value="…"),
            "SSE :8080": StringVar(value="…"),
            "ReMCP :19714": StringVar(value="…"),
            "Git": StringVar(value="…"),
        }
        self._pill_labels: dict[str, ttk.Label] = {}
        self._build_style()
        self._build_ui()
        self.root.after(120, self.refresh_health)
        self.root.after(200, self._drain_log)
        self.root.after(8000, self._auto_health)

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
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"))
        style.configure("TLabelframe", background=PANEL, foreground=BONE)
        style.configure("TLabelframe.Label", background=PANEL, foreground=GOLD, font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, style="TFrame")
        top.pack(fill=X, padx=14, pady=(12, 6))
        ttk.Label(top, text="DAW HORSEMEN", style="Title.TLabel").pack(anchor="w")
        ver = (PACK / "VERSION").read_text(encoding="utf-8").strip() if (PACK / "VERSION").is_file() else "?"
        ttk.Label(
            top,
            text=f"v{ver}  ·  pack: {PACK}  ·  Bitwig agents → http://127.0.0.1:8080/sse",
            style="Sub.TLabel",
        ).pack(anchor="w")

        # Status pills
        pills = ttk.LabelFrame(self.root, text=" HEALTH ", style="TLabelframe")
        pills.pack(fill=X, padx=14, pady=6)
        row = ttk.Frame(pills, style="Panel.TFrame")
        row.pack(fill=X, padx=8, pady=8)
        for key, var in self.status_vars.items():
            cell = ttk.Frame(row, style="Panel.TFrame")
            cell.pack(side=LEFT, padx=4)
            ttk.Label(cell, text=key, style="Sub.TLabel").pack(anchor="w")
            lab = ttk.Label(cell, textvariable=var, style="Pill.TLabel", width=14)
            lab.pack(anchor="w")
            self._pill_labels[key] = lab

        # Actions
        acts = ttk.Frame(self.root, style="TFrame")
        acts.pack(fill=X, padx=14, pady=4)

        left = ttk.LabelFrame(acts, text=" SETUP / UPDATE (GitHub) ", style="TLabelframe")
        left.pack(side=LEFT, fill=Y, padx=(0, 8))
        for text, cmd in (
            ("CARE — update + heal + SSE (recommended)", self.do_care),
            ("Heal bridges / agents only", self.do_heal),
            ("UPDATE from GitHub", self.do_update),
            ("INSTALL (deps + heal)", self.do_install),
            ("Refresh health now", self.refresh_health),
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
            ("Old CLI menu", self.open_cli_menu),
        ):
            ttk.Button(right, text=text, command=cmd).pack(fill=X, padx=8, pady=3)

        # Log
        logf = ttk.LabelFrame(self.root, text=" LOG ", style="TLabelframe")
        logf.pack(fill=BOTH, expand=True, padx=14, pady=(6, 12))
        self.log = ScrolledText(
            logf,
            wrap=WORD,
            height=18,
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
        self.log("DAW Horsemen GUI ready. Hit CARE once on a fresh machine, then Refresh health.\n", "head")

    def log(self, msg: str, tag: str | None = None) -> None:
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

    def _set_pill(self, key: str, ok: bool | None, text: str) -> None:
        var = self.status_vars[key]
        var.set(text)
        lab = self._pill_labels[key]
        if ok is True:
            lab.configure(foreground=OK)
        elif ok is False:
            lab.configure(foreground=BAD)
        else:
            lab.configure(foreground=IDLE)

    def refresh_health(self) -> None:
        if collect is None:
            self.log("health_status.py missing", "bad")
            return

        def work() -> None:
            self.log("--- health ---", "head")
            try:
                rep = collect(PACK)
                text = format_report(rep)
                for line in text.splitlines():
                    tag = "ok" if "OK " in line else ("bad" if "BAD" in line else "info")
                    if line.startswith("==") or line.startswith("RESULT"):
                        tag = "head"
                    self.log(line, tag)
                # pills from live/git groups
                by = {c.name: c for c in rep.checks}
                mapping = [
                    ("Bitwig", "Bitwig"),
                    ("REAPER", "REAPER"),
                    ("Renoise", "Renoise"),
                    ("SSE :8080", "Bitwig shared SSE :8080"),
                    ("ReMCP :19714", "Renoise ReMCP :19714"),
                    ("Git", "sync with origin/main"),
                ]
                for pill, cname in mapping:
                    c = by.get(cname)
                    if not c:
                        self.root.after(0, lambda p=pill: self._set_pill(p, None, "?"))
                        continue
                    label = "UP" if c.ok else "DOWN"
                    if cname.startswith("sync"):
                        label = "SYNC" if c.ok else "DRIFT"
                    if cname in ("Bitwig", "REAPER", "Renoise") and not c.ok:
                        label = "off"
                    self.root.after(
                        0,
                        lambda p=pill, o=c.ok, t=label: self._set_pill(p, o, t),
                    )
            except Exception as e:
                self.log(f"health failed: {e}", "bad")

        threading.Thread(target=work, daemon=True).start()

    def _auto_health(self) -> None:
        if not self.busy.get():
            self.refresh_health()
        self.root.after(12000, self._auto_health)

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
            self.log("Busy — wait for current job.", "bad")
            return
        self.busy.set(True)
        self.log(f">>> {title}", "head")
        self.log(" ".join(args) if isinstance(args, list) else str(args), "info")

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
                    self.log(line.rstrip("\n"), "info")
                rc = proc.wait()
                self.log(f"<<< exit {rc}", "ok" if rc == 0 else "bad")
            except Exception as ex:
                self.log(f"FAILED: {ex}", "bad")
            finally:
                self.busy.set(False)
                self.root.after(400, self.refresh_health)

        threading.Thread(target=work, daemon=True).start()

    def do_care(self) -> None:
        self._run_cmd("CARE (GitHub update + heal + SSE)", ["cmd", "/c", "CARE.bat"], env={"CARE_NOPAUSE": "1"})

    def do_heal(self) -> None:
        self._run_cmd(
            "HEAL",
            [_python(), str(SCRIPTS / "heal_daw_bridges.py")],
        )

    def do_update(self) -> None:
        cmd = (
            "git fetch origin main && git pull --ff-only origin main && "
            f'"{_python()}" scripts\\heal_daw_bridges.py'
        )
        self._run_cmd("UPDATE (git pull + heal)", ["cmd", "/c", cmd])

    def do_install(self) -> None:
        cmd = (
            f'"{_python()}" -m pip install --user -q -r packages\\reaper-mcp\\requirements.txt && '
            f'"{_python()}" -m pip install --user -q mcp[cli] python-osc pydantic pydantic-settings uvicorn starlette anyio && '
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
        self.log(f"Opening showcase: {path}", "head")
        webbrowser.open(path.as_uri())

    def open_file(self, path: Path) -> None:
        if not path.is_file():
            self.log(f"Missing: {path}", "bad")
            return
        self.log(f"Open {path.name}", "info")
        os.startfile(str(path))  # type: ignore[attr-defined]

    def open_cli_menu(self) -> None:
        cli = PACK / "launch_daw_mcp_cli.bat"
        if cli.is_file():
            subprocess.Popen(["cmd", "/c", "start", "DAW Horsemen CLI", str(cli)], cwd=str(PACK))
            self.log("Opened CLI menu window", "info")
        else:
            self.log("CLI bat missing", "bad")

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    # Allow --cli to fall through? GUI is default.
    if "--cli" in sys.argv:
        cli = PACK / "launch_daw_mcp_cli.bat"
        if cli.is_file():
            os.system(f'cmd /c "{cli}"')
            return 0
    app = LauncherApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
