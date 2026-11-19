"""Make one illustration per scene. Free providers first, placeholder for offline tests."""
import base64
import io
import os
import time
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFont


def _fit(img, w, h):
    """Crop/scale to exactly w x h."""
    img = img.convert("RGB")
    scale = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _pollinations(prompt, w, h, seed):
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
    params = {"width": w, "height": h, "seed": seed, "nologo": "true", "model": "flux"}
    headers = {}
    if os.environ.get("POLLINATIONS_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['POLLINATIONS_TOKEN']}"
    for attempt in range(6):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=240)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                return Image.open(io.BytesIO(r.content))
        except requests.RequestException:
            pass
        time.sleep(15 * (attempt + 1))
    raise RuntimeError("Pollinations image failed after retries")


def _gemini(prompt, model):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}},
    }
    for attempt in range(5):
        r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=180)
        if r.status_code in (429, 500, 503):
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        for part in r.json()["candidates"][0]["content"]["parts"]:
            data = part.get("inlineData") or part.get("inline_data")
            if data:
                return Image.open(io.BytesIO(base64.b64decode(data["data"])))
    raise RuntimeError("Gemini image failed")


def _placeholder(prompt, w, h, i):
    """Offline stand-in so the rest of the pipeline can be tested without an image API."""
    palette = [(52, 61, 110), (74, 58, 112), (40, 82, 98), (88, 64, 96)]
    top, bottom = palette[i % 4], (20, 22, 48)
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[k] * (1 - t) + bottom[k] * t) for k in range(3)))
    for sx, sy in [(0.1, 0.1), (0.3, 0.2), (0.7, 0.12), (0.85, 0.3), (0.55, 0.08)]:
        d.ellipse([sx * w - 4, sy * h - 4, sx * w + 4, sy * h + 4], fill=(255, 244, 200))
    d.ellipse([w * 0.78, h * 0.08, w * 0.9, h * 0.08 + w * 0.12], fill=(250, 240, 210))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", h // 30)
    except OSError:
        font = ImageFont.load_default()
    words, lines, line = prompt.split()[:60], [], ""
    for wd in words:
        if len(line) + len(wd) > 70:
            lines.append(line)
            line = ""
        line += wd + " "
    lines.append(line)
    d.multiline_text((w * 0.06, h * 0.55), f"[scene {i + 1}]\n" + "\n".join(lines), fill=(230, 230, 250), font=font)
    return img


def make_images(cfg, story, out_dir, base_seed):
    icfg = cfg["images"]
    w, h, provider = icfg["width"], icfg["height"], icfg["provider"]
    paths = []
    for i, scene in enumerate(story["scenes"]):
        path = os.path.join(out_dir, f"scene_{i:02d}.png")
        prompt = f"{scene['image_prompt']}. {cfg['art_style']}"
        if provider == "pollinations":
            img = _pollinations(prompt, w, h, base_seed + i)
        elif provider == "gemini":
            img = _gemini(prompt, icfg["gemini_model"])
            time.sleep(6)  # stay inside free-tier per-minute limits
        else:
            img = _placeholder(scene["image_prompt"], w, h, i)
        _fit(img, w, h).save(path)
        paths.append(path)
        print(f"  image {i + 1}/{len(story['scenes'])}", flush=True)
    return paths
