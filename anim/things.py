"""More cute objects and animals. Each draws centred on (0,0) with size s (~radius)."""
import math

import cairo

from .draw import OUTLINE, ellipse, face, hexc, obj

WHITE, BLACK, PINKC = (1, 1, 1), (0.1, 0.07, 0.06), hexc("#f8a5b6")


def _poly(cr, pts, fill, lw=6):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_source_rgb(*fill)
    cr.fill_preserve()
    cr.set_source_rgb(*OUTLINE)
    cr.set_line_width(lw)
    cr.stroke()


def _rrect(cr, x, y, w, h, r, fill, lw=6):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()
    cr.set_source_rgb(*fill)
    cr.fill_preserve()
    cr.set_source_rgb(*OUTLINE)
    cr.set_line_width(lw)
    cr.stroke()


def _eyes(cr, s, y, gap, blink, r=0.12):
    for dx in (-gap, gap):
        if blink:
            cr.set_source_rgb(*OUTLINE)
            cr.set_line_width(s * 0.05)
            cr.move_to(dx * s - r * s, y * s)
            cr.line_to(dx * s + r * s, y * s)
            cr.stroke()
        else:
            ellipse(cr, dx * s, y * s, r * s, r * 1.2 * s, BLACK, None)
            ellipse(cr, dx * s + r * 0.35 * s, (y - r * 0.45) * s, r * 0.4 * s, r * 0.4 * s, WHITE, None)


def _mouth(cr, s, y, mouth, w=0.16):
    if mouth > 0.08:
        ellipse(cr, 0, y * s, w * s, (0.04 + 0.16 * mouth) * s, (0.55, 0.1, 0.15), OUTLINE, max(2, s * 0.03))
    else:
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(max(3, s * 0.045))
        cr.arc(0, (y - 0.12) * s, w * 1.1 * s, 0.25 * math.pi, 0.75 * math.pi)
        cr.stroke()


def _cheeks(cr, s, y, gap):
    cr.set_source_rgba(1, 0.45, 0.55, 0.45)
    for dx in (-gap, gap):
        cr.arc(dx * s, y * s, 0.1 * s, 0, 2 * math.pi)
        cr.fill()


# ------------------------------------------------------------- shapes
def shape(cr, kind, c, s, mouth, blink):
    if kind == "circle":
        ellipse(cr, 0, 0, s, s, c, OUTLINE, 7)
    elif kind == "square":
        _rrect(cr, -s * 0.9, -s * 0.9, s * 1.8, s * 1.8, s * 0.12, c, 7)
    elif kind == "rectangle":
        _rrect(cr, -s * 1.2, -s * 0.7, s * 2.4, s * 1.4, s * 0.1, c, 7)
    elif kind == "triangle":
        _poly(cr, [(0, -s * 1.05), (s * 1.05, s * 0.8), (-s * 1.05, s * 0.8)], c, 7)
    elif kind == "oval":
        ellipse(cr, 0, 0, s * 1.2, s * 0.8, c, OUTLINE, 7)
    elif kind == "diamond":
        _poly(cr, [(0, -s * 1.1), (s * 0.8, 0), (0, s * 1.1), (-s * 0.8, 0)], c, 7)
    elif kind == "heart":
        cr.move_to(0, s * 0.95)
        cr.curve_to(-s * 1.4, s * 0.0, -s * 0.9, -s * 1.15, 0, -s * 0.45)
        cr.curve_to(s * 0.9, -s * 1.15, s * 1.4, s * 0.0, 0, s * 0.95)
        cr.set_source_rgb(*c)
        cr.fill_preserve()
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(7)
        cr.stroke()
    elif kind == "star":
        obj(cr, "star", "#%02x%02x%02x" % tuple(int(v * 255) for v in c), 0, 0, s, 0, mouth, blink)
        return
    face(cr, 0, s * 0.1 if kind != "triangle" else s * 0.3, s * (0.75 if kind != "triangle" else 0.6), mouth, blink)


