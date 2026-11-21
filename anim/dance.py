"""Dance Party: long, music-driven sensory videos. Characters with arms and feet dance on the beat
over bright, shifting backgrounds; Bramble calls out names now and then so it still teaches words."""
import math
import random
import subprocess

import cairo
import numpy as np
import soundfile as sf

from . import audio as A
from . import draw as D
from . import music as MU
from . import things as T
from .topics import ANIMALS, COLORS, FRUITS, SHAPES

FPS = 30
PALETTES = [("#7e57c2", "#311b92"), ("#26c6da", "#00838f"), ("#ec407a", "#ad1457"), ("#ffa726", "#e65100"),
            ("#66bb6a", "#2e7d32"), ("#42a5f5", "#1565c0"), ("#ab47bc", "#6a1b9a"), ("#ef5350", "#b71c1c")]
MOVES = ["bounce", "sway", "wave", "spin", "alt", "pop", "conga"]
THEME_TITLES = {
    "fruits": ("Fruit", "Dance Party!"), "animals": ("Animal", "Dance Party!"),
    "shapes": ("Shapes", "Dance Party!"), "mixed": ("Dance", "Party!"),
}


def cast_pool(theme):
    fruits = [dict(group="thing", kind=k, color=c, name=n) for k, n, _, c, _ in FRUITS]
    animals = [dict(group="animal", kind=k, color="#ffffff", name=n) for k, n, _ in ANIMALS]
    shapes = [dict(group="shape", kind=s, color=COLORS[c], name=f"{c} {s}") for s in SHAPES for c in ("red", "blue", "yellow", "green", "purple", "orange")]
    return {"fruits": fruits, "animals": animals, "shapes": shapes, "mixed": fruits + animals + shapes[::4]}[theme]


# ------------------------------------------------------------------ plan
def plan(theme, minutes, seed, vertical=False):
    rnd = random.Random(seed)
    voice = A.Voice("af_heart", 1.0)
    total = minutes * 60
    tunes = [None, "twinkle", None, "london_bridge", None, "mary_lamb", None, "old_macdonald", None, "row_row"]
    rnd.shuffle(tunes)
    songs, t, k = [], 0.0, 0
    while t < total:
        length = min(rnd.uniform(150, 200), total - t + 1) if not vertical else total + 1
        audio, info = MU.song(length, seed * 31 + k, tunes[k % len(tunes)], energy=1.0)
        songs.append(dict(start=t, audio=audio, info=info, length=length))
        t += length - 1.0
        k += 1
    total = t + 1.0
    mix = A.Mixer(total)
    music = np.zeros(int(total * A.SR) + A.SR, dtype=np.float32)
    for sg in songs:
        i = int(sg["start"] * A.SR)
        a = sg["audio"].copy()
        f = A.SR
        a[:f] *= np.linspace(0, 1, f)
        music[i : i + len(a)] += a[: len(music) - i]

    pool = cast_pool(theme)
    scenes = []
    for sg in songs:
        spb = sg["info"]["spb"]
        st = sg["start"] + sg["info"]["bar_start"]
        if not scenes:
            scenes.append(dict(t0=0, t1=st, spb=spb, beat0=0, kind="intro", cast=[], move="bounce", pal=PALETTES[0], word=None))
        end = sg["start"] + sg["length"] - 1.5
        while st < end:
            dur = spb * 32  # 8 bars
            layout = rnd.choice(["one", "three", "three", "five", "pair", "conga", "bramble"])
            if layout == "one":
                cast = [rnd.choice(pool)]
            elif layout == "three":
                cast = [rnd.choice(pool)] * 3 if rnd.random() < 0.5 else rnd.sample(pool, 3)
            elif layout == "five":
                cast = rnd.sample(pool, min(5, len(pool)))
            elif layout == "pair":
                cast = rnd.sample(pool, 2)
            elif layout == "conga":
                cast = [rnd.choice(pool)] * 6
            else:
                cast = [rnd.choice(pool), rnd.choice(pool)]
            moves = rnd.sample(MOVES[:-1], 2) if layout != "conga" else ["conga", "conga"]
            word = cast[0]["name"] if layout in ("one", "three", "conga") and (len(set(c["name"] for c in cast)) == 1) else None
            scenes.append(dict(t0=st, t1=min(st + dur, end), spb=spb, beat0=st, kind=layout, cast=cast, moves=moves,
                               pal=rnd.choice(PALETTES), word=word))
            if word:
                s = voice.say(f"{word.capitalize()}!", 1.0)
                mix.add(st + spb * 0.5, s, 1.0, "b")
                mix.add(st + spb * 16.5, s, 1.0, "b")
            st += dur
    # outro
    scenes.append(dict(t0=scenes[-1]["t1"], t1=total, spb=songs[-1]["info"]["spb"], beat0=scenes[-1]["t1"], kind="outro",
                       cast=[], moves=["bounce", "bounce"], pal=PALETTES[2], word=None))
    hello = voice.say("Let's dance!" if not vertical else "Dance with me!", 1.0)
    mix.add(0.6, hello, 1.0, "b")
    bye = voice.say("Yay! Great dancing! Bye bye!", 1.0)
    mix.add(max(0.5, total - 1.5 - len(bye) / A.SR), bye, 1.0, "b")
    n_frames = int(total * FPS)
    mb = mix.mouth_track(FPS, n_frames, "b")
    wav = mix.finish(total, music[: int(total * A.SR)] * 0.6)
    return dict(total=total, scenes=scenes, wav=wav, mb=mb, theme=theme)


