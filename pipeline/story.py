"""Write a bedtime story (script, scene prompts, YouTube metadata) with Gemini."""
import json
import os
import random
import time

import requests

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _prompt(cfg, theme, recent_titles):
    cast = "\n".join(
        f"- {c['name']}: {c['look']}. Personality: {c['personality']}."
        for c in cfg["characters"]
    )
    words = int(cfg["channel"]["target_minutes"] * 120)  # ~120 wpm at bedtime pace
    avoid = "\n".join(f"- {t}" for t in recent_titles) or "- (none yet)"
    return f"""You write original bedtime stories for a YouTube channel called
"{cfg['channel']['name']}" for {cfg['channel']['audience']}.

Recurring characters (use 2 or 3 of them, always described exactly like this):
{cast}

Setting: {cfg['setting']}

Write ONE new story that gently teaches: {theme}.

Rules:
- About {words} words of narration in total, split into 10 to 14 scenes.
- Simple words a 3-year-old understands. Short sentences. Warm, slow, soothing.
- Nothing scary, violent, sad without comfort, or commercial. No brand names.
- Gentle repetition kids enjoy (a small repeated phrase is good).
- The last scene must wind down: characters get sleepy and say goodnight,
  and the narrator softly says goodnight to the child watching.
- Do not reuse these earlier titles or plots:
{avoid}

For every scene give an image_prompt describing ONLY what is visible:
which characters (repeat their full look description each time so the
illustrator draws them consistently), what they are doing, the place,
time of day. No text or letters in images.

YouTube metadata:
- title: under 70 characters, warm and searchable, e.g. includes
  "Bedtime Story" and the main character. No clickbait, no ALL CAPS.
- description: 2 short paragraphs for parents (what happens, what it
  teaches), then a line inviting them to subscribe for a new calm story.
- tags: 10 to 15 relevant search phrases.

Return JSON only, matching this shape:
{{"title": str, "description": str, "tags": [str],
  "lesson": str,
  "scenes": [{{"narration": str, "image_prompt": str}}]}}"""


def write_story(cfg, theme, recent_titles):
    from . import gemini

    body = {
        "contents": [{"parts": [{"text": _prompt(cfg, theme, recent_titles)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0},
    }
    url = gemini.url(gemini.pick("text", cfg["story"]["model"]))
    for attempt in range(5):
        r = requests.post(url, headers=gemini.headers(), json=body, timeout=180)
        if r.status_code in (429, 500, 503):
            time.sleep(20 * (attempt + 1))
            continue
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        story = json.loads(text)
        if 6 <= len(story.get("scenes", [])) <= 20:
            story["theme"] = theme
            return story
    raise RuntimeError("Gemini did not return a usable story")


def pick_theme(cfg, history):
    recent = {h["theme"] for h in history[-len(cfg["themes"]) // 2 :]}
    options = [t for t in cfg["themes"] if t not in recent] or cfg["themes"]
    return random.choice(options)