# ------------------------------------------------------------- fruits & things
def thing(cr, kind, c, s, t, mouth, blink):
    if kind == "banana":
        cr.move_to(-s * 1.0, -s * 0.5)
        cr.curve_to(-s * 0.6, s * 0.75, s * 0.7, s * 0.75, s * 1.05, -s * 0.35)
        cr.curve_to(s * 0.6, s * 0.2, -s * 0.5, s * 0.25, -s * 1.0, -s * 0.5)
        cr.set_source_rgb(*c)
        cr.fill_preserve()
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(7)
        cr.stroke()
        ellipse(cr, -s * 1.02, -s * 0.52, s * 0.08, s * 0.08, hexc("#6d4c2f"), None)
        face(cr, 0, s * 0.22, s * 0.38, mouth, blink)
    elif kind == "strawberry":
        cr.move_to(0, s * 1.0)
        cr.curve_to(-s * 1.1, s * 0.2, -s * 0.9, -s * 0.8, 0, -s * 0.65)
        cr.curve_to(s * 0.9, -s * 0.8, s * 1.1, s * 0.2, 0, s * 1.0)
        cr.set_source_rgb(*c)
        cr.fill_preserve()
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(7)
        cr.stroke()
        for px, py in [(-0.45, -0.2), (0.45, -0.2), (-0.25, 0.45), (0.3, 0.5), (0, 0.75), (-0.6, 0.2), (0.6, 0.2)]:
            ellipse(cr, px * s, py * s, s * 0.035, s * 0.06, hexc("#ffe082"), None)
        _poly(cr, [(-s * 0.6, -s * 0.7), (0, -s * 0.55), (s * 0.6, -s * 0.7), (s * 0.15, -s * 0.85), (0, -s * 1.05), (-s * 0.15, -s * 0.85)], hexc("#43a047"), 5)
        face(cr, 0, s * 0.05, s * 0.65, mouth, blink)
    elif kind == "orange":
        ellipse(cr, 0, 0, s, s * 0.95, c, OUTLINE, 7)
        ellipse(cr, s * 0.3, -s * 0.95, s * 0.3, s * 0.13, hexc("#43a047"), OUTLINE, 4)
        face(cr, 0, s * 0.1, s * 0.75, mouth, blink)
    elif kind == "watermelon":
        cr.move_to(-s * 1.2, -s * 0.4)
        cr.arc_negative(0, -s * 0.4, s * 1.2, math.pi, 0)
        cr.close_path()
        cr.set_source_rgb(*hexc("#43a047"))
        cr.fill()
        cr.move_to(-s * 1.05, -s * 0.4)
        cr.arc_negative(0, -s * 0.4, s * 1.05, math.pi, 0)
        cr.close_path()
        cr.set_source_rgb(*c)
        cr.fill()
        cr.move_to(-s * 1.2, -s * 0.4)
        cr.arc_negative(0, -s * 0.4, s * 1.2, math.pi, 0)
        cr.close_path()
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(7)
        cr.stroke()
        for px, py in [(-0.6, 0.0), (0.6, 0.0), (-0.3, 0.3), (0.3, 0.3)]:
            ellipse(cr, px * s, py * s, s * 0.05, s * 0.08, BLACK, None)
        face(cr, 0, -s * 0.1, s * 0.5, mouth, blink)
    elif kind == "pear":
        ellipse(cr, 0, s * 0.3, s * 0.8, s * 0.7, c, None)
        ellipse(cr, 0, -s * 0.35, s * 0.5, s * 0.55, c, None)
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(7)
        cr.move_to(0, -s * 0.9)
        cr.curve_to(-s * 0.55, -s * 0.9, -s * 0.5, -s * 0.2, -s * 0.75, s * 0.15)
        cr.curve_to(-s * 0.95, s * 0.8, -s * 0.4, s * 1.0, 0, s * 1.0)
        cr.curve_to(s * 0.4, s * 1.0, s * 0.95, s * 0.8, s * 0.75, s * 0.15)
        cr.curve_to(s * 0.5, -s * 0.2, s * 0.55, -s * 0.9, 0, -s * 0.9)
        cr.stroke()
        cr.move_to(0, -s * 0.9)
        cr.line_to(s * 0.1, -s * 1.15)
        cr.stroke()
        face(cr, 0, s * 0.3, s * 0.5, mouth, blink)
    elif kind == "cherry":
        cr.set_source_rgb(*hexc("#5d8a2f"))
        cr.set_line_width(7)
        cr.move_to(-s * 0.45, -s * 0.1)
        cr.curve_to(-s * 0.3, -s * 0.8, 0, -s * 1.0, s * 0.1, -s * 1.1)
        cr.move_to(s * 0.5, -s * 0.05)
        cr.curve_to(s * 0.4, -s * 0.7, s * 0.2, -s * 1.0, s * 0.1, -s * 1.1)
        cr.stroke()
        for dx in (-0.45, 0.5):
            ellipse(cr, dx * s, s * 0.35, s * 0.48, s * 0.48, c, OUTLINE, 6)
            face(cr, dx * s, s * 0.4, s * 0.3, mouth, blink)
    elif kind == "ball":
        ellipse(cr, 0, 0, s, s, c, OUTLINE, 7)
        cr.save()
        cr.arc(0, 0, s, 0, 2 * math.pi)
        cr.clip()
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(-s, -s * 0.18, s * 2, s * 0.36)
        cr.fill()
        cr.restore()
        ellipse(cr, 0, 0, s, s, c, OUTLINE, 7) if False else None
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(7)
        cr.arc(0, 0, s, 0, 2 * math.pi)
        cr.stroke()
        face(cr, 0, s * 0.45, s * 0.4, mouth, blink)
    elif kind == "car":
        _rrect(cr, -s * 1.2, -s * 0.2, s * 2.4, s * 0.75, s * 0.25, c, 7)
        _rrect(cr, -s * 0.65, -s * 0.75, s * 1.3, s * 0.65, s * 0.25, c, 7)
        _rrect(cr, -s * 0.5, -s * 0.62, s * 0.45, s * 0.42, s * 0.1, hexc("#bbdefb"), 4)
        _rrect(cr, s * 0.05, -s * 0.62, s * 0.45, s * 0.42, s * 0.1, hexc("#bbdefb"), 4)
        spin = t * 6
        for dx in (-0.65, 0.65):
            ellipse(cr, dx * s, s * 0.55, s * 0.3, s * 0.3, (0.2, 0.2, 0.22), OUTLINE, 6)
            ellipse(cr, dx * s + math.cos(spin) * s * 0.1, s * 0.55 + math.sin(spin) * s * 0.1, s * 0.07, s * 0.07, (0.7, 0.7, 0.7), None)
        face(cr, s * 0.75, s * 0.15, s * 0.3, mouth, blink)
    elif kind == "cupcake":
        _poly(cr, [(-s * 0.75, 0), (s * 0.75, 0), (s * 0.55, s * 0.95), (-s * 0.55, s * 0.95)], hexc("#ffcc80"), 6)
        for k in range(-2, 3):
            cr.move_to(k * s * 0.25, s * 0.05)
            cr.line_to(k * s * 0.2, s * 0.9)
        cr.stroke()
        for dx, dy, r in [(-0.5, -0.1, 0.4), (0.5, -0.1, 0.4), (0, -0.35, 0.55), (0, -0.05, 0.6)]:
            ellipse(cr, dx * s, dy * s, r * s, r * s * 0.85, c, None)
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(6)
        cr.arc(0, -s * 0.2, s * 0.85, math.pi * 1.05, math.pi * 1.95)
        cr.stroke()
        ellipse(cr, 0, -s * 0.95, s * 0.17, s * 0.17, hexc("#e53935"), OUTLINE, 4)
        face(cr, 0, -s * 0.25, s * 0.45, mouth, blink)
    elif kind == "flower":
        for k in range(6):
            a = k * math.pi / 3 + t * 0.5
            ellipse(cr, math.cos(a) * s * 0.6, math.sin(a) * s * 0.6, s * 0.42, s * 0.42, c, OUTLINE, 5)
        ellipse(cr, 0, 0, s * 0.55, s * 0.55, hexc("#ffd54f"), OUTLINE, 5)
        face(cr, 0, s * 0.05, s * 0.4, mouth, blink)
    elif kind == "fishc":
        obj(cr, "fish", "#%02x%02x%02x" % tuple(int(v * 255) for v in c), 0, 0, s, t, mouth, blink)