# ------------------------------------------------------------------ drawing
def limbs(cr, s, beat, phase, style):
    """Noodle arms + round feet so objects can dance."""
    swing = math.sin(math.pi * (beat + phase))
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_source_rgb(*D.OUTLINE)
    cr.set_line_width(max(4, s * 0.08))
    for side in (-1, 1):
        up = swing * side if style != "spin" else 1
        hx = side * s * (1.35 + 0.1 * up)
        hy = -s * (0.15 + 0.55 * max(0, up)) + s * 0.25 * max(0, -up)
        cr.move_to(side * s * 0.82, s * 0.1)
        cr.curve_to(side * s * 1.1, s * 0.2, side * s * 1.2, hy + s * 0.2, hx, hy)
        cr.stroke()
        D.ellipse(cr, hx, hy, s * 0.13, s * 0.13, (1, 1, 1), D.OUTLINE, max(3, s * 0.04))
    step = math.sin(math.pi * 2 * (beat + phase) / 2)
    for side in (-1, 1):
        lift = max(0, step * side) * s * 0.18
        cr.set_source_rgb(*D.OUTLINE)
        cr.move_to(side * s * 0.3, s * 0.85)
        cr.line_to(side * s * 0.35, s * 1.12 - lift)
        cr.stroke()
        D.ellipse(cr, side * s * 0.42, s * 1.18 - lift, s * 0.2, s * 0.11, D.hexc("#ff7043"), D.OUTLINE, max(3, s * 0.04))


def dancer(cr, item, x, y, s, t, beat, i, move):
    pulse = math.exp(-((beat % 1.0)) * 7)
    rot, dx, dy, sc = 0.0, 0.0, 0.0, 1.0
    if move == "bounce":
        dy = -abs(math.sin(math.pi * beat)) * s * 0.45
    elif move == "sway":
        rot = 0.28 * math.sin(math.pi * beat)
        dx = s * 0.25 * math.sin(math.pi * beat)
    elif move == "wave":
        dy = -max(0, math.sin(math.pi * (beat * 0.5 + i * 0.35))) * s * 0.6
    elif move == "spin":
        frac = beat % 4
        rot = 2 * math.pi * D.ease_out(frac - 3) if frac > 3 else 0
        dy = -abs(math.sin(math.pi * beat)) * s * 0.15
    elif move == "alt":
        dy = -abs(math.sin(math.pi * beat)) * s * 0.5 if (int(beat) + i) % 2 == 0 else 0
    elif move == "pop":
        sc = 1 + 0.18 * pulse
    elif move == "conga":
        dy = -abs(math.sin(math.pi * beat)) * s * 0.3
        rot = 0.15 * math.sin(math.pi * beat)
    squash = 1 + 0.08 * pulse
    # ground shadow
    cr.save()
    cr.translate(x, y + s * 1.35)
    cr.scale(1, 0.22)
    cr.set_source_rgba(0, 0, 0, 0.18)
    cr.arc(0, 0, s * (0.9 + dy / s * 0.3 if dy else 0.9), 0, 2 * math.pi)
    cr.fill()
    cr.restore()
    cr.save()
    cr.translate(x + dx, y + dy)
    cr.rotate(rot)
    cr.scale(sc * (2 - squash), sc * squash)
    if item["group"] == "bramble":
        D.bramble(cr, 0, s * 1.4, s / 300, t, mouth=0.4 * pulse, wave=1.0 if int(beat) % 4 < 2 else 0.0)
    else:
        limbs(cr, s, beat, i * 0.5, move)
        T.draw_item(cr, item, 0, 0, s, t + i, mouth=0.45 * pulse if int(beat / 2) % 2 == 0 else 0.0,
                    blink=((t + i * 0.7) % 3.1) < 0.12)
    cr.restore()


