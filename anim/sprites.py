"""Pre-rendered 3D sprites (from anim3d/assets.py) drawn inside the 2D engine.

If the sprite folder exists (ASSETS3D env var, default ./assets3d), characters, objects and
backgrounds are drawn from the 3D renders; otherwise the flat 2D drawings are used.
"""
import math
import os

import cairo

ROOT = os.environ.get("ASSETS3D", os.path.join(os.path.dirname(__file__), "..", "assets3d"))
COLOR_NAMES = {"#e53935": "red", "#1e88e5": "blue", "#fdd835": "yellow", "#43a047": "green",
               "#fb8c00": "orange", "#8e24aa": "purple", "#ec407a": "pink", "#8d6e63": "brown"}
FRUITS = {"apple", "banana", "orange", "strawberry", "grapes", "watermelon", "pear", "cherry"}
# ortho camera width (in model units) each sprite family was rendered with, and object-centre offset
ORTHO = {"thing_balloon": (3.8, 0.3), "thing_car": (3.8, 0.0), "shape": (3.4, 0.0), "bramble": (3.6, 0.0)}
_CACHE = {}


def available():
    return os.path.isdir(ROOT) and os.path.exists(os.path.join(ROOT, "bramble_body.png"))


def _surface(name):
    if name not in _CACHE:
        path = os.path.join(ROOT, name + ".png")
        _CACHE[name] = cairo.ImageSurface.create_from_png(path) if os.path.exists(path) else None
    return _CACHE[name]


def _hex_to_name(h):
    h = (h or "").lower()
    if h in COLOR_NAMES:
        return COLOR_NAMES[h]
    r, g, b = (int(h[i : i + 2], 16) for i in (1, 3, 5)) if len(h) == 7 else (255, 0, 0)
    best = min(COLOR_NAMES, key=lambda k: sum((int(k[i : i + 2], 16) - v) ** 2 for i, v in zip((1, 3, 5), (r, g, b))))
    return COLOR_NAMES[best]


def item_name(item, state):
    g, k = item["group"], item["kind"]
    if g == "animal":
        return f"animal_{k}_{state}"
    if g == "shape" or k in ("star", "heart"):
        return f"shape_{k}_{_hex_to_name(item.get('color'))}_{state}"
    if k in FRUITS and (k != "apple" or item.get("color", "#e53935").lower() == "#e53935"):
        return f"fruit_{k}_{state}"
    kind = "fish" if k == "fishc" else k
    return f"thing_{kind}_{_hex_to_name(item.get('color'))}_{state}"


def _family(name):
    for key in ORTHO:
        if name.startswith(key):
            return ORTHO[key]
    return (3.2, 0.0)


def draw_item(cr, item, x, y, s, mouth=0.0, blink=False):
    """Draw a 3D object sprite centred at (x, y) with radius ~s. Returns False if no sprite."""
    state = "blink" if blink else ("talk" if mouth > 0.25 else "idle")
    name = item_name(item, state)
    surf = _surface(name)
    if surf is None:
        surf = _surface(item_name(item, "idle"))
        if surf is None:
            return False
    ortho, offset = _family(name)
    res = surf.get_width()
    k = s * ortho / res  # model unit radius 1 -> s pixels
    cr.save()
    cr.translate(x, y + offset * s)
    cr.scale(k, k)
    cr.set_source_surface(surf, -res / 2, -res / 2)
    cr.get_source().set_filter(cairo.FILTER_GOOD)
    cr.paint()
    cr.restore()
    return True


def _paint(cr, surf, x, y):
    cr.set_source_surface(surf, x, y)
    cr.get_source().set_filter(cairo.FILTER_GOOD)
    cr.paint()


def bramble(cr, x, y, s, t, mouth=0.0, wave=0.0, blink=False, jump=0.0, cheer=0.0, happy=False):
    """3D Bramble from body/head/arm sprites. (x, y) = feet, s = 2D scale (1.0 ~ 560 px tall)."""
    body = _surface("bramble_body")
    res = body.get_width()
    ppu = res / 3.6  # sprite pixels per model unit
    k = (560 * s / 2.8) / ppu
    cz = 1.45  # model z at the sprite centre

    def px(mx, mz):  # model (x, z) -> sprite pixel
        return res / 2 + mx * ppu, res / 2 - (mz - cz) * ppu

    bob = math.sin(t * 2 * math.pi * 0.9) * 0.03
    squash = 1 + 0.03 * math.sin(t * 2 * math.pi * 1.8)
    cr.save()
    cr.translate(x, y - jump * 140 * s)
    # soft ground shadow
    cr.save()
    cr.scale(1, 0.22)
    cr.set_source_rgba(0, 0, 0, 0.16 * (1 - jump * 0.5))
    cr.arc(0, jump * 140 * s / 0.22, 170 * s, 0, 2 * math.pi)
    cr.fill()
    cr.restore()
    cr.scale(k, k * squash)
    ox, oy = px(0, 0)
    cr.translate(-ox, -oy)
    # arms behind/beside the body, rotated at the shoulder
    for side, rest, ang in (("armL", 0.0, cheer * (2.3 + 0.2 * math.sin(t * 16))),
                            ("armR", 0.0, -max(wave * (2.2 + 0.35 * math.sin(t * 14)), cheer * (2.3 + 0.2 * math.sin(t * 16 + 1))))):
        arm = _surface("bramble_" + side)
        sx = -1 if side == "armL" else 1
        pvx, pvy = px(sx * 0.58, 1.32)
        cr.save()
        cr.translate(pvx, pvy)
        cr.rotate(ang)
        cr.translate(-pvx, -pvy)
        _paint(cr, arm, 0, 0)
        cr.restore()
    _paint(cr, body, 0, 0)
    state = "happy" if happy else ("blink" if blink else ("talk" if mouth > 0.2 else "idle"))
    head = _surface(f"bramble_head_{state}") or _surface("bramble_head_idle")
    _paint(cr, head, 0, -bob * ppu)
    cr.restore()


def background(cr, kind, w, h):
    name = f"bg_{kind}{'_v' if h > w else ''}"
    surf = _surface(name)
    if surf is None:
        return False
    cr.save()
    cr.scale(w / surf.get_width(), h / surf.get_height())
    _paint(cr, surf, 0, 0)
    cr.restore()
    return True
