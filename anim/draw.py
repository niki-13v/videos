"""Vector cartoon drawing with cairo: characters, objects, backgrounds, effects.
Everything is drawn from code, so characters look identical in every video."""
import math
import random

import cairo

OUTLINE = (0.24, 0.14, 0.08)


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


SHADE = True


def shade_source(cr, c, x0=None, y0=None, x1=None, y1=None):
    """Soft 3D look: light from top-left, darker toward bottom-right (uses current path bounds)."""
    if not SHADE or c in ((1, 1, 1),) and False:
        cr.set_source_rgb(*c)
        return
    if x0 is None:
        x0, y0, x1, y1 = cr.path_extents()
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    cx, cy = x0 + w * 0.32, y0 + h * 0.28
    r = max(w, h) * 1.05
    g = cairo.RadialGradient(cx, cy, r * 0.04, cx, cy, r)
    light = tuple(min(1, v * 0.6 + 0.4) for v in c)
    dark = tuple(v * 0.78 for v in c)
    g.add_color_stop_rgb(0, *light)
    g.add_color_stop_rgb(0.45, *c)
    g.add_color_stop_rgb(1, *dark)
    cr.set_source(g)


def ellipse(cr, x, y, rx, ry, fill, stroke=OUTLINE, lw=6):
    cr.save()
    cr.translate(x, y)
    cr.scale(rx, ry)
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()
    if stroke and max(rx, ry) > 14 and fill not in ((1, 1, 1),):
        shade_source(cr, fill)
    else:
        cr.set_source_rgb(*fill)
    if stroke:
        cr.fill_preserve()
        cr.set_source_rgb(*stroke)
        cr.set_line_width(lw)
        cr.stroke()
    else:
        cr.fill()


def face(cr, x, y, s, mouth=0.0, blink=False, happy=True):
    """Cute eyes + mouth used on every object so they feel alive."""
    for dx in (-0.32, 0.32):
        ex, ey = x + dx * s, y - 0.1 * s
        if blink:
            cr.set_source_rgb(*OUTLINE)
            cr.set_line_width(max(3, s * 0.06))
            cr.move_to(ex - 0.12 * s, ey)
            cr.line_to(ex + 0.12 * s, ey)
            cr.stroke()
        else:
            ellipse(cr, ex, ey, 0.13 * s, 0.16 * s, (0.1, 0.07, 0.06), None)
            ellipse(cr, ex + 0.04 * s, ey - 0.06 * s, 0.05 * s, 0.05 * s, (1, 1, 1), None)
    # cheeks
    cr.set_source_rgba(1, 0.45, 0.55, 0.45)
    for dx in (-0.5, 0.5):
        cr.arc(x + dx * s, y + 0.12 * s, 0.1 * s, 0, 2 * math.pi)
        cr.fill()
    if mouth > 0.08:
        ellipse(cr, x, y + 0.22 * s, 0.14 * s, 0.05 * s + 0.14 * s * mouth, (0.55, 0.1, 0.15), OUTLINE, max(2, s * 0.04))
    else:
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(max(3, s * 0.05))
        cr.arc(x, y + 0.1 * s, 0.16 * s, 0.2 * math.pi, 0.8 * math.pi) if happy else None
        cr.stroke()


# ---------------------------------------------------------------- Bramble
BROWN, BELLY, PINK, SCARF = hexc("#a0672f"), hexc("#f6e0b5"), hexc("#f4a6b5"), hexc("#e8413c")


def bramble(cr, x, y, s, t, mouth=0.0, wave=0.0, blink=False, jump=0.0, cheer=0.0, happy=False):
    from . import sprites

    if sprites.available():
        return sprites.bramble(cr, x, y, s, t, mouth, wave, blink, jump, cheer, happy)
    return _bramble2d(cr, x, y, s, t, mouth, wave, blink, jump, cheer, happy)


