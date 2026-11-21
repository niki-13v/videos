"""Real-instrument kids' music: write MIDI, render with FluidSynth + the free FluidR3 GM soundfont.

song() returns (mono float32 @44100, beat_times) so animation can dance on the beat.
"""
import os
import random
import subprocess
import tempfile

import mido
import numpy as np
import soundfile as sf

SR = 44100
SF2 = next((p for p in ["/usr/share/sounds/sf2/FluidR3_GM.sf2", "/usr/share/soundfonts/FluidR3_GM.sf2"] if os.path.exists(p)), None)

# Public-domain melodies: (semitones from tonic, beats). Tonic = C.
TUNES = {
    "twinkle": [(0, 1), (0, 1), (7, 1), (7, 1), (9, 1), (9, 1), (7, 2), (5, 1), (5, 1), (4, 1), (4, 1), (2, 1), (2, 1), (0, 2),
                (7, 1), (7, 1), (5, 1), (5, 1), (4, 1), (4, 1), (2, 2), (7, 1), (7, 1), (5, 1), (5, 1), (4, 1), (4, 1), (2, 2)],
    "old_macdonald": [(7, 1), (7, 1), (7, 1), (2, 1), (4, 1), (4, 1), (2, 2), (11, 1), (11, 1), (9, 1), (9, 1), (7, 3), (2, 1),
                      (7, 1), (7, 1), (7, 1), (2, 1), (4, 1), (4, 1), (2, 2), (11, 1), (11, 1), (9, 1), (9, 1), (7, 4)],
    "row_row": [(0, 1.5), (0, 1.5), (0, 1), (2, 0.5), (4, 1.5), (4, 1), (2, 0.5), (4, 1), (5, 0.5), (7, 3),
                (12, 0.5), (12, 0.5), (12, 0.5), (7, 0.5), (7, 0.5), (7, 0.5), (4, 0.5), (4, 0.5), (4, 0.5), (0, 0.5), (0, 0.5), (0, 0.5),
                (7, 1), (5, 0.5), (4, 1), (2, 0.5), (0, 3)],
    "london_bridge": [(7, 1.5), (9, 0.5), (7, 1), (5, 1), (4, 1), (5, 1), (7, 2), (2, 1), (4, 1), (5, 2), (4, 1), (5, 1), (7, 2),
                      (7, 1.5), (9, 0.5), (7, 1), (5, 1), (4, 1), (5, 1), (7, 2), (2, 2), (7, 2), (4, 1), (0, 3)],
    "mary_lamb": [(4, 1), (2, 1), (0, 1), (2, 1), (4, 1), (4, 1), (4, 2), (2, 1), (2, 1), (2, 2), (4, 1), (7, 1), (7, 2),
                  (4, 1), (2, 1), (0, 1), (2, 1), (4, 1), (4, 1), (4, 1), (4, 1), (2, 1), (2, 1), (4, 1), (2, 1), (0, 4)],
}
# GM programs that sound friendly for kids
LEADS = [12, 13, 9, 11, 8, 73, 22, 0, 108, 79]  # marimba, xylophone, glockenspiel, vibraphone, celesta, flute, harmonica, piano, kalimba, ocarina
CHORDS = [0, 4, 24, 25, 46]  # piano, e-piano, nylon gtr, steel gtr, harp
BASSES = [33, 32, 38, 58]  # finger bass, acoustic bass, synth bass, tuba
PROGRESSIONS = [[0, 7, 9, 5], [0, 5, 7, 0], [0, 9, 5, 7], [0, 5, 0, 7]]  # I V vi IV / I IV V I / I vi IV V / I IV I V


def _chord(root):
    minor = root % 12 in (2, 4, 9)
    return [root, root + (3 if minor else 4), root + 7]


def _harmonize(melody):
    """One chord per bar from I, IV, V, vi that fits the bar's first note."""
    beats, bars, pos = 0.0, [], 0.0
    total = sum(b for _, b in melody)
    nbars = int(np.ceil(total / 4))
    for bar in range(nbars):
        notes = [s % 12 for s, b in _notes_at(melody, bar * 4, bar * 4 + 4)]
        best = max([0, 5, 7, 9], key=lambda r: sum(1 for n in notes if n in [x % 12 for x in _chord(r)]) + (0.5 if r == 0 else 0))
        bars.append(best)
    return bars


def _notes_at(melody, a, b):
    pos, out = 0.0, []
    for s, d in melody:
        if a <= pos < b:
            out.append((s, d))
        pos += d
    return out


def _gen_melody(rnd, bars=8):
    """Simple catchy melody: 2-bar motif, repeated with variation, ends on tonic."""
    scale = [0, 2, 4, 5, 7, 9, 12]
    rhythms = [[1, 1, 1, 1], [0.5, 0.5, 1, 2], [1, 0.5, 0.5, 2], [1.5, 0.5, 1, 1], [0.5, 0.5, 0.5, 0.5, 2]]
    def phrase():
        out = []
        for _ in range(2):
            for d in rnd.choice(rhythms):
                out.append((rnd.choice(scale), d))
        return out
    a, b = phrase(), phrase()
    a2 = a[:-1] + [(rnd.choice([0, 4, 7]), a[-1][1])]
    mel = a + b + a + a2
    mel[-1] = (0, mel[-1][1])
    return mel


