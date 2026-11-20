"""Build and render an episode (landscape) or a Short (vertical) from topic segments."""
import math
import random
import subprocess

import cairo
import numpy as np
import soundfile as sf

from . import audio as A
from . import draw as D
from . import things as T
from .topics import TOPICS

FPS = 30
RAINBOW = ["#e53935", "#fb8c00", "#fdd835", "#43a047", "#1e88e5", "#8e24aa"]
INTRO_LINE = {
    "colors": "Let's learn colors together!", "shapes": "Let's learn shapes together!",
    "fruits": "Let's find some yummy fruits!", "animals": "Let's meet some animal friends!",
    "counting": "Let's count to ten together!",
}


class Layout:
    def __init__(self, vertical):
        self.vertical = vertical
        if vertical:
            self.W, self.H = 1080, 1920
            self.stage = (540, 560)
            self.box = (60, 200, 1020, 900)  # x0, y0, x1, y1 for counting / recap grids
            self.word_y, self.word_max, self.item_s = 1070, 960, 220
            self.bear = (540, 1880, 0.85)
            self.title_y = (520, 760)
        else:
            self.W, self.H = 1920, 1080
            self.stage = (1230, 450)
            self.box = (690, 140, 1800, 720)
            self.word_y, self.word_max, self.item_s = 885, 1100, 175
            self.bear = (400, 1030, 0.92)
            self.title_y = (330, 590)


def grid(n, box, cols=None):
    x0, y0, x1, y1 = box
    cols = cols or min(n, 5)
    rows = math.ceil(n / cols)
    cw, ch = (x1 - x0) / cols, (y1 - y0) / rows
    pts = []
    for j in range(n):
        r, c = divmod(j, cols)
        in_row = min(cols, n - r * cols)
        off = (cols - in_row) * cw / 2
        pts.append((x0 + off + cw * (c + 0.5), y0 + ch * (r + 0.5)))
    return pts, min(cw, ch) * 0.36


