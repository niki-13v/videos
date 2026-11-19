"""Narrate each scene with Kokoro (free, open-source, runs on CPU)."""
import os
import re
import urllib.request

import numpy as np
import soundfile as sf

MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.join(os.path.dirname(__file__), "..", "models"))
BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]

LEAD_IN, TAIL = 0.6, 1.0  # seconds of quiet around each scene's narration


def _ensure_models():
    os.makedirs(MODEL_DIR, exist_ok=True)
    for f in FILES:
        p = os.path.join(MODEL_DIR, f)
        if not os.path.exists(p):
            print(f"  downloading {f}", flush=True)
            urllib.request.urlretrieve(BASE + f, p)
    return [os.path.join(MODEL_DIR, f) for f in FILES]


def narrate(cfg, story, out_dir):
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(*_ensure_models())
    vcfg = cfg["voice"]
    clips, captions, t = [], [], 0.0
    for i, scene in enumerate(story["scenes"]):
        samples, sr = kokoro.create(scene["narration"], voice=vcfg["voice"], speed=vcfg["speed"], lang="en-us")
        audio = np.concatenate([np.zeros(int(LEAD_IN * sr)), samples, np.zeros(int(TAIL * sr))])
        path = os.path.join(out_dir, f"scene_{i:02d}.wav")
        sf.write(path, audio, sr)
        dur = len(audio) / sr
        clips.append((path, dur))

        # Captions: split narration into sentences, time them by length.
        speech = len(samples) / sr
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", scene["narration"].strip()) if s]
        total = sum(len(s) for s in sentences) or 1
        start = t + LEAD_IN
        for s in sentences:
            d = speech * len(s) / total
            captions.append((start, start + d, s))
            start += d
        t += dur
        print(f"  voice {i + 1}/{len(story['scenes'])} ({dur:.1f}s)", flush=True)
    return clips, captions


def write_srt(captions, path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    with open(path, "w") as f:
        for n, (a, b, text) in enumerate(captions, 1):
            f.write(f"{n}\n{ts(a)} --> {ts(b)}\n{text}\n\n")