def _bramble2d(cr, x, y, s, t, mouth=0.0, wave=0.0, blink=False, jump=0.0, cheer=0.0, happy=False):
    """Bramble the bear. (x, y) = feet centre, s = scale (1.0 ~ 520px tall)."""
    bob = math.sin(t * 2 * math.pi * 0.9) * 6 * s
    squash = 1 + 0.03 * math.sin(t * 2 * math.pi * 1.8)
    cr.save()
    cr.translate(x, y - jump * 140 * s)
    cr.scale(s, s * squash)
    # shadow
    cr.save()
    cr.scale(1, 0.25)
    cr.set_source_rgba(0, 0, 0, 0.15 * (1 - jump * 0.5))
    cr.arc(0, jump * 560, 150 - jump * 30, 0, 2 * math.pi)
    cr.fill()
    cr.restore()
    by = -200 + bob
    # feet
    for dx in (-70, 70):
        ellipse(cr, dx, -25, 60, 35, BROWN)
        ellipse(cr, dx, -22, 32, 18, BELLY, None)
    # left arm (resting)
    cr.set_source_rgb(*OUTLINE)
    _arm(cr, -118, by - 10, 0.35 + 0.06 * math.sin(t * 3) + cheer * (2.3 + 0.2 * math.sin(t * 16)))
    # right arm (waves)
    _arm(cr, 118, by - 10, -0.35 - max(wave * (2.2 + 0.35 * math.sin(t * 14)), cheer * (2.3 + 0.2 * math.sin(t * 16 + 1))))
    # body
    ellipse(cr, 0, by + 40, 145, 160, BROWN)
    ellipse(cr, 0, by + 65, 95, 110, BELLY, None)
    # head
    hy = by - 205 + bob * 0.4
    for dx in (-115, 115):
        ellipse(cr, dx, hy - 105, 52, 52, BROWN)
        ellipse(cr, dx, hy - 105, 28, 28, PINK, None)
    ellipse(cr, 0, hy, 165, 145, BROWN)
    ellipse(cr, 0, hy + 50, 78, 58, BELLY, None)
    # eyes
    for dx in (-58, 58):
        if happy:
            cr.set_source_rgb(*OUTLINE)
            cr.set_line_width(9)
            cr.arc(dx, hy - 10, 20, 1.15 * math.pi, 1.85 * math.pi)
            cr.stroke()
        elif blink:
            cr.set_source_rgb(*OUTLINE)
            cr.set_line_width(9)
            cr.arc(dx, hy - 22, 20, 0.15 * math.pi, 0.85 * math.pi)
            cr.stroke()
        else:
            ellipse(cr, dx, hy - 20, 22, 28, (0.08, 0.05, 0.04), None)
            ellipse(cr, dx + 8, hy - 31, 9, 9, (1, 1, 1), None)
    cr.set_source_rgba(1, 0.45, 0.55, 0.5)
    for dx in (-95, 95):
        cr.arc(dx, hy + 30, 22, 0, 2 * math.pi)
        cr.fill()
    ellipse(cr, 0, hy + 22, 24, 17, (0.15, 0.08, 0.05), None)
    if mouth > 0.08:
        ellipse(cr, 0, hy + 70, 26, 8 + 30 * mouth, (0.6, 0.12, 0.15), OUTLINE, 5)
        ellipse(cr, 0, hy + 74 + 18 * mouth, 14, 6 * mouth + 2, hexc("#f47c8a"), None)
    else:
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(7)
        cr.arc(0, hy + 45, 34, 0.25 * math.pi, 0.75 * math.pi)
        cr.stroke()
    # scarf
    cr.set_source_rgb(*SCARF)
    cr.rectangle(-120, hy + 118, 240, 42)
    cr.fill_preserve()
    cr.set_source_rgb(*OUTLINE)
    cr.set_line_width(6)
    cr.stroke()
    flap = 6 * math.sin(t * 5)
    cr.move_to(55, hy + 150)
    cr.line_to(95 + flap, hy + 235)
    cr.line_to(50 + flap, hy + 240)
    cr.line_to(30, hy + 155)
    cr.close_path()
    shade_source(cr, SCARF)
    cr.fill_preserve()
    cr.set_source_rgb(*OUTLINE)
    cr.stroke()
    cr.restore()


