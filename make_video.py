"""Make one complete bedtime-story video.

    python make_video.py                     # full run (needs GEMINI_API_KEY)
    python make_video.py --story story.json  # skip the writing step, use a saved story
    python make_video.py --images placeholder  # test without an image API
"""
import argparse
import datetime as dt
import json
import os
import random
import re
import shutil

import yaml

from pipeline import images, music, render, story, voice

ROOT = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(ROOT, "history.json")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", help="use an existing story JSON instead of writing one")
    ap.add_argument("--images", help="override image provider (pollinations|gemini|placeholder)")
    ap.add_argument("--out", default=os.path.join(ROOT, "output"))
    args = ap.parse_args()

    cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yaml")))
    if args.images:
        cfg["images"]["provider"] = args.images
    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else []

    print("1/5 writing story", flush=True)
    if args.story:
        st = json.load(open(args.story))
    else:
        theme = story.pick_theme(cfg, history)
        st = story.write_story(cfg, theme, [h["title"] for h in history[-30:]])
    print(f"    {st['title']}  ({len(st['scenes'])} scenes)")

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out_dir = os.path.join(args.out, f"{stamp}-{slug(st['title'])}")
    work = os.path.join(out_dir, "work")
    os.makedirs(work, exist_ok=True)
    json.dump(st, open(os.path.join(out_dir, "story.json"), "w"), indent=2)

    seed = random.randint(1, 10**6)
    print("2/5 drawing scenes", flush=True)
    imgs = images.make_images(cfg, st, work, seed)

    print("3/5 narrating", flush=True)
    clips, captions = voice.narrate(cfg, st, work)
    voice.write_srt(captions, os.path.join(out_dir, "captions.srt"))

    print("4/5 rendering", flush=True)
    w, h, fps = cfg["images"]["width"], cfg["images"]["height"], cfg["video"]["fps"]
    scene_files = []
    for i, (img, (wav, dur)) in enumerate(zip(imgs, clips)):
        f = os.path.join(work, f"clip_{i:02d}.mp4")
        render.scene_clip(img, wav, dur, i, f, w, h, fps)
        scene_files.append(f)
        print(f"  clip {i + 1}/{len(imgs)}", flush=True)
    total = sum(d for _, d in clips)
    track = music.lullaby(total + 1, os.path.join(work, "music.wav"), seed)
    video = os.path.join(out_dir, "video.mp4")
    render.assemble(scene_files, track, video, cfg["video"]["music_volume"])

    print("5/5 thumbnail + upload sheet", flush=True)
    render.thumbnail(imgs[0], st["title"], os.path.join(out_dir, "thumbnail.jpg"), text=st.get("thumbnail_text"))
    with open(os.path.join(out_dir, "UPLOAD.txt"), "w") as f:
        f.write(
            f"TITLE\n{st['title']}\n\nDESCRIPTION\n{st['description']}\n\n"
            f"TAGS\n{', '.join(st['tags'])}\n\n"
            "SETTINGS\n- Audience: Yes, it's made for kids\n"
            "- Altered or synthetic content: No (cartoon illustration)\n"
            "- Upload captions.srt under Subtitles\n"
            "- Add to playlist: Bedtime Stories\n\n"
            "CHECK BEFORE PUBLISHING\n- Watch it through once (on 2x speed is fine)\n"
            "- Characters look friendly, nothing distorted or scary\n"
            "- Narration matches pictures\n"
        )
    shutil.rmtree(work)

    history.append({"date": stamp, "title": st["title"], "theme": st.get("theme", ""), "minutes": round(total / 60, 1)})
    json.dump(history, open(HISTORY, "w"), indent=2)
    print(f"done: {out_dir}  ({total / 60:.1f} min)")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"dir={out_dir}\ntitle={st['title']}\n")


if __name__ == "__main__":
    main()