# ------------------------------------------------------------- animals
def animal(cr, kind, s, t, mouth, blink):
    if kind == "cow":
        for dx in (-1, 1):
            _poly(cr, [(dx * s * 0.45, -s * 0.75), (dx * s * 0.75, -s * 1.15), (dx * s * 0.7, -s * 0.7)], hexc("#fff3e0"), 5)
            ellipse(cr, dx * s * 0.95, -s * 0.4, s * 0.35, s * 0.17, WHITE, OUTLINE, 5)
        ellipse(cr, 0, 0, s * 0.85, s * 0.9, WHITE, OUTLINE, 7)
        ellipse(cr, -s * 0.4, -s * 0.45, s * 0.22, s * 0.18, BLACK, None)
        ellipse(cr, s * 0.5, -s * 0.05, s * 0.16, s * 0.22, BLACK, None)
        ellipse(cr, 0, s * 0.5, s * 0.6, s * 0.38, PINKC, OUTLINE, 6)
        for dx in (-0.22, 0.22):
            ellipse(cr, dx * s, s * 0.45, s * 0.07, s * 0.1, (0.6, 0.3, 0.35), None)
        _eyes(cr, s, -0.15, 0.3, blink)
        _mouth(cr, s, 0.7, mouth, 0.14)
    elif kind == "pig":
        for dx in (-1, 1):
            _poly(cr, [(dx * s * 0.35, -s * 0.75), (dx * s * 0.85, -s * 1.0), (dx * s * 0.75, -s * 0.45)], PINKC, 5)
        ellipse(cr, 0, 0, s * 0.95, s * 0.85, hexc("#f9b4c4"), OUTLINE, 7)
        ellipse(cr, 0, s * 0.2, s * 0.38, s * 0.27, hexc("#f48fb1"), OUTLINE, 6)
        for dx in (-0.13, 0.13):
            ellipse(cr, dx * s, s * 0.2, s * 0.06, s * 0.1, (0.55, 0.25, 0.3), None)
        _eyes(cr, s, -0.25, 0.35, blink)
        _cheeks(cr, s, 0.15, 0.62)
        _mouth(cr, s, 0.6, mouth, 0.12)
    elif kind == "duck":
        ellipse(cr, 0, 0, s * 0.85, s * 0.85, hexc("#ffeb3b"), OUTLINE, 7)
        _poly(cr, [(0, -s * 0.8), (-s * 0.12, -s * 1.05), (s * 0.08, -s * 0.95)], hexc("#ffeb3b"), 5)
        open_ = 0.05 + 0.25 * mouth
        ellipse(cr, 0, s * 0.2 - open_ * s * 0.3, s * 0.42, s * 0.14, hexc("#ff9800"), OUTLINE, 6)
        ellipse(cr, 0, s * 0.3 + open_ * s * 0.5, s * 0.36, s * 0.12, hexc("#fb8c00"), OUTLINE, 6)
        _eyes(cr, s, -0.2, 0.32, blink)
        _cheeks(cr, s, 0.1, 0.58)
    elif kind == "chick":
        ellipse(cr, 0, 0, s * 0.8, s * 0.8, hexc("#fff176"), OUTLINE, 7)
        for k in (-1, 0, 1):
            ellipse(cr, k * s * 0.12, -s * 0.85, s * 0.08, s * 0.15, hexc("#fff176"), OUTLINE, 4)
        _poly(cr, [(-s * 0.15, s * 0.1), (s * 0.15, s * 0.1), (0, s * (0.3 + 0.2 * mouth))], hexc("#ff9800"), 5)
        _eyes(cr, s, -0.15, 0.3, blink, 0.1)
        _cheeks(cr, s, 0.15, 0.5)
    elif kind == "cat":
        for dx in (-1, 1):
            _poly(cr, [(dx * s * 0.25, -s * 0.7), (dx * s * 0.75, -s * 1.15), (dx * s * 0.85, -s * 0.4)], hexc("#ffb74d"), 6)
            _poly(cr, [(dx * s * 0.4, -s * 0.72), (dx * s * 0.7, -s * 1.0), (dx * s * 0.72, -s * 0.55)], PINKC, 0.1)
        ellipse(cr, 0, 0, s * 0.95, s * 0.82, hexc("#ffb74d"), OUTLINE, 7)
        for dx in (-0.25, 0.25):
            cr.set_source_rgb(*hexc("#f57c00"))
            cr.rectangle(dx * s - s * 0.04, -s * 0.8, s * 0.08, s * 0.25)
            cr.fill()
        _poly(cr, [(-s * 0.08, s * 0.08), (s * 0.08, s * 0.08), (0, s * 0.18)], hexc("#f06292"), 3)
        cr.set_source_rgb(*OUTLINE)
        cr.set_line_width(3)
        for dy in (0.12, 0.25):
            for dx in (-1, 1):
                cr.move_to(dx * s * 0.3, s * dy)
                cr.line_to(dx * s * 0.9, s * (dy + (dy - 0.18) * 1.2))
        cr.stroke()
        _eyes(cr, s, -0.15, 0.33, blink)
        _mouth(cr, s, 0.4, mouth, 0.12)
    elif kind == "dog":
        ellipse(cr, 0, 0, s * 0.85, s * 0.85, hexc("#d7a46f"), OUTLINE, 7)
        flop = 0.08 * math.sin(t * 4)
        for dx in (-1, 1):
            cr.save()
            cr.translate(dx * s * 0.75, -s * 0.45)
            cr.rotate(dx * (0.25 + flop))
            ellipse(cr, 0, s * 0.35, s * 0.25, s * 0.5, hexc("#8d5a33"), OUTLINE, 6)
            cr.restore()
        ellipse(cr, 0, s * 0.35, s * 0.45, s * 0.32, hexc("#f5deb3"), None)
        ellipse(cr, 0, s * 0.18, s * 0.15, s * 0.11, BLACK, None)
        ellipse(cr, s * 0.4, -s * 0.2, s * 0.22, s * 0.2, hexc("#8d5a33"), None)
        _eyes(cr, s, -0.2, 0.3, blink)
        _mouth(cr, s, 0.48, mouth, 0.13)
        if mouth > 0.3:
            ellipse(cr, 0, s * 0.62, s * 0.08, s * 0.1, hexc("#f06292"), OUTLINE, 3)
    elif kind == "sheep":
        for k in range(12):
            a = k * math.pi / 6
            ellipse(cr, math.cos(a) * s * 0.75, math.sin(a) * s * 0.7, s * 0.3, s * 0.3, WHITE, OUTLINE, 5)
        ellipse(cr, 0, 0, s * 0.8, s * 0.75, WHITE, None)
        for dx in (-1, 1):
            ellipse(cr, dx * s * 0.6, -s * 0.1, s * 0.25, s * 0.12, hexc("#5d4037"), OUTLINE, 4)
        ellipse(cr, 0, s * 0.1, s * 0.48, s * 0.55, hexc("#6d4c41"), OUTLINE, 6)
        for dx in (-0.18, 0.18):
            if blink:
                cr.set_source_rgb(1, 1, 1)
                cr.set_line_width(5)
                cr.move_to(dx * s - 8, -s * 0.02)
                cr.line_to(dx * s + 8, -s * 0.02)
                cr.stroke()
            else:
                ellipse(cr, dx * s, 0, s * 0.09, s * 0.11, WHITE, None)
                ellipse(cr, dx * s, s * 0.02, s * 0.05, s * 0.06, BLACK, None)
        if mouth > 0.08:
            ellipse(cr, 0, s * 0.38, s * 0.1, s * (0.03 + 0.1 * mouth), (0.35, 0.05, 0.1), None)
    elif kind == "lion":
        for k in range(14):
            a = k * math.pi / 7
            ellipse(cr, math.cos(a) * s * 0.85, math.sin(a) * s * 0.85, s * 0.32, s * 0.32, hexc("#e67e22"), OUTLINE, 5)
        ellipse(cr, 0, 0, s * 0.85, s * 0.85, hexc("#e67e22"), None)
        for dx in (-1, 1):
            ellipse(cr, dx * s * 0.55, -s * 0.55, s * 0.18, s * 0.18, hexc("#fbc02d"), OUTLINE, 5)
        ellipse(cr, 0, 0, s * 0.75, s * 0.75, hexc("#fbc02d"), OUTLINE, 6)
        ellipse(cr, 0, s * 0.3, s * 0.35, s * 0.25, hexc("#fff3c4"), None)
        _poly(cr, [(-s * 0.12, s * 0.12), (s * 0.12, s * 0.12), (0, s * 0.25)], hexc("#6d4c41"), 3)
        _eyes(cr, s, -0.15, 0.3, blink)
        _mouth(cr, s, 0.45, mouth, 0.14)
    elif kind == "frog":
        obj(cr, "frog", "#43a047", 0, 0, s, t, mouth, blink)


def draw_item(cr, item, x, y, s, t, mouth=0.0, blink=False):
    """item = dict(group=..., kind=..., color=hex). Wobbles gently."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(math.sin(t * 4) * 0.04)
    g, k = item["group"], item["kind"]
    c = hexc(item.get("color", "#ffffff"))
    if g == "shape":
        shape(cr, k, c, s, mouth, blink)
    elif g == "animal":
        animal(cr, k, s, t, mouth, blink)
    elif k in ("apple", "balloon", "star", "frog", "fish", "grapes"):
        obj(cr, k, item["color"], 0, 0, s, t, mouth, blink)
    else:
        thing(cr, k, c, s, t, mouth, blink)
    cr.restore()