def _arm(cr, x, y, angle):
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    ellipse(cr, 0, 70, 38, 80, BROWN)
    ellipse(cr, 0, 130, 32, 30, BROWN)
    cr.restore()


# ---------------------------------------------------------------- objects
def obj(cr, kind, color, x, y, s, t, mouth=0.0, blink=False):
    """Kid-friendly objects with faces. s ~ radius in px."""
    c = hexc(color)
    wob = math.sin(t * 4) * 0.04
    cr.save()
    cr.translate(x, y)
    cr.rotate(wob)
    if kind == "apple":
        ellipse(cr, -s * 0.28, 0, s * 0.7, s * 0.85, c)
        ellipse(cr, s * 0.28, 0, s * 0.7, s * 0.85, c)
        ellipse(cr, 0, s * 0.05, s * 0.75, s * 0.8, c, None)
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(s * 0.08)
        cr.move_to(0, -s * 0.7)
        cr.curve_to(0, -s * 0.9, s * 0.1, -s * 1.05, s * 0.15, -s * 1.1)
        cr.stroke()
        ellipse(cr, s * 0.32, -s * 0.95, s * 0.25, s * 0.12, hexc("#4caf50"), OUTLINE, 4)
        ellipse(cr, -s * 0.45, -s * 0.35, s * 0.12, s * 0.2, (1, 1, 1), None)
        face(cr, 0, s * 0.1, s * 0.8, mouth, blink)
    elif kind == "balloon":
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(4)
        cr.move_to(0, s * 1.05)
        for k in range(1, 9):
            cr.line_to(math.sin(k + t * 3) * 12, s * 1.05 + k * s * 0.12)
        cr.stroke()
        ellipse(cr, 0, 0, s * 0.85, s * 1.05, c)
        cr.move_to(-s * 0.12, s * 1.15)
        cr.line_to(s * 0.12, s * 1.15)
        cr.line_to(0, s * 1.02)
        cr.close_path()
        shade_source(cr, c)
        cr.fill()
        ellipse(cr, -s * 0.38, -s * 0.5, s * 0.14, s * 0.26, (1, 1, 1), None)
        face(cr, 0, 0, s * 0.85, mouth, blink)
    elif kind == "star":
        cr.move_to(0, -s)
        for k in range(1, 10):
            r = s if k % 2 == 0 else s * 0.48
            a = -math.pi / 2 + k * math.pi / 5
            cr.line_to(r * math.cos(a), r * math.sin(a))
        cr.close_path()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        shade_source(cr, c)
        cr.fill_preserve()
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(7)
        cr.stroke()
        face(cr, 0, s * 0.08, s * 0.55, mouth, blink)
    elif kind == "frog":
        ellipse(cr, 0, s * 0.2, s, s * 0.75, c)
        for dx in (-0.5, 0.5):
            ellipse(cr, dx * s, -s * 0.45, s * 0.3, s * 0.3, c)
            ellipse(cr, dx * s, -s * 0.45, s * 0.17, s * 0.19, (1, 1, 1), None)
            if not blink:
                ellipse(cr, dx * s, -s * 0.43, s * 0.1, s * 0.12, (0.1, 0.07, 0.06), None)
        cr.set_source_rgba(1, 0.45, 0.55, 0.45)
        for dx in (-0.6, 0.6):
            cr.arc(dx * s, s * 0.2, s * 0.12, 0, 2 * math.pi)
            cr.fill()
        if mouth > 0.08:
            ellipse(cr, 0, s * 0.25, s * 0.3, s * 0.06 + s * 0.15 * mouth, (0.55, 0.1, 0.15), OUTLINE, 4)
        else:
            cr.set_source_rgb(*OUTLINE)
            cr.set_line_width(6)
            cr.arc(0, s * 0.02, s * 0.45, 0.25 * math.pi, 0.75 * math.pi)
            cr.stroke()
    elif kind == "fish":
        cr.move_to(s * 0.6, 0)
        cr.line_to(s * 1.15, -s * 0.5)
        cr.line_to(s * 1.15, s * 0.5)
        cr.close_path()
        shade_source(cr, c)
        cr.fill_preserve()
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(6)
        cr.stroke()
        ellipse(cr, 0, 0, s * 0.85, s * 0.62, c)
        face(cr, -s * 0.25, 0, s * 0.55, mouth, blink)
    elif kind == "grapes":
        pts = [(0, -0.55), (-0.38, -0.55), (0.38, -0.55), (-0.2, -0.2), (0.2, -0.2), (-0.55, -0.2),
               (0.55, -0.2), (0, 0.15), (-0.38, 0.15), (0.38, 0.15), (-0.2, 0.48), (0.2, 0.48), (0, 0.78)]
        for px, py in pts:
            ellipse(cr, px * s, py * s, s * 0.25, s * 0.25, c, OUTLINE, 4)
            ellipse(cr, px * s - s * 0.08, py * s - s * 0.08, s * 0.05, s * 0.05, (1, 1, 1), None)
        ellipse(cr, 0.15 * s, -0.9 * s, s * 0.3, s * 0.14, hexc("#4caf50"), OUTLINE, 4)
        face(cr, 0, -s * 0.05, s * 0.6, mouth, blink)
    cr.restore()