# ------------------------------------------------------------------ timeline
def build(topic, segs, short=False, seed=0, voice="af_heart"):
    bv = A.Voice(voice, 0.95)
    iv = A.Voice("bf_emma", 0.9)
    clips, ev = [], dict(waves=[], jumps=[], segs=[], chapters=[], recap=None, party=None, title=None)
    t = 0.5

    def say(text, at, who="b", speed=None, gain=1.0):
        s = (bv if who == "b" else iv).say(text, speed)
        clips.append((at, s, gain, who))
        return at + len(s) / A.SR

    def sfx(fn, at, gain=1.0):
        clips.append((at, fn(), gain, None))

    if short:
        t0 = t
        sfx(A.sfx_boing, t)
        t = say("Can you guess? Let's play!", t + 0.2)
        ev["waves"].append((t0, t))
        t += 0.2
    else:
        sfx(A.sfx_boing, t)
        ev["title"] = (t, None)
        t0 = t
        t = say("Hi friends! It's me, Bramble!", t + 0.4)
        t = say(INTRO_LINE[topic], t + 0.25) + 0.5
        ev["waves"].append((t0, t - 0.5))
        ev["title"] = (ev["title"][0], t)
        t += 0.3

    for seg in segs:
        if seg.get("items") and not ev.get("round2"):
            ev["round2"] = t
            sfx(A.sfx_boing, t)
            t = say("Now let's play a game!", t + 0.2) + 0.3
        se = dict(item=seg.get("item"), items=seg.get("items"), target=seg.get("target"), t0=t, enter=None, exit=None,
                  end=None, thinks=[], reveals=[], counts=[], count=seg.get("count"), pick=None)
        ev["chapters"].append((t, seg["chapter"]))
        for st in seg["steps"]:
            kind = st[0]
            if kind == "enter":
                sfx(A.sfx_whoosh, t)
                sfx(A.sfx_pop, t + 0.35)
                se["enter"] = t
                t += 0.5
            elif kind in ("b", "i"):
                t = say(st[1], t, kind, st[2] if len(st) > 2 else None) + 0.25
            elif kind == "think":
                for k in range(3):
                    sfx(A.sfx_tick, t + 0.25 + k * 0.5)
                se["thinks"].append((t, t + st[1]))
                t += st[1]
            elif kind == "reveal":
                sfx(A.sfx_ding, t, 0.8)
                se["reveals"].append((t, st[1], st[2]))
                ev["jumps"].append(t)
                t += 0.1
            elif kind == "pick":
                sfx(A.sfx_ding, t, 0.8)
                se["pick"] = t
                se["reveals"].append((t, st[1], st[2]))
                ev["jumps"].append(t)
                t += 0.1
            elif kind == "count":
                if se["enter"] is None:
                    se["enter"] = t
                for j in range(1, st[1] + 1):
                    sfx(A.sfx_pop, t)
                    se["counts"].append(t)
                    t = say(f"{j}!", t + 0.05, speed=1.0) + 0.2
                t += 0.3
            elif kind == "exit":
                t += 0.2
                sfx(A.sfx_whoosh, t)
                se["exit"] = t
                t += 0.35
        se["end"] = t
        ev["segs"].append(se)

    if not short:
        main = [s for s in segs if not s.get("items")]
        words = [s["chapter"] if not s.get("count") else str(s["count"]) for s in main]
        rec = dict(t=t, times=[], items=[s["item"] for s in main])
        ev["chapters"].append((t, "Let's say them all"))
        t = say("Let's say them all!" if topic != "counting" else "Let's count to ten, fast!", t + 0.2) + 0.2
        for w in words:
            sfx(A.sfx_pop, t)
            rec["times"].append(t)
            t = say((w if not w.isdigit() else w) + "!", t + 0.05, speed=1.0) + 0.22
        ev["recap"] = rec
        t += 0.3

    sfx(A.sfx_ding, t)
    ev["party"] = t
    ev["jumps"].append(t)
    t = say("Yay! You did it! Great job!", t + 0.1)
    t0 = t
    t = say("Bye bye, friends! See you next time!" if not short else "Watch more with Bramble!", t + 0.3)
    ev["waves"].append((t0, t + 1.0))
    total = t + 1.6

    mix = A.Mixer(total)
    for at, s, gain, who in clips:
        mix.add(at, s, gain, who)
    n_frames = int(total * FPS)
    mb = mix.mouth_track(FPS, n_frames, "b")
    mi = mix.mouth_track(FPS, n_frames, "i")
    tune = TOPICS[topic]["music"]
    music = A.music_bouncy(total + 1, seed) if tune == "bouncy" else A.music_tune(total + 1, tune, seed)
    wav = mix.finish(total, music)
    return dict(total=total, ev=ev, mb=mb, mi=mi, wav=wav)


# ------------------------------------------------------------------ drawing
def word_size(L, word, size=175):
    return min(size, int(L.word_max / (0.8 * max(1, len(word)))))


