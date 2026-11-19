"""Generate an original, royalty-free music-box lullaby (no copyright risk)."""
import numpy as np
import soundfile as sf

SR = 44100


def _note(freq, dur, vol=0.25):
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-t * 2.8) * (1 - np.exp(-t * 400))
    tone = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) + 0.12 * np.sin(6 * np.pi * freq * t)
    return vol * env * tone


def _pad(freqs, dur, vol=0.06):
    t = np.arange(int(dur * SR)) / SR
    env = np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 1.5)
    return vol * env * sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)


def lullaby(seconds, path, seed=0):
    rng = np.random.default_rng(seed)
    root = 261.63 * 2 ** (rng.integers(-3, 4) / 12)  # random key near middle C
    scale = [0, 2, 4, 7, 9, 12, 14, 16]  # major pentatonic, two octaves
    progression = [[0, 4, 7], [-3, 0, 4], [5, 9, 12], [7, 11, 14]]  # I vi IV V
    beat = 60 / 66  # slow tempo
    # One 4-bar melody, repeated so the tune feels familiar.
    melody = [scale[i] for i in rng.integers(0, len(scale), 16)]
    melody[-1] = 0
    bar = beat * 4
    loop = np.zeros(int(bar * 4 * SR) + SR * 3)
    for b, chord in enumerate(progression):
        start = int(b * bar * SR)
        p = _pad([root / 2 * 2 ** (s / 12) for s in chord], bar + 1.5)
        loop[start : start + len(p)] += p
        for k in range(4):
            semis = melody[b * 4 + k]
            n = _note(root * 2 ** (semis / 12) * 2, beat * 2.5)
            s = start + int(k * beat * SR)
            loop[s : s + len(n)] += n
    loop_len = int(bar * 4 * SR)
    out = np.zeros(int(seconds * SR) + len(loop))
    for s in range(0, len(out) - len(loop), loop_len):
        out[s : s + len(loop)] += loop
    out = out[: int(seconds * SR)]
    fade = int(3 * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    out /= np.max(np.abs(out)) + 1e-9
    sf.write(path, (out * 0.8).astype(np.float32), SR)
    return path