# ---------------------------------------------------------------- scene
def background(cr, w, h, t, tint=None, tint_amt=0.0):
    sky = cairo.LinearGradient(0, 0, 0, h)
    top, bot = hexc("#6ec6ff"), hexc("#c9ecff")
    if tint:
        tc = hexc(tint)
        top = tuple(top[i] * (1 - tint_amt * 0.35) + tc[i] * tint_amt * 0.35 for i in range(3))
    sky.add_color_stop_rgb(0, *top)
    sky.add_color_stop_rgb(1, *bot)
    cr.set_source(sky)
    cr.paint()
    # sun with rays
    sx, sy = w * 0.88, h * 0.16
    cr.save()
    cr.translate(sx, sy)
    cr.rotate(t * 0.3)
    cr.set_source_rgba(1, 0.85, 0.2, 0.5)
    for k in range(12):
        cr.save()
        cr.rotate(k * math.pi / 6)
        cr.move_to(-14, 95)
        cr.line_to(14, 95)
        cr.line_to(0, 150)
        cr.close_path()
        cr.fill()
        cr.restore()
    cr.restore()
    ellipse(cr, sx, sy, 85, 85, hexc("#ffd23f"), hexc("#f2a20c"), 6)
    # clouds
    for i, (cx, cy, sc) in enumerate([(0.15, 0.15, 1.0), (0.5, 0.1, 0.8), (0.72, 0.28, 0.6)]):
        x = (cx * w + t * 25 * (1 + i * 0.3)) % (w + 400) - 200
        for dx, dy, r in [(-60, 10, 55), (0, -15, 70), (60, 10, 55), (0, 20, 50)]:
            ellipse(cr, x + dx * sc, cy * h + dy * sc, r * sc * 1.2, r * sc, (1, 1, 1), None)
    # hills
    for col, base, amp, ph in [("#8fd468", 0.68, 40, 0.0), ("#6cc04a", 0.76, 30, 1.5)]:
        cr.move_to(0, h)
        for x in range(0, w + 41, 40):
            cr.line_to(x, h * base + amp * math.sin(x / 300 + ph))
        cr.line_to(w, h)
        cr.close_path()
        cr.set_source_rgb(*hexc(col))
        cr.fill()
    # flowers
    rnd = random.Random(3)
    for _ in range(26):
        fx, fy = rnd.uniform(0, w), rnd.uniform(h * 0.8, h * 0.98)
        fc = hexc(rnd.choice(["#ff6b9d", "#ffd23f", "#ffffff", "#b388ff"]))
        sway = 4 * math.sin(t * 2 + fx)
        for k in range(5):
            a = k * 2 * math.pi / 5
            ellipse(cr, fx + sway + 11 * math.cos(a), fy + 11 * math.sin(a), 8, 8, fc, None)
        ellipse(cr, fx + sway, fy, 6, 6, hexc("#ffb300"), None)