def draw_frame(cr, t, tl, L, topic, bg):
    ev, W, H = tl["ev"], L.W, L.H
    fi = min(int(t * FPS), len(tl["mb"]) - 1)
    seg = next((s for s in ev["segs"] if s["t0"] <= t < s["end"]), None)

    punch = 0.0
    for s in ev["segs"]:
        for rt, *_ in s["reveals"]:
            if 0 <= t - rt < 0.5:
                punch = max(punch, 0.05 * (1 - (t - rt) / 0.5))
    cr.save()
    cr.translate(W / 2, H / 2)
    cr.scale(1 + punch, 1 + punch)
    cr.translate(-W / 2, -H / 2)
    D.scene_bg(cr, bg, W, H, t)

    sx, sy = L.stage
    multi = None
    if seg and seg["items"]:
        multi, msize = grid(3, (L.box[0] - 60, L.box[1] + 60, L.box[2] + 80, L.box[3] - 60) if not L.vertical else (30, 330, 1050, 900), cols=3)
        msize *= 1.0
    if seg and seg["reveals"] and t >= seg["reveals"][0][0]:
        fade = 1 - D.ease_out((t - seg["exit"]) / 0.35) if seg["exit"] else 1
        a = min(1, (t - seg["reveals"][0][0]) * 3) * fade
        if multi:
            rx, ry = multi[seg["target"]]
        else:
            rx, ry = sx, (sy if not seg["count"] else (L.box[1] + L.box[3]) / 2)
        D.rays(cr, rx, ry, t, seg["reveals"][-1][2] if not seg["count"] else seg["item"]["color"], a)

    # Bramble
    waving = any(a <= t < b for a, b in ev["waves"])
    jump = 0.0
    for jt in ev["jumps"]:
        dt = t - jt
        if 0 <= dt < 0.6:
            jump = math.sin(math.pi * dt / 0.6)
    if ev["party"] and 0 <= t - ev["party"] < 1.8:
        jump = abs(math.sin(math.pi * (t - ev["party"]) / 0.6))
    bx, by, bs = L.bear
    D.bramble(cr, bx, by, bs, t, mouth=float(tl["mb"][fi]), wave=1.0 if waving else 0.0, blink=(t % 3.3) < 0.12, jump=jump)

    # title
    if ev["title"] and ev["title"][1] and t < ev["title"][1] + 0.5:
        p = (t - ev["title"][0]) / 0.8
        out = max(0, (t - ev["title"][1]) / 0.5)
        l1, l2 = TOPICS[topic]["title"]
        cr.save()
        cr.translate(0, -out * H * 0.7)
        tx = W * 0.64 if not L.vertical else W / 2
        D.word_row(cr, l1, RAINBOW, tx, L.title_y[0], 180, t, p)
        D.word_row(cr, l2, RAINBOW[2:] + RAINBOW[:2], tx, L.title_y[1], 180, t, p - 0.3)
        cr.restore()

    if seg:
        leave = D.ease_out((t - seg["exit"]) / 0.35) if seg["exit"] else 0.0
        shift = -leave * W * 0.75
        item = seg["item"] or seg["items"][seg["target"]]
        blink = ((t + 1.1) % 2.7) < 0.12
        last_rev = max((r for r in seg["reveals"] if r[0] <= t), default=None, key=lambda r: r[0])
        if multi:
            enter = D.ease_out((t - seg["enter"]) / 0.5)
            for j, (px, py) in enumerate(multi):
                it = seg["items"][j]
                sc = D.elastic((t - seg["enter"] - 0.2 - j * 0.12) / 0.6) if t > seg["enter"] + 0.2 + j * 0.12 else 0.01
                hop, mouth = 0, 0.0
                if seg["pick"] and t >= seg["pick"]:
                    if j == seg["target"]:
                        hop = -abs(math.sin((t - seg["pick"]) * 6)) * 35
                        sc *= 1 + 0.25 * D.ease_out((t - seg["pick"]) / 0.4)
                        mouth = float(tl["mi"][fi])
                    else:
                        sc *= 1 - 0.35 * D.ease_out((t - seg["pick"]) / 0.4)
                T.draw_item(cr, it, px + (1 - enter) * W * 0.5 + shift, py + hop, msize * max(0.01, sc), t + j, mouth=mouth, blink=blink)
            q = 0.0
            for a, b in seg["thinks"]:
                if a <= t < b:
                    q = min(1, (t - a) * 4)
            D.question_mark(cr, multi[2][0] + msize * 0.9, multi[2][1] - msize * 1.4, t, q)
        elif seg["count"]:
            pts, size = grid(seg["count"], L.box)
            for j, (px, py) in enumerate(pts):
                ct = seg["counts"][j]
                if t < ct:
                    continue
                hop = -abs(math.sin((t - ct) * 7)) * 25 * max(0, 1 - (t - ct) / 0.8)
                if last_rev:
                    hop = -abs(math.sin((t - last_rev[0]) * 6 + j * 0.5)) * 20 * max(0, 1 - (t - last_rev[0]) / 1.5)
                T.draw_item(cr, item, px + shift, py + hop, size * D.elastic((t - ct) / 0.5), t + j, blink=blink)
                D.big_word(cr, str(j + 1), "#ffffff", px + shift, py - size * 1.35, int(size * 0.7), (t - ct) / 0.4)
        else:
            enter = D.ease_out((t - seg["enter"]) / 0.5)
            x = sx + (1 - enter) * W * 0.5 + shift
            bounce = 0
            if last_rev:
                bounce = -abs(math.sin((t - last_rev[0]) * 6)) * 25 * max(0, 1 - (t - last_rev[0]) / 1.5)
            pop = D.elastic((t - seg["enter"] - 0.3) / 0.6) if t > seg["enter"] + 0.3 else 0.01
            T.draw_item(cr, item, x, sy + bounce, L.item_s * max(0.01, pop), t, mouth=float(tl["mi"][fi]), blink=blink)
            q = 0.0
            for a, b in seg["thinks"]:
                if a <= t < b:
                    q = min(1, (t - a) * 4)
            D.question_mark(cr, x + L.item_s * 1.45, sy - L.item_s * 1.1, t, q)
        if last_rev:
            word = last_rev[1].upper() if not last_rev[1][:1].isdigit() else last_rev[1]
            size = word_size(L, word) if not seg["count"] else 230
            wx = (sx if not L.vertical else W / 2) if not multi else multi[seg["target"]][0]
            wx = min(max(wx, L.word_max / 2 * 0.0 + (W * 0.42 if not L.vertical else W * 0.3)), W * 0.85 if not L.vertical else W * 0.7) if multi else wx
            D.big_word(cr, word, last_rev[2], wx + shift, L.word_y, size if not multi else min(size, 150), (t - last_rev[0]) / 0.7)
        cx, cy = multi[seg["target"]] if multi else (sx, sy)
        for rt, _, col in seg["reveals"]:
            D.confetti(cr, cx, cy, t - rt, int(rt * 10), [col, "#ffffff", "#fdd835"])

    rec = ev["recap"]
    if rec and t >= rec["t"]:
        n = len(rec["items"])
        pts, size = grid(n, L.box, cols=5 if n > 8 else min(n, 4))
        for k, (px, py) in enumerate(pts):
            pt = rec["times"][k]
            if t < pt:
                continue
            hop = -abs(math.sin((t - pt) * 7)) * 30 * max(0, 1 - (t - pt) / 1.0)
            if ev["party"] and t > ev["party"]:
                hop = -abs(math.sin(t * 6 + k)) * 22
            it = rec["items"][k]
            T.draw_item(cr, it, px, py + hop, size * D.elastic((t - pt) / 0.5), t + k, blink=((t + k) % 2.9) < 0.12)
            if topic == "counting":
                D.big_word(cr, str(k + 1), "#ffffff", px, py + size * 1.3, int(size * 0.7), (t - pt) / 0.4)
    if ev["party"]:
        D.confetti(cr, W * 0.5, H * 0.3, t - ev["party"], 99, RAINBOW)
        D.confetti(cr, W * 0.8, H * 0.3, t - ev["party"] - 0.3, 98, RAINBOW)
    cr.restore()


