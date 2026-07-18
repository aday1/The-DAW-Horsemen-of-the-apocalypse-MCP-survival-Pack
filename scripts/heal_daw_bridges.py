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
    py = shutil.which("py") or shutil.which("python") or "python"
    doc = {
        "mcpServers": {
            "bitwig": {"url": "http://127.0.0.1:8080/sse"},
            "reaper": {
                "command": py,
                "args": [str(pack / "packages" / "reaper-mcp" / "reaper_mcp_server.py")],
            },
            "renoise": {
                "command": "node",
                "args": [
                    str(pack / "packages" / "renoise-mcp-bridge" / "bridge.js")
                ],
                "cwd": str(pack / "packages" / "renoise-mcp-bridge"),
                "env": {"RENOISE_MCP_URL": "http://127.0.0.1:19714/mcp"},
            },
        }
    }
    # Claude Desktop (stdio-only UI) prefers mcp-remote shim for Bitwig
    desktop_bitwig = {
        "command": str(Path(r"C:\Program Files\nodejs\npx.cmd")),
        "args": ["-y", "mcp-remote", "http://127.0.0.1:8080/sse"],
    }
    out = pack / "mcp.generated.json"
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    desk = pack / "mcp.claude_desktop.snippet.json"
    desk.write_text(
        json.dumps({"mcpServers": {"bitwig": desktop_bitwig, **{k: v for k, v in doc["mcpServers"].items() if k != "bitwig"}}}, indent=2),
        encoding="utf-8",
    )
    print(f"  wrote {out.name} + {desk.name}")
    return out


def patch_json_mcp(path: Path, pack: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  WARN: skip {path}: {e}")
        return False
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return False
    changed = False
    # bitwig -> shared SSE url (Cursor / Claude Code). Desktop uses separate snippet.
    if "bitwig" in servers:
        want = {"url": "http://127.0.0.1:8080/sse"}
        if servers["bitwig"] != want and "mcp-remote" not in json.dumps(servers["bitwig"]):
            # keep mcp-remote if already present (Desktop)
            if not (
                isinstance(servers["bitwig"], dict)
                and "mcp-remote" in json.dumps(servers["bitwig"])
            ):
                servers["bitwig"] = want
                changed = True
    reaper_py = str(pack / "packages" / "reaper-mcp" / "reaper_mcp_server.py")
    if "reaper" in servers and isinstance(servers["reaper"], dict):
        args = servers["reaper"].get("args") or []
        if args and "DAW-Horsemen" not in str(args[0]):
            servers["reaper"]["args"] = [reaper_py]
            changed = True
        elif not args:
            servers["reaper"]["args"] = [reaper_py]
            changed = True
    renoise_js = str(pack / "packages" / "renoise-mcp-bridge" / "bridge.js")
    renoise_cwd = str(pack / "packages" / "renoise-mcp-bridge")
    if "renoise" in servers and isinstance(servers["renoise"], dict):
        r = servers["renoise"]
        if r.get("cwd") != renoise_cwd or (
            r.get("args") and "DAW-Horsemen" not in str(r["args"][0])
        ):
            r["args"] = [renoise_js]
            r["cwd"] = renoise_cwd
            r.setdefault("env", {})["RENOISE_MCP_URL"] = "http://127.0.0.1:19714/mcp"
            changed = True
    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  patched agent config: {path}")
    return changed


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

    print("[4b] Mackie / Behringer X-Touch (Bitwig template + MCU note)")
    install_mackie_xtouch(pack)

    print("[5] mcp.generated.json")
    write_mcp_generated(pack)

    print("[6] agent MCP path heal (project configs)")
    jam = pack.parent
    for rel in (".mcp.json", ".cursor/mcp.json"):
        patch_json_mcp(jam / rel, pack)
    # Claude Desktop Store path
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    desk = (
        local
        / "Packages"
        / "Claude_pzs8sxrjxfjjc"
        / "LocalCache"
        / "Roaming"
        / "Claude"
        / "claude_desktop_config.json"
    )
    if desk.is_file():
        try:
            data = json.loads(desk.read_text(encoding="utf-8"))
            servers = data.setdefault("mcpServers", {})
            py = r"C:\Users\aday\AppData\Local\Programs\Python\Python311\python.exe"
            if not Path(py).is_file():
                py = shutil.which("python") or shutil.which("py") or "python"
            npx = Path(r"C:\Program Files\nodejs\npx.cmd")
            servers["bitwig"] = {
                "command": str(npx) if npx.is_file() else "npx",
                "args": ["-y", "mcp-remote", "http://127.0.0.1:8080/sse"],
            }
            servers["reaper"] = {
                "command": py,
                "args": [
                    str(pack / "packages" / "reaper-mcp" / "reaper_mcp_server.py")
                ],
            }
            servers["renoise"] = {
                "command": "node",
                "args": [
                    str(pack / "packages" / "renoise-mcp-bridge" / "bridge.js")
                ],
                "cwd": str(pack / "packages" / "renoise-mcp-bridge"),
                "env": {"RENOISE_MCP_URL": "http://127.0.0.1:19714/mcp"},
            }
            desk.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"  patched Claude Desktop: {desk}")
        except Exception as e:
            print(f"  WARN: Claude Desktop patch failed: {e}")

    print()
    print("DONE. Next:")
    print("  1. Quit Bitwig fully, reopen (loads DawpocalypseMCP + fixed ports)")
    print("  2. Controllers: enable DawpocalypseMCP / Open Sound Control")
    print("     Receive 8005 / Send 9001 / host 127.0.0.1")
    print("  3. Launchers menu 1 = shared SSE :8080")
    print("  4. Paste mcp.generated.json into Cursor/Claude Code;")
    print("     Claude Desktop use mcp.claude_desktop.snippet.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
