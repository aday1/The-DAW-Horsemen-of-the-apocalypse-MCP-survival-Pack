#!/usr/bin/env python3
"""Structured health status for DAW Horsemen (GUI + CLI)."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    group: str = ""


@dataclass
class HealthReport:
    pack: str
    checks: list[Check] = field(default_factory=list)
    fail_count: int = 0

    def add(self, group: str, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name=name, ok=ok, detail=detail, group=group))
        if not ok:
            self.fail_count += 1

    def by_group(self) -> dict[str, list[Check]]:
        out: dict[str, list[Check]] = {}
        for c in self.checks:
            out.setdefault(c.group, []).append(c)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack": self.pack,
            "fail_count": self.fail_count,
            "checks": [asdict(c) for c in self.checks],
        }


def pack_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _http_ok(url: str, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read(200).decode("utf-8", errors="replace")
            return True, body.strip()[:120]
    except Exception as e:
        return False, str(e)[:120]


def _proc_running(*names: str) -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"],
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return False
    low = out.lower()
    needles = [n.lower() for n in names]
    # Bitwig process is often BitwigStudioApp.exe
    if any("bitwig" in n for n in needles):
        needles.extend(["bitwigstudioapp", "bitwig studio"])
    return any(n in low for n in needles)


def _cmdline_has(needle: str) -> bool:
    try:
        import ctypes
        from ctypes import wintypes

        # Fallback: wmic is gone on some boxes; use tasklist + netstat for ports
        _ = ctypes  # keep import used on Windows
        _ = wintypes
    except Exception:
        pass
    try:
        ps = (
            "Get-CimInstance Win32_Process | "
            f"Where-Object {{ $_.CommandLine -match '{needle}' }} | "
            "Select-Object -First 1 -ExpandProperty ProcessId"
        )
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps,
            ],
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=8,
        )
        return bool(out.strip())
    except Exception:
        return False


def _tcp_listen(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.6):
            return True
    except OSError:
        # connect succeeding means something accepts; for listen check use bind fail
        pass
    # Better: try bind — if fails, something is listening (or firewalled)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, port))
        return False  # we bound = nothing listening
    except OSError:
        return True
    finally:
        s.close()


def _file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(pack: Path | None = None) -> HealthReport:
    pack = (pack or pack_root()).resolve()
    rep = HealthReport(pack=str(pack))

    # git — MSI/ZIP installs have no .git; that is Info, not a hard fail for GUI
    git_dir = pack / ".git"
    if not git_dir.exists():
        rep.add("git", "origin", True, "MSI/ZIP install (no .git)")
        rep.add("git", "sync with origin/main", True, "use GitHub Releases to update")
    else:
        try:
            remote = subprocess.check_output(
                ["git", "-C", str(pack), "remote", "get-url", "origin"],
                text=True,
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).strip()
            ok = "The-DAW-Horsemen" in remote or "DAW-Horsemen" in remote
            rep.add("git", "origin", ok, remote)
        except Exception as e:
            rep.add("git", "origin", False, str(e)[:100])

        try:
            subprocess.check_call(
                ["git", "-C", str(pack), "fetch", "origin", "--quiet"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=30,
            )
            counts = subprocess.check_output(
                ["git", "-C", str(pack), "rev-list", "--left-right", "--count", "origin/main...HEAD"],
                text=True,
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).strip()
            synced = counts in ("0\t0", "0 0", "0\t0\n")
            rep.add("git", "sync with origin/main", synced, counts.replace("\t", " / "))
            head = subprocess.check_output(
                ["git", "-C", str(pack), "rev-parse", "--short", "HEAD"],
                text=True,
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).strip()
            rep.add("git", "HEAD", True, head)
        except Exception as e:
            rep.add("git", "sync with origin/main", False, str(e)[:100])

    # packages
    need = [
        "packages/bitwig-mcp-server/serve_sse.py",
        "packages/bitwig-mcp-server/run_bitwig_mcp_shared.bat",
        "packages/reaper-mcp/reaper_mcp_server.py",
        "packages/reaper-mcp/reaper_mcp_bridge.lua",
        "packages/renoise-mcp-bridge/bridge.js",
        "packages/renoise-mcp-bridge/com.renoise.ReMCP_v0.1_api6.xrnx",
        "drivebymossvaday.bwextension",
        "launcher_gui.py",
    ]
    for rel in need:
        p = pack / rel.replace("/", os.sep)
        rep.add("packages", rel, p.is_file(), str(p) if p.is_file() else "missing")

    # installed bridges
    lua_pack = pack / "packages" / "reaper-mcp" / "reaper_mcp_bridge.lua"
    lua_inst = Path(os.environ.get("APPDATA", "")) / "REAPER" / "Scripts" / "reaper_mcp_bridge.lua"
    ha, hb = _file_hash(lua_pack), _file_hash(lua_inst)
    rep.add(
        "bridges",
        "REAPER lua",
        bool(ha and hb and ha == hb),
        "match" if ha and hb and ha == hb else f"pack={bool(ha)} inst={bool(hb)}",
    )

    ext_pack = pack / "DawpocalypseMCP.bwextension"
    if not ext_pack.is_file():
        ext_pack = pack / "drivebymossvaday.bwextension"
    ext_inst = (
        Path.home()
        / "Documents"
        / "Bitwig Studio"
        / "Extensions"
        / "DawpocalypseMCP.bwextension"
    )
    ha, hb = _file_hash(ext_pack), _file_hash(ext_inst)
    rep.add(
        "bridges",
        "Bitwig extension",
        bool(ha and hb and ha == hb),
        "match" if ha and hb and ha == hb else f"pack={bool(ha)} inst={bool(hb)}",
    )

    remcp = (
        Path(os.environ.get("APPDATA", ""))
        / "Renoise"
        / "V3.5.4"
        / "Scripts"
        / "Tools"
        / "com.renoise.ReMCP.xrnx"
    )
    # Installed tool may be a folder (.xrnx unpacked) or a zip file
    rep.add(
        "bridges",
        "Renoise ReMCP",
        remcp.exists(),
        str(remcp) if remcp.exists() else "missing",
    )

    # agents — pack-local always; jam only when parent is a real project
    agent_paths: list[tuple[str, Path]] = [
        ("pack/.mcp.json", pack / ".mcp.json"),
        ("pack/.cursor/mcp.json", pack / ".cursor" / "mcp.json"),
    ]
    parent = pack.parent
    if parent.name.lower() != "programs":
        agent_paths.extend(
            [
                (".mcp.json", parent / ".mcp.json"),
                (".cursor/mcp.json", parent / ".cursor" / "mcp.json"),
            ]
        )
    jam = Path(r"E:\ChiptuneClaude")
    if jam.is_dir() and jam.resolve() != pack.resolve():
        agent_paths.extend(
            [
                ("jam/.mcp.json", jam / ".mcp.json"),
                ("jam/.cursor/mcp.json", jam / ".cursor" / "mcp.json"),
            ]
        )
    seen_agent: set[str] = set()
    for label, path in agent_paths:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen_agent:
            continue
        seen_agent.add(key)
        if not path.is_file():
            # Missing jam configs are soft; pack configs matter more
            soft = label.startswith("jam/") or label.startswith(".")
            if soft:
                continue
            rep.add("agents", label, False, "missing")
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            bw = (data.get("mcpServers") or {}).get("bitwig") or {}
            ok = "8080/sse" in json.dumps(bw)
            rep.add("agents", f"{label} bitwig SSE", ok, json.dumps(bw)[:80])
        except Exception as e:
            rep.add("agents", label, False, str(e)[:80])

    # live
    bitwig = _proc_running("BitwigStudio", "Bitwig Studio")
    reaper = _proc_running("reaper")
    renoise = _proc_running("Renoise")
    rep.add("live", "Bitwig", bitwig, "running" if bitwig else "not running")
    rep.add("live", "REAPER", reaper, "running" if reaper else "not running")
    rep.add("live", "Renoise", renoise, "running" if renoise else "not running")

    sse_proc = _cmdline_has("serve_sse")
    sse_http, sse_body = _http_ok("http://127.0.0.1:8080/healthz")
    rep.add(
        "live",
        "Bitwig shared SSE :8080",
        sse_http,
        sse_body if sse_http else ("process up, healthz down" if sse_proc else "down"),
    )
    mon_ok = _tcp_listen(8765)
    rep.add("live", "Bitwig monitor :8765", mon_ok, "listen" if mon_ok else "down")

    remcp_ok, remcp_body = _http_ok("http://127.0.0.1:19714/health")
    rep.add(
        "live",
        "Renoise ReMCP :19714",
        remcp_ok,
        remcp_body if remcp_ok else "start Tools -> Renoise MCP",
    )

    # ports snapshot as named checks (GUI pills)
    for p in ports_snapshot():
        # OSC free is normal when Bitwig off — do not count as health failure
        soft = p["name"].startswith("OSC ") and not p["ok"]
        if soft:
            rep.checks.append(
                Check(name=p["name"], ok=True, detail=f"{p['detail']} (Bitwig off OK)", group="ports")
            )
        else:
            rep.add("ports", p["name"], p["ok"], p["detail"])

    # update — available update is news, not a health failure
    upd = check_github_update(pack)
    rep.checks.append(
        Check(
            name="GitHub release",
            ok=True,
            detail=upd["detail"],
            group="update",
        )
    )

    return rep


# Known Horsemen wire map (for tray tooltip + GUI)
PORT_DEFS: list[dict[str, Any]] = [
    {"name": "SSE :8080", "kind": "http", "url": "http://127.0.0.1:8080/healthz", "role": "shared Bitwig MCP"},
    {"name": "OSC recv :8005", "kind": "udp", "port": 8005, "role": "Bitwig OSC in (DrivenByMoss)"},
    {"name": "OSC send :9001", "kind": "udp", "port": 9001, "role": "Bitwig OSC out (one owner)"},
    {"name": "monitor :8765", "kind": "tcp", "port": 8765, "role": "Bitwig MCP monitor"},
    {"name": "ReMCP :19714", "kind": "http", "url": "http://127.0.0.1:19714/health", "role": "Renoise ReMCP"},
]


def _udp_in_use(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind((host, port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def ports_snapshot() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in PORT_DEFS:
        if d["kind"] == "http":
            ok, body = _http_ok(d["url"])
            out.append(
                {
                    "name": d["name"],
                    "ok": ok,
                    "detail": body if ok else "down",
                    "role": d["role"],
                }
            )
        elif d["kind"] == "udp":
            ok = _udp_in_use(int(d["port"]))
            out.append(
                {
                    "name": d["name"],
                    "ok": ok,
                    "detail": "bound" if ok else "free",
                    "role": d["role"],
                }
            )
        else:
            ok = _tcp_listen(int(d["port"]))
            out.append(
                {
                    "name": d["name"],
                    "ok": ok,
                    "detail": "listen" if ok else "closed",
                    "role": d["role"],
                }
            )
    return out


def local_version(pack: Path | None = None) -> str:
    pack = (pack or pack_root()).resolve()
    vf = pack / "VERSION"
    if vf.is_file():
        return vf.read_text(encoding="utf-8").strip()
    return "0.0.0"


def _parse_ver(s: str) -> tuple[int, ...]:
    s = s.strip().lstrip("vV")
    parts: list[int] = []
    for p in s.split("."):
        try:
            parts.append(int("".join(ch for ch in p if ch.isdigit()) or "0"))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def check_github_update(pack: Path | None = None) -> dict[str, Any]:
    """Compare local VERSION to GitHub latest release (works for MSI + git clone)."""
    pack = (pack or pack_root()).resolve()
    local = local_version(pack)
    api = (
        "https://api.github.com/repos/aday1/"
        "The-DAW-Horsemen-of-the-apocalypse-MCP-survival-Pack/releases/latest"
    )
    try:
        req = urllib.request.Request(
            api,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "DAW-Horsemen-GUI",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        tag = str(data.get("tag_name") or "").strip()
        remote = tag.lstrip("vV")
        url = str(data.get("html_url") or "")
        msi = ""
        for a in data.get("assets") or []:
            name = str(a.get("name") or "")
            if name.lower().endswith(".msi"):
                msi = str(a.get("browser_download_url") or "")
                break
        available = _parse_ver(remote) > _parse_ver(local)
        detail = f"local {local} / latest {remote}"
        if available:
            detail += " - UPDATE available"
        else:
            detail += " - current"
        return {
            "available": available,
            "local": local,
            "remote": remote,
            "tag": tag,
            "url": url,
            "msi_url": msi,
            "detail": detail,
            "ok": True,
        }
    except Exception as e:
        return {
            "available": False,
            "local": local,
            "remote": "",
            "tag": "",
            "url": "",
            "msi_url": "",
            "detail": f"check failed: {str(e)[:100]}",
            "ok": False,
        }


def tray_summary(rep: HealthReport, upd: dict[str, Any] | None = None) -> str:
    """Short multiline string for tray tooltip (Windows ~127 char soft limit — keep tight)."""
    by = {c.name: c for c in rep.checks}
    bits = []
    for name, short in (
        ("Bitwig shared SSE :8080", "SSE"),
        ("Renoise ReMCP :19714", "ReMCP"),
        ("Bitwig", "BW"),
        ("REAPER", "RP"),
        ("Renoise", "RN"),
    ):
        c = by.get(name)
        if c:
            bits.append(f"{short}:{'OK' if c.ok else 'NO'}")
    line1 = " ".join(bits) if bits else "health?"
    if upd and upd.get("available"):
        line2 = f"UPD {upd.get('local')}->{upd.get('remote')}"
    else:
        line2 = f"v{upd.get('local') if upd else local_version()}"
    # tooltip max ~128 on classic tray
    s = f"Horsemen {line2} | {line1}"
    return s[:120]


def format_report(rep: HealthReport) -> str:
    lines = [
        f"== DAW HORSEMEN HEALTH ==",
        f"Pack: {rep.pack}",
        "",
    ]
    for group, checks in rep.by_group().items():
        lines.append(f"[{group}]")
        for c in checks:
            mark = "OK " if c.ok else "BAD"
            extra = f"  {c.detail}" if c.detail else ""
            lines.append(f"  {mark}  {c.name}{extra}")
        lines.append("")
    if rep.fail_count:
        lines.append(f"RESULT: {rep.fail_count} issue(s) need attention.")
    else:
        lines.append("RESULT: healthy (or idle-ready).")
    return "\n".join(lines)


def main() -> int:
    rep = collect()
    print(format_report(rep))
    return 1 if rep.fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
