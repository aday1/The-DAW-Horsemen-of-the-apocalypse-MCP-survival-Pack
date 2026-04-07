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


def build_drums(section: str, bars: int) -> list[tuple[float, float, int, int, int]]:
    notes: list[tuple[float, float, int, int, int]] = []
    for bar in range(bars):
        base = bar * 4.0

        # Kick: 4x4 foundation.
        for beat in [0.0, 1.0, 2.0, 3.0]:
            vel = 124 if beat in (0.0, 2.0) else 118
            notes.append((base + beat, 0.11, 36, vel, 1))

        # Add a pickup kick in drive/drop sections.
        if section in {"groove", "drop1", "drop2", "outro"}:
            notes.append((base + 3.5, 0.10, 36, 98, 1))

        # Snare/clap backbeat.
        if section != "intro":
            notes.append((base + 1.0, 0.11, 38, 116, 1))
            notes.append((base + 3.0, 0.11, 38, 121, 1))

        # Closed hats.
        if section in {"groove", "build1", "drop1", "build2", "drop2", "outro"}:
            for i in range(8):
                t = base + (i * 0.5) + 0.25
                vel = 74 + (i % 2) * 8
                notes.append((t, 0.055, 42, vel, 1))

        # Open hat for groove.
        if section in {"groove", "drop1", "drop2", "outro"}:
            notes.append((base + 1.5, 0.10, 46, 84, 1))
            notes.append((base + 3.5, 0.10, 46, 88, 1))

        # Build snare roll in final two bars.
        if section in {"build1", "build2"} and bar >= bars - 2:
            for s in range(8):
                t = base + (s * 0.25)
                notes.append((t, 0.05, 38, 90 + s * 4, 1))

    return notes


def main() -> None:
    for section, bars in SECTIONS:
        path = os.path.join(OUT_DIR, f"euro_trance_drums_{section}.mid")
        write_midi(path, build_drums(section, bars))
    print(OUT_DIR)


if __name__ == "__main__":
    main()
