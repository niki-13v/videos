"""Make one video + 2 Shorts + thumbnail + upload sheet.

    python make_episode.py                       # next format in the rotation
    python make_episode.py --topic animals       # learning episode (~2.5 min)
    python make_episode.py --topic dance-fruits  # Dance Party (~20 min)
    python make_episode.py --next                # just print the next topic
"""
import argparse
import datetime as dt
import json
import os
import random
import time

from anim import dance as DN
from anim import episode as E
from anim import topics as TP

ROOT = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(ROOT, "episodes.json")
LEARN = ["colors", "animals", "shapes", "counting", "fruits"]
DANCE = ["dance-fruits", "dance-animals", "dance-mixed", "dance-shapes"]
ROTATION = ["colors", "dance-fruits", "animals", "shapes", "dance-animals", "counting", "fruits", "dance-mixed",
            "colors", "animals", "dance-shapes", "shapes", "counting", "fruits"]
BACKGROUNDS = ["meadow", "beach", "playroom"]
DANCE_MINUTES = 20


def dance_meta(theme, minutes):
    names = {"fruits": "Fruit", "animals": "Animal", "shapes": "Shapes", "mixed": "Fruits & Animals"}[theme]
    emoji = {"fruits": "🍓🍌", "animals": "🐮🐷", "shapes": "⭐❤️", "mixed": "🍓🐮"}[theme]
    title = f"{names} Dance Party {emoji} | {minutes} Min Baby Sensory Video | Fun Music for Babies & Toddlers"
    desc = (f"Dance along with happy, dancing {names.lower()} and Bramble the bear! {minutes} minutes of bright colors, "
            "bouncy original music and friendly characters, made for babies and toddlers (ages 0-3).\n\n"
            "Great for playtime, high-contrast visual stimulation and calm, happy focus.\n\n"
            "Subscribe for new videos with Bramble and friends every day!\n\n"
            "#babysensory #sensoryvideo #dancingfruit #toddlermusic #babyvideo")
    tags = ["baby sensory", "sensory video for babies", "dancing fruit", "baby dance video", "toddler music",
            "baby sensory video", "fun music for babies", "high contrast baby video", "dance party for kids", "bramble the bear"]
    return title[:100], desc, tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", choices=LEARN + DANCE)
    ap.add_argument("--out", default=os.path.join(ROOT, "output"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-shorts", action="store_true")
    ap.add_argument("--next", action="store_true")
    args = ap.parse_args()

    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else []
    topic = args.topic or ROTATION[len(history) % len(ROTATION)]
    if args.next:
        print(topic)
        return
    seed = int(time.time() * 1000) % 1_000_000
    rnd = random.Random(seed)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out = os.path.join(args.out, f"{stamp}-{topic}-{seed}")
    os.makedirs(out, exist_ok=True)
    print(f"topic={topic} seed={seed}", flush=True)
    shorts = []

    if topic.startswith("dance-"):
        theme = topic.split("-", 1)[1]
        minutes = 1 if args.quick else DANCE_MINUTES
        print("1/4 dance party", flush=True)
        P = DN.plan(theme, minutes, seed)
        DN.render(P, os.path.join(out, "episode.mp4"))
        total = P["total"]
        title, desc, tags = dance_meta(theme, minutes)
        playlist = "Dance Party (Baby Sensory)"
        print("2/4 thumbnail", flush=True)
        DN.thumbnail(theme, seed, os.path.join(out, "thumbnail.jpg"))
        if not args.no_shorts:
            print("3/4 shorts", flush=True)
            for k in range(2):
                SP = DN.plan(theme, 0.6, seed + 7 + k, vertical=True)
                DN.render(SP, os.path.join(out, f"short{k + 1}.mp4"), vertical=True)
                shorts.append(f"Dance with me! 🎶 {theme.capitalize()} Dance Party #shorts #babysensory #dancingfruit")
    else:
        bg = rnd.choice(BACKGROUNDS)
        segs = TP.segments(topic, rnd, 3 if args.quick else None)
        segs += TP.find_segments(topic, rnd, 2 if args.quick else 6)
        print("1/4 episode", flush=True)
        tl = E.build(topic, segs, seed=seed)
        E.render(tl, E.Layout(False), topic, bg, os.path.join(out, "episode.mp4"))
        total = tl["total"]
        title, desc, tags = TP.metadata(topic, segs, tl["ev"]["chapters"], rnd)
        playlist = TP.TOPICS[topic]["playlist"]
        print("2/4 thumbnail", flush=True)
        dull = {"#8d6e63"}  # brown reads muddy in small thumbnails
        thumb_items = [s["item"] for s in segs if s.get("item") and s["item"].get("color") not in dull]
        thumb_items.sort(key=lambda it: it.get("kind") in ("ball", "car"))
        E.thumbnail(topic, thumb_items, bg, os.path.join(out, "thumbnail.jpg"))
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
                E.render(stl, E.Layout(True), topic, srnd.choice(BACKGROUNDS), os.path.join(out, f"short{k + 1}.mp4"))
                names = ", ".join(s["chapter"] for s in ssegs)
                shorts.append(f"Can you guess? {names} 🐻 #shorts #toddlerlearning #{topic}forkids")

    print("4/4 upload sheet", flush=True)
    with open(os.path.join(out, "UPLOAD.txt"), "w") as f:
        f.write(f"VIDEO (episode.mp4 + thumbnail.jpg)\n\nTITLE\n{title}\n\nDESCRIPTION\n{desc}\n\nTAGS\n{', '.join(tags)}\n\n")
        f.write(f"PLAYLIST\n{playlist}\n\n")
        for k, stitle in enumerate(shorts, 1):
            f.write(f"SHORT {k} (short{k}.mp4)\nTITLE\n{stitle[:100]}\n\n")
        f.write("SETTINGS FOR EVERY UPLOAD\n- Audience: Yes, it's made for kids\n- Altered or synthetic content: No\n")
    history.append(dict(date=stamp, topic=topic, seed=seed, title=title, minutes=round(total / 60, 2)))
    json.dump(history, open(HISTORY, "w"), indent=2)
    print(f"done: {out}  ({total / 60:.1f} min)")
    if os.environ.get("GITHUB_OUTPUT"):
        prefix = "dance" if topic.startswith("dance-") else "ep"
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"dir={out}\ntitle={title}\ntag={prefix}-{stamp}-{topic}-{seed}\n")


if __name__ == "__main__":
    main()
