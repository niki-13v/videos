"""Join recent episodes into one long video (30+ min) with its own thumbnail.

    python make_compilation.py ep1.mp4 ep2.mp4 ... --out output/comp
"""
import argparse
import os
import random
import subprocess

from anim import episode as E
from anim import topics as TP


def duration(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    lst = os.path.join(args.out, "list.txt")
    with open(lst, "w") as f:
        for v in args.videos:
            f.write(f"file '{os.path.abspath(v)}'\n")
    video = os.path.join(args.out, "compilation.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    "-movflags", "+faststart", video], check=True)
    os.remove(lst)

    total = duration(video)
    minutes = int(total // 60)
    rnd = random.Random(minutes)
    items = [dict(group="animal", kind="cow"), dict(group="thing", kind="balloon", color="#e53935"),
             dict(group="shape", kind="star", color="#fdd835")]
    E.thumbnail("colors", items, rnd.choice(["meadow", "beach", "playroom"]), os.path.join(args.out, "thumbnail.jpg"),
                label=("Learn & Play!", f"{minutes} Minutes!"))

    t, chapters = 0.0, []
    for v in args.videos:
        chapters.append(f"{int(t // 60)}:{int(t % 60):02d} Episode {len(chapters) + 1}")
        t += duration(v)
    title = f"{minutes} Minutes of Learning with Bramble 🐻 Colors, Shapes, Animals & Numbers | Toddler Learning Videos"
    desc = (
        f"{minutes} minutes of learning fun with Bramble the bear! Colors, shapes, fruits, animal sounds "
        "and counting, with questions that give your little one time to answer.\n\n"
        + "\n".join(chapters)
        + "\n\nSubscribe for new learning videos with Bramble and friends every day!\n\n#toddlerlearning #kidslearning #preschool"
    )
    with open(os.path.join(args.out, "UPLOAD.txt"), "w") as f:
        f.write(f"COMPILATION (compilation.mp4 + thumbnail.jpg)\n\nTITLE\n{title[:100]}\n\nDESCRIPTION\n{desc}\n\n"
                "TAGS\ntoddler learning video, learning videos for toddlers, colors for kids, shapes for kids, "
                "animal sounds, counting to 10, preschool learning, kids learning videos, bramble the bear\n\n"
                "PLAYLIST\nLong Videos (30+ min)\n\n"
                "SETTINGS\n- Audience: Yes, it's made for kids\n- Altered or synthetic content: No\n")
    print(f"done: {video} ({total / 60:.1f} min)")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"dir={args.out}\ntitle={title[:100]}\n")


if __name__ == "__main__":
    main()
