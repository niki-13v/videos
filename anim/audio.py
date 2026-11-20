"""Speech, sound effects and an upbeat original tune, mixed on one timeline."""
import os
import sys

import numpy as np

SR = 44100
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class Mixer:
    def __init__(self, seconds):
        self.buf = np.zeros(int(seconds * SR) + SR * 5, dtype=np.float32)
        self.speech = np.zeros_like(self.buf)

    def add(self, t, samples, gain=1.0, speech=False):
        i = int(t * SR)
        n = min(len(samples), len(self.buf) - i)
        self.buf[i : i + n] += samples[:n] * gain
        if speech:
            self.speech[i : i + n] += samples[:n]

    def mouth_track(self, fps, n_frames):
        """Per-frame mouth openness 0..1 from the speech loudness."""
        hop = SR // fps
        env = np.array([np.sqrt(np.mean(self.speech[k * hop : (k + 1) * hop] ** 2)) for k in range(n_frames)])
        if env.max() > 0:
            env = np.clip(env / (np.percentile(env[env > 0], 90) + 1e-9), 0, 1)
        return env

    def finish(self, seconds, music):
        out = self.buf[: int(seconds * SR)]
        m = music[: len(out)]
        # duck the music while someone is talking
        sp = np.abs(self.speech[: len(out)])
        k = SR // 10
        env = np.convolve(sp, np.ones(k) / k, mode="same")
        duck = 1 - 0.55 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
        out = out + m * duck
        return out / (np.max(np.abs(out)) + 1e-9) * 0.9


class Voice:
    def __init__(self, voice="af_bella", speed=1.0):
        from kokoro_onnx import Kokoro
        from pipeline.voice import _ensure_models

        self.k = Kokoro(*_ensure_models())
        self.voice, self.speed = voice, speed

    def say(self, text, speed=None):
        s, sr = self.k.create(text, voice=self.voice, speed=speed or self.speed, lang="en-us")
        s = np.interp(np.arange(0, len(s), sr / SR), np.arange(len(s)), s).astype(np.float32)
        # trim silence
        nz = np.where(np.abs(s) > 0.01)[0]
        return s[nz[0] : nz[-1] + 1] if len(nz) else s


def _t(d):
    return np.arange(int(d * SR)) / SR


def sfx_pop():
    t = _t(0.18)
    f = 300 + 900 * t / 0.18
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 22) * 0.6).astype(np.float32)


def sfx_ding():
    t = _t(1.2)
    s = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(1318, 0.5), (1976, 0.3), (2637, 0.15)])
    return (s * np.exp(-t * 4) * 0.6).astype(np.float32)


def sfx_tick():
    t = _t(0.05)
    return (np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 90) * 0.35).astype(np.float32)


def sfx_whoosh():
    t = _t(0.45)
    n = np.random.default_rng(1).normal(size=len(t))
    n = np.convolve(n, np.ones(8) / 8, mode="same")
    return (n * np.sin(np.pi * t / 0.45) * 0.25).astype(np.float32)


def sfx_boing():
    t = _t(0.4)
    f = 220 + 160 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 5)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * 0.5).astype(np.float32)


def music_bouncy(seconds, seed=0):
    """Original cheerful xylophone + bass loop, 120 bpm, in C major."""
    rng = np.random.default_rng(seed)
    beat = 0.5
    chords = [[0, 4, 7], [5, 9, 12], [7, 11, 14], [0, 4, 7]]  # I IV V I
    root = 261.63 * 2 ** (int(rng.integers(-2, 3)) / 12)
    scale = [0, 2, 4, 7, 9, 12]
    mel = [scale[i] for i in rng.integers(0, len(scale), 32)]
    loop_len = int(beat * 16 * SR)
    loop = np.zeros(loop_len + SR, dtype=np.float32)

    def tone(freq, dur, decay, vol, harm=(1, 0.3)):
        t = _t(dur)
        w = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harm))
        return (w * np.exp(-t * decay) * (1 - np.exp(-t * 300)) * vol).astype(np.float32)

    for b, ch in enumerate(chords):
        for k in range(4):
            s = int((b * 4 + k) * beat * SR)
            bass = tone(root / 4 * 2 ** (ch[0] / 12), beat * 0.9, 5, 0.35, (1, 0.5, 0.2))
            loop[s : s + len(bass)] += bass
            for half in (0, 1):
                note = mel[(b * 8 + k * 2 + half) % 32]
                if (k * 2 + half) % 3 == 2:
                    note = ch[(k + half) % 3]
                x = tone(root * 2 * 2 ** (note / 12), 0.6, 9, 0.22, (1, 0.25, 0.1))
                ss = s + int(half * beat / 2 * SR)
                loop[ss : ss + len(x)] += x
            # soft shaker
            n = np.random.default_rng(b * 4 + k).normal(size=int(0.04 * SR)).astype(np.float32)
            n *= np.exp(-_t(0.04) * 80).astype(np.float32) * 0.05
            sh = s + int(beat / 2 * SR)
            loop[sh : sh + len(n)] += n
    total = int(seconds * SR)
    out = np.zeros(total + len(loop), dtype=np.float32)
    for s in range(0, total, loop_len):
        out[s : s + len(loop)] += loop
    out = out[:total]
    out[-SR:] *= np.linspace(1, 0, SR)
    return out / (np.max(np.abs(out)) + 1e-9) * 0.22