def song(seconds, seed=0, tune=None, bpm=None, energy=1.0):
    """Arrange and render a looping kids' track at least `seconds` long."""
    rnd = random.Random(seed)
    bpm = bpm or rnd.choice([104, 110, 116, 120, 124])
    key = rnd.choice([0, 2, 5, 7, -3])  # C, D, F, G, A
    melody = TUNES[tune] if tune else _gen_melody(rnd)
    mel_beats = sum(d for _, d in melody)
    mel_bars = int(np.ceil(mel_beats / 4))
    chords = _harmonize(melody) if tune else (rnd.choice(PROGRESSIONS) * 4)[:mel_bars]
    spb = 60 / bpm
    total_bars = int(np.ceil((seconds + 2) / (spb * 4))) + 1

    mid = mido.MidiFile(ticks_per_beat=480)
    TPB = 480
    tracks = {}

    def track(ch, program=None):
        if ch not in tracks:
            tr = mido.MidiTrack()
            mid.tracks.append(tr)
            tracks[ch] = (tr, [])
            if program is not None:
                tracks[ch][1].append((0, mido.Message("program_change", channel=ch, program=program)))
        return tracks[ch][1]

    def note(ch, pitch, start_beat, dur_beats, vel):
        ev = track(ch)
        a = int(start_beat * TPB)
        b = int((start_beat + dur_beats) * TPB) - 10
        ev.append((a, mido.Message("note_on", channel=ch, note=int(pitch), velocity=int(max(1, min(127, vel))))))
        ev.append((b, mido.Message("note_off", channel=ch, note=int(pitch), velocity=0)))

    tr0 = mido.MidiTrack()
    mid.tracks.insert(0, tr0)
    tr0.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm)))

    leads = rnd.sample(LEADS, 4)
    track(0, leads[0])
    track(1, rnd.choice(CHORDS))
    track(2, rnd.choice(BASSES))
    track(3, 48)  # strings pad (quiet)
    track(9)
    intro = 2
    section_len = mel_bars
    for bar in range(total_bars):
        b0 = bar * 4
        in_intro = bar < intro
        mb = (bar - intro) % section_len
        section = (bar - intro) // section_len
        root = key + 60 + (chords[mb % len(chords)] if not in_intro else 0)
        ch_notes = _chord(root - 12)
        # lead: switch instrument each section to keep it fresh
        if not in_intro and mb == 0:
            track(0).append((int(b0 * TPB), mido.Message("program_change", channel=0, program=leads[section % len(leads)])))
        if not in_intro:
            for s, d in _notes_at(melody, mb * 4, mb * 4 + 4):
                pos = sum(dd for _, dd in melody[: melody.index((s, d)) if False else 0])
            pos = 0.0
            for s, d in melody:
                if mb * 4 <= pos < mb * 4 + 4:
                    note(0, key + 72 + s, b0 + (pos - mb * 4), d * 0.95, 96 * energy + rnd.randint(-6, 6))
                pos += d
        # chords: off-beat stabs + sustained pad
        for beat in (1, 3) if rnd.random() < 2 else ():
            for p in ch_notes:
                note(1, p + 12, b0 + beat, 0.45, 62)
        for beat in (0.5, 2.5):
            for p in ch_notes:
                note(1, p + 12, b0 + beat, 0.3, 48)
        for p in ch_notes:
            note(3, p, b0, 4, 34)
        # bass: bouncy root-fifth pattern
        bass_root = root - 24
        for beat, off in [(0, 0), (1, 7), (1.5, 12), (2, 0), (3, 7), (3.5, 5)]:
            note(2, bass_root + off, b0 + beat, 0.45, 92)
        # drums
        fill = (bar - intro) % 8 == 7
        for beat in (0, 2, 2.5) if not in_intro or bar == intro - 1 else (0, 2):
            note(9, 36, b0 + beat, 0.2, 110)
        for beat in (1, 3):
            note(9, 38 if rnd.random() < 0.5 else 39, b0 + beat, 0.2, 95)
        for k in range(8):
            note(9, 42, b0 + k * 0.5, 0.1, 70 if k % 2 else 85)
        if energy > 0.9 and not in_intro:
            for k in range(16):
                if k % 4 == 2:
                    note(9, 54, b0 + k * 0.25, 0.1, 55)
        if fill:
            for k in range(4):
                note(9, 38, b0 + 3 + k * 0.25, 0.1, 70 + k * 12)
        if not in_intro and mb == 0:
            note(9, 49, b0, 1, 90)

    for ch, (tr, events) in tracks.items():
        events.sort(key=lambda e: (e[0], 0 if e[1].type == "note_off" else 1))
        last = 0
        for tick, msg in events:
            tr.append(msg.copy(time=tick - last))
            last = tick

    with tempfile.TemporaryDirectory() as td:
        mpath, wpath = os.path.join(td, "s.mid"), os.path.join(td, "s.wav")
        mid.save(mpath)
        subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.7", "-r", str(SR), "-F", wpath, SF2, mpath],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio, sr = sf.read(wpath, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    n = int(seconds * SR)
    audio = np.pad(audio, (0, max(0, n - len(audio))))[:n]
    fade = int(1.5 * SR)
    audio[-fade:] *= np.linspace(1, 0, fade)
    audio /= np.max(np.abs(audio)) + 1e-9
    beats = np.arange(0, seconds, spb)
    return audio * 0.9, dict(bpm=bpm, beats=beats, spb=spb, bar_start=intro * 4 * spb)
