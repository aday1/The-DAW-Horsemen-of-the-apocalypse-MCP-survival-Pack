import os
import struct


PPQ = 480


def vlq(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(out)


def beat_to_tick(beat: float) -> int:
    return int(round(beat * PPQ))


def write_midi(path: str, notes: list[tuple[float, float, int, int, int]]) -> None:
    events = []
    for start_beat, length_beat, note, velocity, channel in notes:
        start_tick = beat_to_tick(start_beat)
        end_tick = beat_to_tick(start_beat + length_beat)
        status_on = 0x90 | ((channel - 1) & 0x0F)
        status_off = 0x80 | ((channel - 1) & 0x0F)
        events.append((start_tick, 1, bytes([status_on, note & 0x7F, velocity & 0x7F])))
        events.append((end_tick, 0, bytes([status_off, note & 0x7F, 0])))

    events.sort(key=lambda e: (e[0], e[1]))

    track = bytearray()
    last_tick = 0
    for tick, _, msg in events:
        delta = tick - last_tick
        track.extend(vlq(delta))
        track.extend(msg)
        last_tick = tick

    track.extend(vlq(0))
    track.extend(b"\xFF\x2F\x00")

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ)
    chunk = b"MTrk" + struct.pack(">I", len(track)) + bytes(track)

    with open(path, "wb") as f:
        f.write(header + chunk)


def make_drums() -> list[tuple[float, float, int, int, int]]:
    notes = []
    for bar in range(4):
        base = bar * 4.0
        # Kick (C1=36): front-heavy dubstep groove
        for b in [0.0, 1.5, 2.75]:
            notes.append((base + b, 0.12, 36, 122, 1))
        # Snare (D1=38): hard backbeat
        for b in [1.0, 3.0]:
            notes.append((base + b, 0.12, 38, 120, 1))
        # Hats (F#1=42): driving 1/8 groove
        for i in range(8):
            notes.append((base + (i * 0.5) + 0.25, 0.08, 42, 78, 1))
    return notes


def make_bass() -> list[tuple[float, float, int, int, int]]:
    notes = []
    pattern = [
        (0.0, 0.38, 41),
        (0.5, 0.22, 41),
        (1.0, 0.35, 44),
        (1.5, 0.22, 41),
        (2.0, 0.35, 46),
        (2.5, 0.22, 44),
        (3.0, 0.35, 41),
        (3.5, 0.22, 39),
    ]
    for bar in range(4):
        base = bar * 4.0
        for st, ln, nt in pattern:
            notes.append((base + st, ln, nt, 110, 1))
    return notes


def make_stab() -> list[tuple[float, float, int, int, int]]:
    notes = []
    # Offbeat stabs for energy in the drop.
    for bar in range(4):
        base = bar * 4.0
        for b in [0.75, 1.75, 2.75, 3.75]:
            for nt in [53, 57, 60]:
                notes.append((base + b, 0.18, nt, 98, 1))
    return notes


def main() -> None:
    out_dir = os.path.dirname(os.path.abspath(__file__))
    write_midi(os.path.join(out_dir, "dubstep_drums_drop.mid"), make_drums())
    write_midi(os.path.join(out_dir, "dubstep_bass_wobble.mid"), make_bass())
    write_midi(os.path.join(out_dir, "dubstep_stab_offbeat.mid"), make_stab())
    print(out_dir)


if __name__ == "__main__":
    main()