def render(tl, L, topic, bg, out):
    wav_path = out + ".wav"
    sf.write(wav_path, tl["wav"], A.SR)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{L.W}x{L.H}", "-r", str(FPS),
         "-i", "-", "-i", wav_path, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-g", "60", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE,
    )
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, L.W, L.H)
    n = int(tl["total"] * FPS)
    for i in range(n):
        cr = cairo.Context(surf)
        draw_frame(cr, i / FPS, tl, L, topic, bg)
        surf.flush()
        ff.stdin.write(bytes(surf.get_data()))
        if i % 900 == 0:
            print(f"    frame {i}/{n}", flush=True)
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg failed")
    import os

    os.remove(wav_path)


def thumbnail(topic, items, bg, out, label=None):
    """Bright 1280x720 thumbnail: Bramble + three items + big title."""
    W, H = 1920, 1080
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(surf)
    D.scene_bg(cr, bg, W, H, 0.0)
    D.rays(cr, W * 0.66, H * 0.62, 0.3, items[0].get("color", "#fdd835") if items[0]["group"] != "animal" else "#ffb74d", 1)
    for (x, y, s), it in zip([(1000, 800, 165), (1340, 760, 185), (1680, 810, 165)], items[:3]):
        T.draw_item(cr, it, x, y, s, 0.0)
    D.bramble(cr, 380, 1060, 1.05, 0.0, mouth=0.7, wave=1.0)
    l1, l2 = TOPICS[topic]["title"] if not label else label
    fit = lambda w: min(200, int(1150 / (0.66 * len(w))))
    D.word_row(cr, l1, RAINBOW, 1300, 150, fit(l1), 0.0, 5)
    D.word_row(cr, l2, RAINBOW[2:] + RAINBOW[:2], 1300, 360, fit(l2), 0.0, 5)
    png = out + ".png"
    surf.write_to_png(png)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", png, "-vf", "scale=1280:720", "-q:v", "2", out], check=True)
    import os

    os.remove(png)