def rays(cr, x, y, t, color, alpha):
    """Spinning sunburst behind a revealed object."""
    if alpha <= 0:
        return
    c = tuple(0.25 * v + 0.75 for v in hexc(color))  # near-white tint: bright over any background
    cr.save()
    cr.translate(x, y)
    cr.rotate(t * 0.8)
    for k in range(16):
        cr.move_to(0, 0)
        cr.arc(0, 0, 2400, k * math.pi / 8, k * math.pi / 8 + math.pi / 16)
        cr.close_path()
        cr.set_source_rgba(*c, 0.5 * alpha)
        cr.fill()
    glow = cairo.RadialGradient(0, 0, 0, 0, 0, 380)
    glow.add_color_stop_rgba(0, 1, 1, 1, 0.8 * alpha)
    glow.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(glow)
    cr.arc(0, 0, 380, 0, 2 * math.pi)
    cr.fill()
    cr.restore()


def word_row(cr, text, colors, cx, y, size, t, pop):
    """Rainbow word with each letter bouncing, properly spaced."""
    cr.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size)
    widths = [cr.text_extents(ch).x_advance for ch in text]
    x = cx - sum(widths) / 2
    for k, ch in enumerate(text):
        big_word(cr, ch, colors[k % len(colors)], x + widths[k] / 2, y + 12 * math.sin(t * 5 + k), size, pop - k * 0.08)
        x += widths[k]


def big_word(cr, text, color, x, y, size, pop):
    """Bouncy outlined word. pop: 0..1 entrance progress."""
    if pop <= 0:
        return
    sc = elastic(pop)
    cr.save()
    cr.translate(x, y)
    cr.scale(sc, sc)
    cr.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size)
    ext = cr.text_extents(text)
    cr.move_to(-ext.width / 2 - ext.x_bearing, ext.height / 2)
    cr.text_path(text)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_source_rgb(1, 1, 1)
    cr.set_line_width(size * 0.22)
    cr.stroke_preserve()
    cr.set_source_rgb(*hexc(color))
    cr.fill_preserve()
    cr.set_source_rgb(*OUTLINE)
    cr.set_line_width(size * 0.04)
    cr.stroke()
    cr.restore()


def confetti(cr, x, y, age, seed, colors):
    if age < 0 or age > 2.2:
        return
    rnd = random.Random(seed)
    for _ in range(70):
        a, v = rnd.uniform(0, 2 * math.pi), rnd.uniform(300, 900)
        px = x + math.cos(a) * v * age
        py = y + math.sin(a) * v * age + 600 * age * age
        cr.save()
        cr.translate(px, py)
        cr.rotate(rnd.uniform(0, 6) + age * rnd.uniform(-8, 8))
        cr.set_source_rgba(*hexc(rnd.choice(colors)), max(0, 1 - age / 2.2))
        cr.rectangle(-10, -6, 20, 12)
        cr.fill()
        cr.restore()


def question_mark(cr, x, y, t, alpha):
    if alpha <= 0:
        return
    cr.save()
    cr.translate(x, y + 10 * math.sin(t * 6))
    cr.rotate(0.15 * math.sin(t * 5))
    cr.push_group()
    big_word(cr, "?", "#ffffff", 0, 0, 200, 1)
    cr.pop_group_to_source()
    cr.paint_with_alpha(alpha)
    cr.restore()


