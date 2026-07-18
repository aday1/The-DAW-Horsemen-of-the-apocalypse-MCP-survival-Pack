#!/usr/bin/env python3
"""Heal DAW Horsemen bridges + Bitwig OSC prefs for THIS machine.

- Sync Bitwig extension / REAPER lua / tip Renoise ReMCP
- Rename controller label OSC-vaday -> DawpocalypseMCP (extension + prefs)
- Fix Bitwig OSC ports: receive 8005, send 9001 (prefs store IEEE doubles)
- Write mcp.generated.json with absolute paths
- Optionally rewrite known agent MCP configs to Horsemen paths + shared SSE

Close Bitwig before prefs patch for a clean write (script still patches; Bitwig
may overwrite if left open).
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import sys
import zipfile
from pathlib import Path

NEW_NAME = "DawpocalypseMCP"
OLD_NAME = "OSC-vaday"
RECV_PORT = 8005
SEND_PORT = 9001


def pack_root() -> Path:
    return Path(__file__).resolve().parents[1]


def bitwig_ext_dir() -> Path:
    return Path.home() / "Documents" / "Bitwig Studio" / "Extensions"


def bitwig_prefs_path() -> Path | None:
    prefs = Path(os.environ.get("LOCALAPPDATA", "")) / "Bitwig Studio" / "prefs"
    if not prefs.is_dir():
        return None
    cands = sorted(prefs.glob("*.prefs"), key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None


def java_replace_utf8(data: bytes, old: str, new: str) -> tuple[bytes, int]:
    """Replace CONSTANT_Utf8 entries in a .class file (tag=1, u2 len, bytes)."""
    old_b, new_b = old.encode("utf-8"), new.encode("utf-8")
    out = bytearray()
    i = 0
    n = 0
    while i < len(data):
        if (
            i + 3 + len(old_b) <= len(data)
            and data[i] == 1
            and int.from_bytes(data[i + 1 : i + 3], "big") == len(old_b)
            and data[i + 3 : i + 3 + len(old_b)] == old_b
        ):
            out.append(1)
            out.extend(len(new_b).to_bytes(2, "big"))
            out.extend(new_b)
            i += 3 + len(old_b)
            n += 1
            continue
        out.append(data[i])
        i += 1
    return bytes(out), n


def rebuild_extension(src_ext: Path, dest_ext: Path) -> None:
    tmp = dest_ext.with_suffix(".tmp.zip")
    if tmp.exists():
        tmp.unlink()
    patched = 0
    with zipfile.ZipFile(src_ext, "r") as zin, zipfile.ZipFile(
        tmp, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            raw = zin.read(info.filename)
            if info.filename.endswith("OSCControllerDefinition.class"):
                raw, n = java_replace_utf8(raw, OLD_NAME, NEW_NAME)
                patched += n
            # keep artifact id in maven metadata readable
            if info.filename.endswith(("pom.xml", "pom.properties", "MANIFEST.MF")):
                try:
                    text = raw.decode("utf-8")
                    text2 = text.replace("drivebymossvaday", "dawpocalypse-mcp").replace(
                        OLD_NAME, NEW_NAME
                    )
                    if "vaday" in text2.lower():
                        text2 = text2.replace("vaday", "dawpocalypse")
                    raw = text2.encode("utf-8")
                except UnicodeDecodeError:
                    pass
            zout.writestr(info, raw)
    if patched < 1:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"did not find {OLD_NAME} in OSCControllerDefinition.class")
    dest_ext.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp), str(dest_ext))
    print(f"  extension rebuilt -> {dest_ext} (renamed {patched} class string(s))")


def prefs_replace_pascal_string(blob: bytes, old: str, new: str) -> tuple[bytes, int]:
    """Bitwig string field: 0x08 + u32be length + utf8 bytes."""
    old_b, new_b = old.encode("utf-8"), new.encode("utf-8")
    needle = b"\x08" + len(old_b).to_bytes(4, "big") + old_b
    repl = b"\x08" + len(new_b).to_bytes(4, "big") + new_b
    n = blob.count(needle)
    if n:
        blob = blob.replace(needle, repl)
    return blob, n


def prefs_fix_ports(blob: bytes) -> tuple[bytes, int]:
    """After 'Port to receive on' keep 8005; after 'Port to send to' set 9001."""
    recv_marker = b"Port to receive on"
    send_marker = b"Port to send to (requires restart)"
    recv_d = struct.pack(">d", float(RECV_PORT))
    send_d = struct.pack(">d", float(SEND_PORT))
    wrong = struct.pack(">d", float(RECV_PORT))  # both were 8005

    def patch_after(marker: bytes, want: bytes, label: str) -> int:
        nonlocal blob
        i = blob.find(marker)
        if i < 0:
            print(f"  WARN: prefs missing {label!r}")
            return 0
        # search forward for type-07 double equal to 8005 (or already want)
        window = blob[i : i + 240]
        for j in range(len(window) - 9):
            if window[j] == 0x07:
                cur = window[j + 1 : j + 9]
                if cur in (wrong, want, struct.pack(">d", float(SEND_PORT))):
                    abs_j = i + j
                    if cur == want:
                        print(f"  {label}: already {struct.unpack('>d', want)[0]:.0f}")
                        return 0
                    blob = blob[: abs_j + 1] + want + blob[abs_j + 9 :]
                    print(
                        f"  {label}: {struct.unpack('>d', cur)[0]:.0f} -> "
                        f"{struct.unpack('>d', want)[0]:.0f}"
                    )
                    return 1
        print(f"  WARN: could not locate double for {label}")
        return 0

    n = 0
    n += patch_after(recv_marker, recv_d, "receive port")
    n += patch_after(send_marker, send_d, "send port")
    return blob, n


def heal_bitwig_prefs() -> None:
    prefs = bitwig_prefs_path()
    if not prefs:
        print("  WARN: no Bitwig prefs found")
        return
    print(f"  prefs: {prefs}")
    raw = prefs.read_bytes()
    bak = prefs.with_suffix(prefs.suffix + ".bak_horsemen")
    if not bak.exists():
        shutil.copy2(prefs, bak)
        print(f"  backup: {bak.name}")

    raw2, n_name = prefs_replace_pascal_string(raw, OLD_NAME, NEW_NAME)
    raw3, n_port = prefs_fix_ports(raw2)
    if n_name or n_port:
        prefs.write_bytes(raw3)
        print(f"  wrote prefs (name fixes={n_name}, port fixes={n_port})")
    else:
        print("  prefs already healthy or markers not found")


def sync_reaper(pack: Path) -> None:
    src = pack / "packages" / "reaper-mcp" / "reaper_mcp_bridge.lua"
    dest_dir = Path(os.environ.get("APPDATA", "")) / "REAPER" / "Scripts"
    if not src.is_file():
        print("  WARN: missing reaper_mcp_bridge.lua in pack")
        return
    if not dest_dir.parent.is_dir():
        print("  WARN: REAPER not installed (no %APPDATA%\\REAPER)")
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "reaper_mcp_bridge.lua"
    shutil.copy2(src, dest)
    print(f"  REAPER lua -> {dest}")


def disable_reaper_mcu_for_bitwig() -> None:
    """Bitwig+DrivenByMoss is Horsemen's default X-Touch home.

    Windows MIDI is exclusive — REAPER Mackie and Bitwig MCU cannot share
    the same X-Touch ports. Clear REAPER MCU/HUI csurf lines so Bitwig wins.
    """
    ini = Path(os.environ.get("APPDATA", "")) / "REAPER" / "reaper.ini"
    if not ini.is_file():
        print("  ..  no reaper.ini (skip MCU disable)")
        return
    bak = ini.with_name("reaper.ini.bak_horsemen_xtouch")
    if not bak.is_file():
        shutil.copy2(ini, bak)
    lines = ini.read_text(encoding="utf-8", errors="replace").splitlines(True)
    out: list[str] = []
    removed: list[str] = []
    for line in lines:
        if line.startswith("csurf_cnt="):
            nl = "\n" if line.endswith("\n") else ""
            out.append(f"csurf_cnt=0{nl}")
            if line.strip() != "csurf_cnt=0":
                removed.append(line.strip())
            continue
        if line.startswith("csurf_") and not line.startswith("csurf_cnt"):
            body = line.split("=", 1)[-1].strip().upper()
            if body.startswith(("MCU", "HUI")) or "MACKIE" in body or "XTOUCH" in body.replace("-", ""):
                removed.append(line.strip())
                continue
        out.append(line)
    ini.write_text("".join(out), encoding="utf-8")
    if removed:
        side = ini.parent / "horsemen_xtouch_owner.txt"
        side.write_text(
            "owner=bitwig\n"
            "reason=Horsemen default: DrivenByMoss MCU best supported on Bitwig\n"
            "disabled_reaper_csurf:\n"
            + "\n".join(removed)
            + "\nbackup="
            + str(bak)
            + "\n",
            encoding="utf-8",
        )
        print("  REAPER Mackie/MCU disabled (X-Touch -> Bitwig)")
        print(f"  backup: {bak.name}")
        print("  If REAPER was open: restart it so MIDI ports release.")
    else:
        print("  REAPER has no Mackie/MCU surface (X-Touch free for Bitwig)")


def install_mackie_xtouch(pack: Path) -> None:
    """Install Behringer X-Touch Bitwig template from pack (MCU is in DawpocalypseMCP)."""
    src = pack / "packages" / "mackie-xtouch" / "bitwig-template"
    if not src.is_dir():
        print("  WARN: packages/mackie-xtouch/bitwig-template missing")
        return
    dest = (
        Path.home()
        / "Documents"
        / "Bitwig Studio"
        / "Library"
        / "Templates"
        / "Mackie-XTouch-Behringer-Yggdrasil.bwtemplate"
    )
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    proj_src = (
        pack
        / "packages"
        / "mackie-xtouch"
        / "bitwig-project"
        / "MackieXtouch-Tracking-Start.bwproject"
    )
    if proj_src.is_file():
        proj_dest_dir = (
            Path.home()
            / "Documents"
            / "Bitwig Studio"
            / "Projects"
            / "Templates-Horsemen"
        )
        proj_dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proj_src, proj_dest_dir / proj_src.name)
        print(f"  Bitwig starter project -> {proj_dest_dir / proj_src.name}")
    print(f"  Bitwig X-Touch template -> {dest}")
    print("  MCU surface: Controllers -> DrivenByMoss -> MCU - Control Universal")
    print("  (same DawpocalypseMCP.bwextension; X-Touch is MIDI MCU, not MCP)")


def tip_renoise(pack: Path) -> None:
    remcp = (
        Path(os.environ.get("APPDATA", ""))
        / "Renoise"
        / "V3.5.4"
        / "Scripts"
        / "Tools"
        / "com.renoise.ReMCP.xrnx"
    )
    xrnx = pack / "packages" / "renoise-mcp-bridge" / "com.renoise.ReMCP_v0.1_api6.xrnx"
    if remcp.exists():
        print(f"  Renoise ReMCP OK: {remcp}")
    elif xrnx.is_file():
        print(f"  Renoise ReMCP missing - open: {xrnx}")
    else:
        print("  WARN: no ReMCP tool in pack")


def write_mcp_generated(pack: Path) -> Path:
    doc = {"mcpServers": horsemen_servers(pack, desktop=False)}
    out = pack / "mcp.generated.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    desk = pack / "mcp.claude_desktop.snippet.json"
    desk.write_text(
        json.dumps({"mcpServers": horsemen_servers(pack, desktop=True)}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"  wrote {out.name} + {desk.name}")
    return out


def _python_cmd() -> str:
    for cand in (
        Path(r"C:\Users\aday\AppData\Local\Programs\Python\Python311\python.exe"),
        Path(shutil.which("python") or ""),
        Path(shutil.which("py") or ""),
    ):
        if cand and cand.is_file():
            return str(cand)
    return shutil.which("python") or shutil.which("py") or "python"


def horsemen_servers(pack: Path, *, desktop: bool = False) -> dict:
    """Canonical MCP server blocks for this pack (absolute paths)."""
    py = _python_cmd()
    reaper_py = str(pack / "packages" / "reaper-mcp" / "reaper_mcp_server.py")
    renoise_js = str(pack / "packages" / "renoise-mcp-bridge" / "bridge.js")
    renoise_cwd = str(pack / "packages" / "renoise-mcp-bridge")
    npx = Path(r"C:\Program Files\nodejs\npx.cmd")
    if desktop:
        bitwig = {
            "command": str(npx) if npx.is_file() else "npx",
            "args": ["-y", "mcp-remote", "http://127.0.0.1:8080/sse"],
        }
    else:
        bitwig = {"url": "http://127.0.0.1:8080/sse"}
    return {
        "bitwig": bitwig,
        "reaper": {"command": py, "args": [reaper_py]},
        "renoise": {
            "command": "node",
            "args": [renoise_js],
            "cwd": renoise_cwd,
            "env": {"RENOISE_MCP_URL": "http://127.0.0.1:19714/mcp"},
        },
    }


def patch_json_mcp(path: Path, pack: Path, *, create: bool = False) -> bool:
    """Upsert bitwig/reaper/renoise into an MCP JSON file; keep other servers."""
    if not path.is_file():
        if not create:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"mcpServers": {}}
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  WARN: skip {path}: {e}")
            return False
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return False
    want = horsemen_servers(pack, desktop=False)
    changed = False
    for name, block in want.items():
        cur = servers.get(name)
        # Keep Desktop mcp-remote bitwig if somehow in a project file
        if (
            name == "bitwig"
            and isinstance(cur, dict)
            and "mcp-remote" in json.dumps(cur)
        ):
            continue
        if cur != block:
            servers[name] = block
            changed = True
    if changed or create:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  patched agent config: {path}")
    return changed


def ensure_claude_code_enabled(project_roots: list[Path]) -> None:
    """Enable bitwig/reaper/renoise in ~/.claude.json for known project roots."""
    cfg = Path.home() / ".claude.json"
    if not cfg.is_file():
        print("  ..  no ~/.claude.json (Claude Code/CLI not initialized yet)")
        return
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  WARN: ~/.claude.json unreadable: {e}")
        return
    projects = data.setdefault("projects", {})
    if not isinstance(projects, dict):
        return
    need = ["bitwig", "reaper", "renoise"]
    changed = False
    # Normalize keys Claude uses (forward slashes)
    variants = []
    for root in project_roots:
        r = str(root.resolve())
        variants.extend({r, r.replace("\\", "/"), r.replace("/", "\\")})
    for key, proj in list(projects.items()):
        if not isinstance(proj, dict):
            continue
        key_norm = key.replace("\\", "/").rstrip("/").lower()
        hit = any(
            v.replace("\\", "/").rstrip("/").lower() == key_norm
            or key_norm.endswith("/" + Path(v).name.lower())
            for v in variants
        )
        # Also match if project path contains ChiptuneClaude or DAW-Horsemen
        if not hit:
            if "chiptuneclaude" not in key_norm and "daw-horsemen" not in key_norm:
                continue
        enabled = proj.get("enabledMcpjsonServers")
        if not isinstance(enabled, list):
            enabled = []
        new = list(enabled)
        for n in need:
            if n not in new:
                new.append(n)
                changed = True
        if new != enabled:
            proj["enabledMcpjsonServers"] = new
            changed = True
            print(f"  Claude Code/CLI enabled MCP for: {key} -> {new}")
    if changed:
        cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        print("  Claude Code/CLI MCP enable list already OK (or no matching project)")


def find_claude_desktop_configs() -> list[Path]:
    found: list[Path] = []
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming = Path(os.environ.get("APPDATA", ""))
    candidates = [
        roaming / "Claude" / "claude_desktop_config.json",
        local / "Claude" / "claude_desktop_config.json",
    ]
    pkg = local / "Packages"
    if pkg.is_dir():
        for d in pkg.glob("Claude_*"):
            candidates.append(
                d / "LocalCache" / "Roaming" / "Claude" / "claude_desktop_config.json"
            )
    for c in candidates:
        if c.is_file() and c not in found:
            found.append(c)
    return found


def patch_claude_desktop(pack: Path) -> None:
    servers_want = horsemen_servers(pack, desktop=True)
    desks = find_claude_desktop_configs()
    if not desks:
        print("  ..  Claude Desktop config not found (OK if Desktop unused)")
        return
    for desk in desks:
        try:
            data = json.loads(desk.read_text(encoding="utf-8"))
            servers = data.setdefault("mcpServers", {})
            for name, block in servers_want.items():
                servers[name] = block
            desk.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"  patched Claude Desktop: {desk}")
        except Exception as e:
            print(f"  WARN: Claude Desktop patch failed ({desk}): {e}")


def main() -> int:
    pack = pack_root()
    print(f"== HEAL DAW bridges ==\n  pack: {pack}")

    src_ext = pack / "drivebymossvaday.bwextension"
    # Prefer already-renamed build if present as source of truth name
    built = pack / "DawpocalypseMCP.bwextension"
    if not src_ext.is_file() and built.is_file():
        src_ext = built
    if not src_ext.is_file():
        print("ERROR: missing drivebymossvaday.bwextension in pack root")
        return 1

    print("[1] Bitwig extension (DawpocalypseMCP)")
    rebuild_extension(src_ext, built)
    # also keep legacy filename so old docs still find a file, but install the new name
    shutil.copy2(built, bitwig_ext_dir() / "DawpocalypseMCP.bwextension")
    # remove confusing duplicate old install name if hash-identical old vaday copy
    old_inst = bitwig_ext_dir() / "drivebymossvaday.bwextension"
    if old_inst.is_file():
        # leave DrivenByMoss.bwextension alone; replace our fork
        shutil.copy2(built, old_inst)  # overwrite old fork so Bitwig sees updated class
        print(f"  also refreshed legacy name {old_inst.name}")
    print(f"  installed -> {bitwig_ext_dir() / 'DawpocalypseMCP.bwextension'}")

    print("[2] Bitwig prefs (ports + rename)")
    heal_bitwig_prefs()

    print("[3] REAPER lua")
    sync_reaper(pack)

    print("[4] Renoise ReMCP")
    tip_renoise(pack)

    print("[4b] Mackie / Behringer X-Touch (Bitwig = default owner)")
    disable_reaper_mcu_for_bitwig()
    install_mackie_xtouch(pack)

    print("[5] mcp.generated.json")
    write_mcp_generated(pack)

    print("[6] agent MCP path heal (Cursor / Claude Code / pack)")
    # Dev clone: pack lives inside a jam/repo tree (parent has .git or jam/).
    # MSI install: pack is %LOCALAPPDATA%\Programs\DAW-Horsemen — parent is NOT a project.
    jam_roots: list[Path] = []
    parent = pack.parent
    if parent.name.lower() != "programs" and (
        (parent / ".git").exists()
        or (parent / "jam").is_dir()
        or (parent / "AdLibitum.bat").is_file()
        or (parent / ".mcp.json").is_file()
    ):
        jam_roots.append(parent)
    for cand in (Path(r"E:\ChiptuneClaude"), Path.home() / "ChiptuneClaude"):
        if cand.is_dir() and cand.resolve() != pack.resolve():
            if (cand / "jam").is_dir() or (cand / "AdLibitum.bat").is_file():
                if cand not in jam_roots:
                    jam_roots.append(cand)

    for jam in jam_roots:
        patch_json_mcp(jam / ".mcp.json", pack, create=True)
        patch_json_mcp(jam / ".cursor" / "mcp.json", pack, create=True)
        patch_json_mcp(jam / ".vscode" / "mcp.json", pack, create=False)
    if not jam_roots:
        print("  ..  no jam project beside pack (MSI/ZIP install OK) — pack + Desktop only")
    patch_json_mcp(pack / ".mcp.json", pack, create=True)
    patch_json_mcp(pack / ".cursor" / "mcp.json", pack, create=True)

    print("[7] Claude Code / Claude CLI enable list")
    ensure_claude_code_enabled(jam_roots + [pack])

    print("[8] Claude Desktop")
    patch_claude_desktop(pack)

    print()
    print("DONE. Out of the box next:")
    print("  1. Quit Bitwig fully once, reopen (loads DawpocalypseMCP + ports)")
    print("  2. Controllers: enable DawpocalypseMCP / Open Sound Control")
    print("     Receive 8005 / Send 9001 / host 127.0.0.1")
    print("  3. Desktop 'DAW MCP Launchers' menu 1 = shared SSE :8080")
    print("     (CARE.bat starts SSE if it was down)")
    print("  4. Restart Cursor / Claude Desktop / Claude Code session once")
    print("  Agents already pointed at Horsemen paths + shared Bitwig SSE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