def background(cr, W, H, t, sc, beat):
    a, b = sc["pal"]
    g = cairo.RadialGradient(W / 2, H * 0.45, 50, W / 2, H * 0.45, max(W, H) * 0.8)
    g.add_color_stop_rgb(0, *D.hexc(a))
    g.add_color_stop_rgb(1, *D.hexc(b))
    cr.set_source(g)
    cr.paint()
    cr.save()
    cr.translate(W / 2, H * 0.45)
    cr.rotate(t * 0.15)
    for k in range(20):
        cr.move_to(0, 0)
        cr.arc(0, 0, max(W, H) * 1.3, k * math.pi / 10, k * math.pi / 10 + math.pi / 20)
        cr.close_path()
        cr.set_source_rgba(1, 1, 1, 0.07)
        cr.fill()
    cr.restore()
    # floating bubbles & stars rising
    rnd = random.Random(7)
    for k in range(26):
        bx = rnd.uniform(0, W)
        speed = rnd.uniform(40, 110)
        by = H + 60 - ((t * speed + rnd.uniform(0, H)) % (H + 120))
        r = rnd.uniform(10, 34)
        if k % 3 == 0:
            cr.save()
            cr.translate(bx + 20 * math.sin(t + k), by)
            cr.rotate(t + k)
            cr.move_to(0, -r)
            for j in range(1, 10):
                rr = r if j % 2 == 0 else r * 0.45
                ang = -math.pi / 2 + j * math.pi / 5
                cr.line_to(rr * math.cos(ang), rr * math.sin(ang))
            cr.close_path()
            cr.set_source_rgba(1, 0.95, 0.5, 0.55)
            cr.fill()
            cr.restore()
        else:
            cr.arc(bx + 20 * math.sin(t + k), by, r, 0, 2 * math.pi)
            cr.set_source_rgba(1, 1, 1, 0.18)
            cr.fill_preserve()
            cr.set_source_rgba(1, 1, 1, 0.4)
            cr.set_line_width(3)
            cr.stroke()
    # downbeat flash
    bar_pulse = math.exp(-((beat % 4.0)) * 4)
    cr.set_source_rgba(1, 1, 1, 0.08 * bar_pulse)
    cr.paint()


def positions(kind, n, W, H, beat, vertical):
    cy = H * (0.5 if not vertical else 0.45)
    if kind == "one":
        return [(W / 2, cy)], (H * 0.2 if not vertical else W * 0.28)
    if kind == "pair":
        return [(W * 0.33, cy), (W * 0.67, cy)], (H * 0.16 if not vertical else W * 0.2)
    if kind == "bramble":
        return [(W * 0.25, cy), (W * 0.75, cy)], (H * 0.15 if not vertical else W * 0.17)
    if kind == "three":
        if vertical:
            return [(W * 0.5, H * 0.28), (W * 0.27, H * 0.55), (W * 0.73, H * 0.55)], W * 0.15
        return [(W * (0.22 + 0.28 * i), cy) for i in range(3)], H * 0.14
    if kind == "five":
        if vertical:
            return [(W * 0.25, H * 0.3), (W * 0.75, H * 0.3), (W * 0.5, H * 0.45), (W * 0.25, H * 0.62), (W * 0.75, H * 0.62)], W * 0.12
        return [(W * (0.12 + 0.19 * i), cy + (0 if i % 2 else -H * 0.06)) for i in range(5)], H * 0.1
    if kind == "conga":
        span = W + W * 0.9
        out = []
        for i in range(n):
            x = ((beat * W * 0.035) + i * W * 0.17) % span - W * 0.45
            out.append((x, cy + 30 * math.sin(beat * math.pi * 0.5 + i)))
        return out, H * 0.1 if not vertical else W * 0.12
    return [], 0