def elastic(p):
    p = max(0.0, min(1.0, p))
    if p in (0.0, 1.0):
        return p
    return 2 ** (-10 * p) * math.sin((p * 10 - 0.75) * (2 * math.pi) / 3) + 1


def ease_out(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def _sky(cr, w, h, top, bot):
    g = cairo.LinearGradient(0, 0, 0, h)
    g.add_color_stop_rgb(0, *hexc(top))
    g.add_color_stop_rgb(1, *hexc(bot))
    cr.set_source(g)
    cr.paint()


def _clouds(cr, w, h, t):
    for i, (cx, cy, sc) in enumerate([(0.15, 0.12, 1.0), (0.5, 0.08, 0.8), (0.72, 0.22, 0.6)]):
        x = (cx * w + t * 25 * (1 + i * 0.3)) % (w + 400) - 200
        for dx, dy, r in [(-60, 10, 55), (0, -15, 70), (60, 10, 55), (0, 20, 50)]:
            ellipse(cr, x + dx * sc, cy * h + dy * sc, r * sc * 1.2, r * sc, (1, 1, 1), None)


def bg_beach(cr, w, h, t):
    _sky(cr, w, h, "#4fc3f7", "#e1f5fe")
    ellipse(cr, w * 0.85, h * 0.14, 80, 80, hexc("#ffd23f"), hexc("#f2a20c"), 6)
    _clouds(cr, w, h, t)
    sea = h * 0.6
    cr.rectangle(0, sea, w, h)
    cr.set_source_rgb(*hexc("#29b6f6"))
    cr.fill()
    for row in range(3):
        y = sea + 25 + row * 45
        cr.move_to(0, y)
        for x in range(0, w + 21, 20):
            cr.line_to(x, y + 8 * math.sin(x / 40 + t * 2 + row))
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.set_line_width(5)
        cr.stroke()
    cr.move_to(0, h)
    for x in range(0, w + 41, 40):
        cr.line_to(x, h * 0.78 + 18 * math.sin(x / 250))
    cr.line_to(w, h)
    cr.close_path()
    cr.set_source_rgb(*hexc("#ffe0a3"))
    cr.fill()
    rnd = random.Random(5)
    for _ in range(9):
        sx, sy = rnd.uniform(0, w), rnd.uniform(h * 0.86, h * 0.98)
        cr.save()
        cr.translate(sx, sy)
        cr.set_source_rgb(*hexc(rnd.choice(["#ff8a80", "#ffffff", "#ffd180"])))
        cr.arc(0, 0, 16, math.pi, 2 * math.pi)
        cr.fill()
        cr.restore()


def bg_playroom(cr, w, h, t):
    cr.set_source_rgb(*hexc("#fff3e0"))
    cr.paint()
    for k in range(0, w, 120):
        cr.rectangle(k, 0, 60, h * 0.72)
        cr.set_source_rgb(*hexc("#ffe0b2"))
        cr.fill()
    # window
    wx, wy, ww, wh = w * 0.06, h * 0.1, w * 0.2, h * 0.32
    cr.rectangle(wx, wy, ww, wh)
    cr.set_source_rgb(*hexc("#81d4fa"))
    cr.fill_preserve()
    cr.set_source_rgb(*hexc("#ffffff"))
    cr.set_line_width(16)
    cr.stroke()
    cr.move_to(wx + ww / 2, wy)
    cr.line_to(wx + ww / 2, wy + wh)
    cr.move_to(wx, wy + wh / 2)
    cr.line_to(wx + ww, wy + wh / 2)
    cr.stroke()
    # bunting
    cols = ["#e53935", "#fdd835", "#1e88e5", "#43a047", "#8e24aa", "#fb8c00"]
    n = 14
    for k in range(n):
        x0 = w * 0.3 + k * (w * 0.68 / n)
        sway = 4 * math.sin(t * 2 + k)
        cr.move_to(x0, h * 0.06)
        cr.line_to(x0 + w * 0.68 / n, h * 0.06)
        cr.line_to(x0 + w * 0.34 / n, h * 0.14 + sway)
        cr.close_path()
        cr.set_source_rgb(*hexc(cols[k % 6]))
        cr.fill()
    # floor + rug
    cr.rectangle(0, h * 0.72, w, h)
    cr.set_source_rgb(*hexc("#d7a86e"))
    cr.fill()
    for k in range(0, w, 160):
        cr.move_to(k, h * 0.72)
        cr.line_to(k - 60, h)
        cr.set_source_rgba(0, 0, 0, 0.08)
        cr.set_line_width(4)
        cr.stroke()
    ellipse(cr, w * 0.55, h * 0.9, w * 0.4, h * 0.08, hexc("#ce93d8"), None)
    ellipse(cr, w * 0.55, h * 0.9, w * 0.32, h * 0.055, hexc("#e1bee7"), None)


def scene_bg(cr, kind, w, h, t):
    from . import sprites

    if sprites.available() and sprites.background(cr, kind, w, h):
        # 3D set; keep only small moving life on top
        if kind == "beach":
            bird(cr, (w * 0.3 + t * 60) % (w + 200) - 100, h * 0.15 + 10 * math.sin(t), 1.0, t)
            bird(cr, (w * 0.5 + t * 50) % (w + 200) - 100, h * 0.2 + 10 * math.sin(t + 1), 0.8, t + 0.3)
        elif kind != "playroom":
            for k, col in enumerate(["#ff7043", "#ab47bc", "#29b6f6"]):
                bx = w * (0.3 + 0.25 * k) + 160 * math.sin(t * 0.5 + k * 2)
                by = h * (0.25 + 0.08 * k) + 60 * math.sin(t * 1.3 + k)
                butterfly(cr, bx, by, 1.0, t + k, col)
        return
    if kind == "beach":
        bg_beach(cr, w, h, t)
    elif kind == "playroom":
        bg_playroom(cr, w, h, t)
    else:
        background(cr, w, h, t)
    scenery(cr, kind, w, h, t)


# ------------------------------------------------------------------ scenery details
def tree(cr, x, y, s, t):
    sway = math.sin(t * 1.2 + x) * 0.02
    cr.save()
    cr.translate(x, y)
    cr.rotate(sway)
    cr.rectangle(-22 * s, -150 * s, 44 * s, 150 * s)
    shade_source(cr, hexc("#8d5a33"))
    cr.fill_preserve()
    cr.set_source_rgb(*OUTLINE)
    cr.set_line_width(5)
    cr.stroke()
    for dx, dy, r in [(-70, -190, 85), (70, -190, 85), (0, -260, 100), (0, -170, 90)]:
        ellipse(cr, dx * s, dy * s, r * s, r * s * 0.92, hexc("#4caf50"))
    for dx, dy in [(-50, -220), (40, -270), (60, -170)]:
        ellipse(cr, dx * s, dy * s, 12 * s, 12 * s, hexc("#e53935"), OUTLINE, 3)
    cr.restore()


def bush(cr, x, y, s):
    for dx, r in [(-45, 45), (0, 60), (45, 45)]:
        ellipse(cr, x + dx * s, y - r * s * 0.6, r * s, r * s * 0.8, hexc("#66bb6a"))


def butterfly(cr, x, y, s, t, color):
    flap = abs(math.sin(t * 14))
    c = hexc(color)
    cr.save()
    cr.translate(x, y)
    for side in (-1, 1):
        cr.save()
        cr.scale(side * (0.3 + 0.7 * flap), 1)
        ellipse(cr, 18 * s, -10 * s, 18 * s, 15 * s, c, OUTLINE, 3)
        ellipse(cr, 14 * s, 12 * s, 12 * s, 10 * s, c, OUTLINE, 3)
        cr.restore()
    ellipse(cr, 0, 0, 5 * s, 18 * s, OUTLINE, None)
    cr.restore()


def bird(cr, x, y, s, t):
    f = math.sin(t * 10) * 12 * s
    cr.set_source_rgb(*OUTLINE)
    cr.set_line_width(5)
    cr.move_to(x - 30 * s, y - f)
    cr.curve_to(x - 15 * s, y - 15 * s, x - 5 * s, y - 10 * s, x, y)
    cr.curve_to(x + 5 * s, y - 10 * s, x + 15 * s, y - 15 * s, x + 30 * s, y - f)
    cr.stroke()


def palm(cr, x, y, s, t):
    cr.save()
    cr.translate(x, y)
    for k in range(9):
        ellipse(cr, math.sin(k * 0.25) * 30 * s, -k * 45 * s, 26 * s, 28 * s, hexc("#a1887f"), OUTLINE, 4)
    top = (math.sin(8 * 0.25) * 30 * s, -400 * s)
    for a in range(6):
        ang = -math.pi / 2 + (a - 2.5) * 0.55 + math.sin(t * 1.5 + a) * 0.04
        cr.save()
        cr.translate(*top)
        cr.rotate(ang + math.pi / 2)
        cr.move_to(0, 0)
        cr.curve_to(-60 * s, -60 * s, -40 * s, -170 * s, 0, -210 * s)
        cr.curve_to(40 * s, -170 * s, 60 * s, -60 * s, 0, 0)
        shade_source(cr, hexc("#43a047"))
        cr.fill_preserve()
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(4)
        cr.stroke()
        cr.restore()
    for dx in (-18, 18):
        ellipse(cr, top[0] + dx * s, top[1] + 20 * s, 20 * s, 20 * s, hexc("#795548"), OUTLINE, 3)
    cr.restore()


def toy_shelf(cr, x, y, s, t):
    cr.rectangle(x, y, 380 * s, 22 * s)
    shade_source(cr, hexc("#a1887f"))
    cr.fill()
    cols = ["#e53935", "#1e88e5", "#fdd835", "#43a047"]
    for k, c in enumerate(cols):
        bx = x + 30 * s + k * 85 * s
        cr.rectangle(bx, y - 70 * s, 68 * s, 70 * s)
        shade_source(cr, hexc(c))
        cr.fill_preserve()
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(4)
        cr.stroke()
        cr.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(48 * s)
        cr.set_source_rgb(1, 1, 1)
        cr.move_to(bx + 18 * s, y - 18 * s)
        cr.show_text("ABCD"[k])


def scenery(cr, kind, w, h, t):
    """Moving details layered on top of the base background."""
    if kind == "beach":
        palm(cr, w * 0.07, h * 0.86, 1.0, t)
        bird(cr, (w * 0.3 + t * 60) % (w + 200) - 100, h * 0.2 + 10 * math.sin(t), 1.0, t)
        bird(cr, (w * 0.5 + t * 50) % (w + 200) - 100, h * 0.26 + 10 * math.sin(t + 1), 0.8, t + 0.3)
    elif kind == "playroom":
        toy_shelf(cr, w * 0.3, h * 0.66, 1.0, t)
    else:
        tree(cr, w * 0.04, h * 0.74, 1.0, t)
        tree(cr, w * 0.97, h * 0.72, 0.9, t)
        bush(cr, w * 0.4, h * 0.79, 1.0)
        bush(cr, w * 0.85, h * 0.8, 0.8)
        for k, col in enumerate(["#ff7043", "#ab47bc", "#29b6f6"]):
            bx = w * (0.3 + 0.25 * k) + 160 * math.sin(t * 0.5 + k * 2)
            by = h * (0.25 + 0.08 * k) + 60 * math.sin(t * 1.3 + k)
            butterfly(cr, bx, by, 1.0, t + k, col)
