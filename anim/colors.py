"""Episode: "Learn Colors with Bramble". Builds audio + timeline, then renders frames.

    python -m anim.colors out.mp4
"""
import math
import subprocess
import sys

import cairo
import numpy as np
import soundfile as sf

from . import audio as A
from . import draw as D

W, H, FPS = 1920, 1080, 30

ITEMS = [
    ("red", "#e53935", "apple", "apple"),
    ("blue", "#1e88e5", "balloon", "balloon"),
    ("yellow", "#fdd835", "star", "star"),
    ("green", "#43a047", "frog", "frog"),
    ("orange", "#fb8c00", "fish", "fish"),
    ("purple", "#8e24aa", "grapes", "grapes"),
]
RAINBOW = [c for _, c, _, _ in ITEMS]


def build():
    v = A.Voice("af_bella", 1.0)
    clips, ev, t = [], [], 0.6

    def say(text, at, speed=None, gain=1.0):
        s = v.say(text, speed)
        clips.append((at, s, gain, True))
        return at + len(s) / A.SR

    def sfx(fn, at, gain=1.0):
        clips.append((at, fn(), gain, False))

    # intro
    sfx(A.sfx_boing, t)
    ev.append(("title", t, None))
    t = say("Hi friends! It's me, Bramble!", t + 0.4)
    ev.append(("wave", 0.6, t))
    t = say("Let's learn colors together!", t + 0.25) + 0.5
    ev.append(("title_out", t, None))

    for i, (name, col, kind, noun) in enumerate(ITEMS):
        start = t
        sfx(A.sfx_whoosh, t)
        sfx(A.sfx_pop, t + 0.35)
        t = say(f"What color is this {noun}?", t + 0.7)
        ask_end = t
        for k in range(3):
            sfx(A.sfx_tick, t + 0.3 + k * 0.55)
        reveal = t + 1.9
        sfx(A.sfx_ding, reveal, 0.8)
        t = say(f"{name.capitalize()}!", reveal + 0.1, speed=0.95, gain=1.1)
        t = say(f"It's a {name} {noun}!", t + 0.3)
        t = say(f"{name.capitalize()}!", t + 0.35, speed=0.95) + 0.6
        sfx(A.sfx_whoosh, t)
        ev.append(("item", start, dict(i=i, ask_end=ask_end, reveal=reveal, end=t + 0.45)))
        t += 0.5

    # recap: all colors again, fast and fun
    rec = t
    t = say("Let's say them all!", t + 0.2) + 0.2
    times = []
    for name, *_ in ITEMS:
        sfx(A.sfx_pop, t)
        times.append(t)
        t = say(name.capitalize() + "!", t + 0.05, speed=1.0) + 0.25
    ev.append(("recap", rec, dict(times=times)))
    t += 0.3
    sfx(A.sfx_ding, t)
    ev.append(("party", t, None))
    t = say("Yay! You did it! Great job!", t + 0.1)
    t = say("Bye bye, friends!", t + 0.3)
    ev.append(("wave", t - 1.5, t + 1.0))
    total = t + 1.6

    mix = A.Mixer(total)
    for at, s, gain, is_speech in clips:
        mix.add(at, s, gain, is_speech)
    n_frames = int(total * FPS)
    mouth = mix.mouth_track(FPS, n_frames)
    wav = mix.finish(total, A.music_bouncy(total + 1, seed=7))
    return total, ev, mouth, wav