def draw_frame(cr, t, P, W, H, vertical):
    sc = next((s for s in P["scenes"] if s["t0"] <= t < s["t1"]), P["scenes"][-1])
    beat = (t - sc["beat0"]) / sc["spb"]
    background(cr, W, H, t, sc, beat)
    fi = min(int(t * FPS), len(P["mb"]) - 1)
    if sc["kind"] in ("intro", "outro"):
        pulse = math.exp(-((beat % 1.0)) * 7)
        bs = (H * 0.22 if not vertical else W * 0.3)
        dancer(cr, dict(group="bramble"), W / 2, H * 0.52 if not vertical else H * 0.55, bs, t, beat, 0, "bounce")
        l1, l2 = THEME_TITLES[P["theme"]]
        cols = ["#ffffff", "#fff176", "#ffffff", "#80deea"]
        if sc["kind"] == "intro":
            D.word_row(cr, l1, cols, W / 2, H * (0.16 if not vertical else 0.14), 150 if not vertical else 130, t, t / 0.8)
            D.word_row(cr, l2, cols[1:] + cols[:1], W / 2, H * (0.86 if not vertical else 0.84), 150 if not vertical else 110, t, t / 0.8 - 0.3)
        return
    progress = (t - sc["t0"]) / max(0.1, sc["t1"] - sc["t0"])
    move = sc["moves"][0] if progress < 0.5 else sc["moves"][1]
    pts, size = positions(sc["kind"], len(sc["cast"]), W, H, beat, vertical)
    enter = D.ease_out((t - sc["t0"]) / 0.6)
    cast = sc["cast"] if sc["kind"] != "bramble" else [dict(group="bramble"), sc["cast"][0]]
    for i, ((x, y), item) in enumerate(zip(pts, cast)):
        drop = (1 - enter) * -H * 0.8 if sc["kind"] != "conga" else 0
        dancer(cr, item, x, y + drop, size, t, beat, i, move)
    if sc["word"]:
        for wt in (0.5, 16.5):
            age = beat - wt
            if 0 <= age < 6:
                fade = 1 if age < 5 else 6 - age
                cr.push_group()
                D.big_word(cr, sc["word"].upper(), "#ffffff" if sc["cast"][0]["group"] == "animal" else sc["cast"][0]["color"],
                           W / 2, H * (0.85 if not vertical else 0.8), 130 if not vertical else 150, age / 0.6)
                cr.pop_group_to_source()
                cr.paint_with_alpha(max(0, fade))


def render(P, out, vertical=False):
    from .render import render as prender

    W, H = (1080, 1920) if vertical else (1920, 1080)
    prender(lambda cr, t: draw_frame(cr, t, P, W, H, vertical), W, H, P["total"], P["wav"], A.SR, out)


def thumbnail(theme, seed, out):
    W, H = 1920, 1080
    rnd = random.Random(seed)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(surf)
    sc = dict(pal=rnd.choice(PALETTES))
    background(cr, W, H, 1.0, sc, 0.0)
    pool = cast_pool(theme)
    cast = rnd.sample(pool, 3)
    for (x, y, s), it, mv in zip([(430, 760, 170), (960, 730, 195), (1490, 760, 170)], cast, ["sway", "bounce", "sway"]):
        dancer(cr, it, x, y, s, 0.3, 0.45, 0, mv)
    l1, l2 = THEME_TITLES[theme]
    D.word_row(cr, l1, ["#ffffff", "#fff176"], W / 2, 150, 190, 0.0, 5)
    D.word_row(cr, l2, ["#fff176", "#ffffff", "#80deea"], W / 2, 330, 170, 0.0, 5)
    png = out + ".png"
    surf.write_to_png(png)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", png, "-vf", "scale=1280:720", "-q:v", "2", out], check=True)
    import os

    os.remove(png)
