import os
import struct


PPQ = 480
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


SECTIONS = [
    ("intro", 16),
    ("groove", 16),
    ("build1", 16),
    ("drop1", 16),
    ("break", 8),
    ("build2", 8),
    ("drop2", 16),
    ("outro", 16),
]


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
        s = beat_to_tick(start_beat)
        e = beat_to_tick(start_beat + length_beat)
        on = 0x90 | ((channel - 1) & 0x0F)
        off = 0x80 | ((channel - 1) & 0x0F)
        events.append((s, 1, bytes([on, note & 0x7F, velocity & 0x7F])))
        events.append((e, 0, bytes([off, note & 0x7F, 0])))
    events.sort(key=lambda x: (x[0], x[1]))

    track = bytearray()
    last = 0
    for tick, _, msg in events:
        track.extend(vlq(tick - last))
        track.extend(msg)
        last = tick
    track.extend(vlq(0))
    track.extend(b"\xFF\x2F\x00")

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ)
    chunk = b"MTrk" + struct.pack(">I", len(track)) + bytes(track)
    with open(path, "wb") as f:
        f.write(header + chunk)


def root_for_bar(bar: int) -> int:
    # E minor -> C -> G -> D
    roots = [40, 36, 43, 38]
    return roots[bar % 4]


def chord_for_root(root: int) -> list[int]:
    # Minor triad
    return [root + 12, root + 15, root + 19]


def drums(section: str, bars: int) -> list[tuple[float, float, int, int, int]]:
    notes = []
    for bar in range(bars):
        base = bar * 4.0
        for beat in [0.0, 1.0, 2.0, 3.0]:
            notes.append((base + beat, 0.10, 36, 122, 1))

        use_snare = section in {"groove", "build1", "drop1", "build2", "drop2", "outro"}
        if use_snare:
            notes.append((base + 1.0, 0.10, 38, 114, 1))
            notes.append((base + 3.0, 0.10, 38, 118, 1))

        if section in {"build1", "build2"}:
            # Extra snare roll building into drops.
            notes.append((base + 3.5, 0.08, 38, 100, 1))
            notes.append((base + 3.75, 0.08, 38, 104, 1))

        if section in {"groove", "drop1", "drop2", "outro"}:
            for i in range(8):
                notes.append((base + (i * 0.5) + 0.25, 0.06, 42, 76, 1))
    return notes


def bass(section: str, bars: int) -> list[tuple[float, float, int, int, int]]:
    notes = []
    active = section in {"groove", "build1", "drop1", "build2", "drop2", "outro"}
    if not active:
        return notes

    for bar in range(bars):
        base = bar * 4.0
        root = root_for_bar(bar)
        # Offbeat trance bass
        for beat in [0.5, 1.5, 2.5, 3.5]:
            length = 0.30 if section not in {"drop1", "drop2"} else 0.38
            vel = 106 if section not in {"drop1", "drop2"} else 116
            notes.append((base + beat, length, root, vel, 1))
    return notes


def chords(section: str, bars: int) -> list[tuple[float, float, int, int, int]]:
    notes = []
    active = section in {"intro", "groove", "build1", "drop1", "break", "build2", "drop2", "outro"}
    if not active:
        return notes

    for bar in range(bars):
        base = bar * 4.0
        triad = chord_for_root(root_for_bar(bar))
        if section in {"drop1", "drop2", "groove"}:
            # Offbeat stabs.
            for off in [0.5, 1.5, 2.5, 3.5]:
                for n in triad:
                    notes.append((base + off, 0.26, n, 92, 1))
        elif section in {"build1", "build2"}:
            # Longer chord tension in build.
            for n in triad:
                notes.append((base + 0.0, 3.6, n, 84, 1))
        else:
            # Intro/break/outro smoother pads.
            for n in triad:
                notes.append((base + 0.0, 2.0, n, 72, 1))
                notes.append((base + 2.0, 1.8, n, 72, 1))
    return notes


def lead(section: str, bars: int) -> list[tuple[float, float, int, int, int]]:
    notes = []
    if section not in {"build1", "drop1", "build2", "drop2"}:
        return notes

    motif = [64, 67, 71, 72, 71, 67, 64, 62]
    for bar in range(bars):
        base = bar * 4.0
        for i, note in enumerate(motif):
            t = base + (i * 0.5)
            dur = 0.40 if section in {"drop1", "drop2"} else 0.28
            vel = 104 if section in {"drop1", "drop2"} else 94
            notes.append((t, dur, note, vel, 1))
    return notes


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for section, bars in SECTIONS:
        write_midi(os.path.join(OUT_DIR, f"euro_trance_drums_{section}.mid"), drums(section, bars))
        write_midi(os.path.join(OUT_DIR, f"euro_trance_bass_{section}.mid"), bass(section, bars))
        write_midi(os.path.join(OUT_DIR, f"euro_trance_chords_{section}.mid"), chords(section, bars))
        write_midi(os.path.join(OUT_DIR, f"euro_trance_lead_{section}.mid"), lead(section, bars))
    print(OUT_DIR)


if __name__ == "__main__":
    main()