def frame(cr, t, ev, mouth):
    tint, tint_amt = None, 0.0
    item = next((e for e in ev if e[0] == "item" and e[1] <= t < e[2]["end"]), None)
    if item:
        name, col, kind, noun = ITEMS[item[2]["i"]]
        if t >= item[2]["reveal"]:
            tint, tint_amt = col, min(1, (t - item[2]["reveal"]) * 3)

    # camera punch on reveals
    punch = 0.0
    for e in ev:
        if e[0] == "item":
            dt = t - e[2]["reveal"]
            if 0 <= dt < 0.5:
                punch = max(punch, 0.05 * (1 - dt / 0.5))
    cr.save()
    cr.translate(W / 2, H / 2)
    cr.scale(1 + punch, 1 + punch)
    cr.translate(-W / 2, -H / 2)

    D.background(cr, W, H, t)
    if item and tint:
        d = item[2]
        fade = 1 - D.ease_out((t - (d["end"] - 0.45)) / 0.45)
        D.rays(cr, W * 0.66, H * 0.43, t, tint, tint_amt * fade)

    # Bramble
    waving = any(e[0] == "wave" and e[1] <= t < e[2] for e in ev)
    jump = 0.0
    for e in ev:
        if e[0] == "item":
            dt = t - e[2]["reveal"]
            if 0 <= dt < 0.6:
                jump = math.sin(math.pi * dt / 0.6)
        if e[0] == "party":
            dt = t - e[1]
            if 0 <= dt < 1.2:
                jump = abs(math.sin(math.pi * dt / 0.6))
    blink = (t % 3.3) < 0.12
    fi = min(int(t * FPS), len(mouth) - 1)
    D.bramble(cr, W * 0.25, H * 0.95, 0.92, t, mouth=float(mouth[fi]), wave=1.0 if waving else 0.0, blink=blink, jump=jump)

    # title
    title = next((e for e in ev if e[0] == "title"), None)
    tout = next((e for e in ev if e[0] == "title_out"), None)
    if title and t < tout[1] + 0.4:
        p = (t - title[1]) / 0.8
        out = max(0, (t - tout[1]) / 0.4)
        cr.save()
        cr.translate(0, -out * 700)
        D.word_row(cr, "Learn", RAINBOW, W * 0.64, H * 0.3, 180, t, p)
        D.word_row(cr, "Colors!", RAINBOW[2:] + RAINBOW[:2], W * 0.64, H * 0.55, 180, t, p - 0.3)
        cr.restore()

    # current item
    if item:
        d = item[2]
        name, col, kind, noun = ITEMS[d["i"]]
        enter = D.ease_out((t - item[1]) / 0.5)
        leave = D.ease_out((t - (d["end"] - 0.45)) / 0.45)
        x = W * 0.66 + (1 - enter) * 900 - leave * 1300
        bounce = 0
        if t >= d["reveal"]:
            bounce = -abs(math.sin((t - d["reveal"]) * 6)) * 25 * max(0, 1 - (t - d["reveal"]) / 1.5)
        D.obj(cr, kind, col, x, H * 0.43 + bounce, 175 * D.elastic(min(1, (t - item[1] - 0.3) / 0.6)) if t > item[1] + 0.3 else 1,
              t, blink=((t + 1.1) % 2.7) < 0.12)
        # "?" while kids think
        q = 0.0
        if d["ask_end"] <= t < d["reveal"]:
            q = min(1, (t - d["ask_end"]) * 4)
        D.question_mark(cr, x + 260, H * 0.22, t, q)
        if t >= d["reveal"]:
            D.big_word(cr, name.upper(), col, x - leave * 0, H * 0.82, 175, (t - d["reveal"]) / 0.7)
            D.confetti(cr, x, H * 0.4, t - d["reveal"], d["i"], [col, "#ffffff", col])

    # recap row
    recap = next((e for e in ev if e[0] == "recap"), None)
    party = next((e for e in ev if e[0] == "party"), None)
    if recap and t >= recap[1]:
        for k, (name, col, kind, noun) in enumerate(ITEMS):
            pt = recap[2]["times"][k]
            if t < pt:
                continue
            cx = W * 0.47 + (k % 3) * 330
            cy = H * 0.27 + (k // 3) * 330
            hop = -abs(math.sin((t - pt) * 7)) * 30 * max(0, 1 - (t - pt) / 1.0)
            if party and t > party[1]:
                hop = -abs(math.sin(t * 6 + k)) * 25
            D.obj(cr, kind, col, cx, cy + hop, 105 * D.elastic((t - pt) / 0.5), t + k, blink=((t + k) % 2.9) < 0.12)
    if party:
        D.confetti(cr, W * 0.5, H * 0.3, t - party[1], 99, RAINBOW)
        D.confetti(cr, W * 0.8, H * 0.3, t - party[1] - 0.3, 98, RAINBOW)
    cr.restore()


def render(out):
    total, ev, mouth, wav = build()
    wav_path = out + ".wav"
    sf.write(wav_path, wav, A.SR)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-i", wav_path, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE,
    )
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    n = int(total * FPS)
    for i in range(n):
        cr = cairo.Context(surf)
        frame(cr, i / FPS, ev, mouth)
        surf.flush()
        ff.stdin.write(bytes(surf.get_data()))
        if i % 300 == 0:
            print(f"  frame {i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"done: {out} ({total:.1f}s)")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "colors.mp4")
