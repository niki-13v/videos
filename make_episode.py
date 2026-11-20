"""Make one episode (~3 min, landscape) + 2 Shorts + thumbnail + upload sheet.

    python make_episode.py                 # next topic in the rotation
    python make_episode.py --topic animals
    python make_episode.py --quick         # 3 items only, for testing
"""
import argparse
import datetime as dt
import json
import os
import random
import time

from anim import episode as E
from anim import topics as TP

ROOT = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(ROOT, "episodes.json")
ROTATION = ["colors", "animals", "shapes", "counting", "fruits"]
BACKGROUNDS = ["meadow", "beach", "playroom"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", choices=ROTATION)
    ap.add_argument("--out", default=os.path.join(ROOT, "output"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-shorts", action="store_true")
    args = ap.parse_args()

    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else []
    topic = args.topic or ROTATION[len(history) % len(ROTATION)]
    seed = int(time.time()) % 1_000_000
    rnd = random.Random(seed)
    bg = rnd.choice(BACKGROUNDS)
    number = sum(1 for h in history if h["topic"] == topic) + 1

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out = os.path.join(args.out, f"{stamp}-{topic}-{seed}")
    os.makedirs(out, exist_ok=True)
    print(f"topic={topic} bg={bg} seed={seed}", flush=True)

    segs = TP.segments(topic, rnd, 3 if args.quick else None)
    segs += TP.find_segments(topic, rnd, 2 if args.quick else 6)
    print("1/4 episode", flush=True)
    tl = E.build(topic, segs, seed=seed)
    E.render(tl, E.Layout(False), topic, bg, os.path.join(out, "episode.mp4"))
    title, desc, tags = TP.metadata(topic, segs, tl["ev"]["chapters"], rnd)
    if number > 1 and topic == "counting":
        title = title.replace("Count to 10 with Bramble", f"Count to 10 with Bramble #{number}")

    print("2/4 thumbnail", flush=True)
    E.thumbnail(topic, [s["item"] for s in segs if s.get("item")], bg, os.path.join(out, "thumbnail.jpg"))

    shorts = []
    if not args.no_shorts:
        print("3/4 shorts", flush=True)
        for k in range(2):
            srnd = random.Random(seed + 100 + k)
            if topic == "counting":
                ssegs = TP.segments(topic, srnd, 10)[k * 2 + 2 : k * 2 + 4]
            elif k == 0:
                ssegs = TP.segments(topic, srnd, 3)
            else:
                ssegs = TP.find_segments(topic, srnd, 3)
            stl = E.build(topic, ssegs, short=True, seed=seed + k)
            path = os.path.join(out, f"short{k + 1}.mp4")
            E.render(stl, E.Layout(True), topic, srnd.choice(BACKGROUNDS), path)
            names = ", ".join(s["chapter"] for s in ssegs)
            shorts.append((path, f"Can you guess? {names} 🐻 #shorts #toddlerlearning #{topic}forkids"))

    print("4/4 upload sheet", flush=True)
    with open(os.path.join(out, "UPLOAD.txt"), "w") as f:
        f.write(f"EPISODE (episode.mp4 + thumbnail.jpg)\n\nTITLE\n{title}\n\nDESCRIPTION\n{desc}\n\nTAGS\n{', '.join(tags)}\n\n")
        f.write(f"PLAYLIST\n{TP.TOPICS[topic]['playlist']}\n\n")
        for k, (_, stitle) in enumerate(shorts, 1):
            f.write(f"SHORT {k} (short{k}.mp4)\nTITLE\n{stitle[:100]}\n\n")
        f.write("SETTINGS FOR EVERY UPLOAD\n- Audience: Yes, it's made for kids\n- Altered or synthetic content: No\n")
    history.append(dict(date=stamp, topic=topic, seed=seed, bg=bg, title=title, minutes=round(tl["total"] / 60, 2)))
    json.dump(history, open(HISTORY, "w"), indent=2)
    print(f"done: {out}  ({tl['total'] / 60:.1f} min)")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"dir={out}\ntitle={title}\n")


if __name__ == "__main__":
    main()
