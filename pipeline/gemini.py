"""Shared Gemini helpers. Picks the newest available model so Google retiring
an old one never breaks the pipeline."""
import functools
import os
import re

import requests

BASE = "https://generativelanguage.googleapis.com/v1beta"


def headers():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set (get a free one at aistudio.google.com)")
    return {"x-goog-api-key": key}


@functools.lru_cache(None)
def _models():
    names, token = [], None
    while True:
        params = {"pageSize": 1000, **({"pageToken": token} if token else {})}
        r = requests.get(f"{BASE}/models", headers=headers(), params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        names += [
            m["name"].split("/", 1)[1]
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        token = data.get("nextPageToken")
        if not token:
            return names


def _version(name):
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


def pick(kind, preferred=None):
    """kind='text' -> newest flash text model; kind='image' -> newest flash image model."""
    names = _models()
    if preferred and preferred != "auto" and preferred in names:
        return preferred
    skip = ("tts", "audio", "live", "embedding", "thinking", "exp", "learnlm", "robotics", "computer")
    pool = [n for n in names if n.startswith("gemini") and "flash" in n and not any(s in n for s in skip)]
    if kind == "image":
        pool = [n for n in pool if "image" in n]
    else:
        pool = [n for n in pool if "image" not in n]
    if not pool:
        raise RuntimeError(f"No Gemini {kind} model available. Models: {', '.join(names)}")
    # full flash before lite; then newest version; stable before preview
    pool.sort(key=lambda n: ("lite" in n, -_version(n), "preview" in n, len(n)))
    print(f"    using {pool[0]}", flush=True)
    return pool[0]


def url(model):
    return f"{BASE}/models/{model}:generateContent"
