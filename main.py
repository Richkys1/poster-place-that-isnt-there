#!/usr/bin/env python3
"""VESPERA — a travel poster for a place that isn't there.

Draws a 1024x1024 travel poster with Pillow only: no network, no system
fonts (Cinzel + Cormorant Garamond are vendored in fonts/), fully
deterministic (fixed seeds, no timestamps, no absolute paths).

The place: VESPERA, an island where dusk never ends. Its one landmark is
the Dusk Bell — a slender white tower on a black cliff, whose bell rings
once each evening as the sun touches the sea and never quite sets.

Usage: python3 main.py [output_path]   (default: /output/entry.png)
"""
import os
import random
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = H = 1024
HORIZON = 640            # y of the sea line
SUN = (390, 556)         # sun centre
SUN_R = 76

CREAM = (255, 243, 210)
CREAM_DIM = (232, 214, 178)

# ---------------------------------------------------------------- gradients
def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

def vgrad(size, stops):
    """Vertical gradient image. stops: list of (pos 0..1, (r,g,b))."""
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                px[0, y] = lerp(c0, c1, f)
                break
        else:
            px[0, y] = stops[-1][1]
    return img.resize((w, h))

def radial_glow(diameter, inner, outer):
    """Soft radial glow: bright centre fading to transparent."""
    small = Image.new("L", (128, 128), 0)
    d = ImageDraw.Draw(small)
    for r in range(64, 0, -1):
        a = int(255 * (1.0 - r / 64.0) ** 1.6)
        d.ellipse([64 - r, 64 - r, 64 + r, 64 + r], fill=a)
    small = small.resize((diameter, diameter), Image.BICUBIC)
    glow = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    glow.putalpha(small)
    solid = Image.new("RGBA", (diameter, diameter), inner + (255,))
    out = Image.composite(solid, glow, small)
    return out

def font(path, size, weight):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f

# ------------------------------------------------------------------- sky
def draw_sky(base):
    sky = vgrad((W, HORIZON), [
        (0.00, (28, 18, 64)),
        (0.30, (62, 38, 96)),
        (0.52, (138, 74, 104)),
        (0.78, (214, 122, 82)),
        (1.00, (255, 178, 96)),
    ])
    base.paste(sky, (0, 0))

    # stars: faint, only high in the violet sky
    rng = random.Random(11)
    stars = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(stars)
    for _ in range(46):
        x = rng.randint(30, 994)
        y = rng.randint(20, 300)
        r = rng.choice([1, 1, 1, 2])
        a = rng.randint(70, 170)
        ds.ellipse([x - r, y - r, x + r, y + r], fill=(255, 240, 210, a))
    base.alpha_composite(stars)

    # sun glow, then the sun disc
    glow = radial_glow(560, (255, 196, 110), (255, 150, 80))
    base.alpha_composite(glow, (SUN[0] - 280, SUN[1] - 280))
    d = ImageDraw.Draw(base)
    d.ellipse([SUN[0] - SUN_R, SUN[1] - SUN_R,
               SUN[0] + SUN_R, SUN[1] + SUN_R], fill=(255, 233, 168, 255))
    # pale inner disc for a hot core
    d.ellipse([SUN[0] - 52, SUN[1] - 52,
               SUN[0] + 52, SUN[1] + 52], fill=(255, 247, 214, 255))

    # thin warm cloud bands, blurred for softness
    clouds = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(clouds)
    bands = [
        (120, 210, 640, 26, (255, 196, 160, 110)),
        (430, 300, 520, 22, (255, 170, 140, 95)),
        (60, 420, 700, 30, (255, 150, 120, 80)),
        (560, 470, 430, 20, (255, 180, 130, 90)),
    ]
    for x, y, w, h, col in bands:
        dc.ellipse([x, y, x + w, y + h], fill=col)
    clouds = clouds.filter(ImageFilter.GaussianBlur(14))
    base.alpha_composite(clouds)

    # birds: five small silhouettes high in the sky
    for bx, by, s in [(250, 180, 14), (300, 150, 11), (700, 120, 13),
                      (760, 165, 10), (180, 260, 9)]:
        d.arc([bx - s, by - s // 2, bx, by + s // 2], 200, 340,
              fill=(40, 26, 70, 220), width=3)
        d.arc([bx, by - s // 2, bx + s, by + s // 2], 200, 340,
              fill=(40, 26, 70, 220), width=3)

# ------------------------------------------------------------------- sea
def draw_sea(base):
    sea = vgrad((W, H - HORIZON), [
        (0.00, (150, 92, 110)),
        (0.18, (84, 58, 112)),
        (0.55, (48, 36, 88)),
        (1.00, (24, 18, 62)),
    ])
    base.paste(sea, (0, HORIZON))
    d = ImageDraw.Draw(base)

    # sun's golden path on the water: centred dashes, widening downward;
    # ends well above the tagline so no dash crosses the type
    rng = random.Random(7)
    for i in range(34):
        y = HORIZON + 8 + i * 7
        f = i / 33.0
        w = int(70 + f * 120) + rng.randint(-12, 12)
        cx = SUN[0] + rng.randint(-10, 10)
        a = int(235 * (1.0 - f * 0.75))
        d.line([cx - w // 2, y, cx + w // 2, y],
               fill=(255, 196, 110, a), width=4 if i % 3 else 5)

# ------------------------------------------------- cliff and the Dusk Bell
def draw_cliff_and_tower(base):
    d = ImageDraw.Draw(base)
    # black cliff rising from the sea on the right, jagged top edge
    cliff = [(700, 1024), (700, 560), (742, 512), (790, 528), (828, 470),
             (872, 492), (918, 452), (962, 470), (1000, 440),
             (1024, 452), (1024, 1024)]
    d.polygon(cliff, fill=(26, 18, 52, 255))
    # warm rim light along the cliff's top edge
    rim = [(700, 560), (742, 512), (790, 528), (828, 470),
           (872, 492), (918, 452), (962, 470), (1000, 440), (1024, 452)]
    d.line(rim, fill=(255, 170, 110, 200), width=3)

    # the Dusk Bell tower: slender cream tower on the cliff's highest point
    tx = 878                      # tower centre x
    tw = 30                       # half-width
    base_y = 470                  # cliff top under the tower
    # tower body with a soft warm side shade
    d.rectangle([tx - tw, 366, tx + tw, base_y], fill=(245, 227, 192, 255))
    d.rectangle([tx + 8, 366, tx + tw, base_y], fill=(226, 198, 158, 255))
    # bell chamber: dark arched opening, glowing amber from within
    d.rectangle([tx - tw, 340, tx + tw, 366], fill=(58, 34, 74, 255))
    d.pieslice([tx - 20, 322, tx + 20, 362], 180, 360, fill=(58, 34, 74, 255))
    d.pieslice([tx - 13, 332, tx + 13, 358], 180, 360, fill=(255, 196, 110, 255))
    d.rectangle([tx - 13, 346, tx + 13, 366], fill=(255, 196, 110, 255))
    # the bell itself, a small dark shape in the glow
    d.polygon([(tx - 7, 352), (tx + 7, 352), (tx + 4, 340), (tx - 4, 340)],
              fill=(70, 44, 30, 255))
    d.ellipse([tx - 3, 351, tx + 3, 357], fill=(70, 44, 30, 255))
    # cornice, dome and spire above the chamber
    d.rectangle([tx - tw - 2, 314, tx + tw + 2, 322], fill=(238, 216, 176, 255))
    d.pieslice([tx - tw - 2, 282, tx + tw + 2, 322], 180, 360,
               fill=(212, 164, 92, 255))
    d.rectangle([tx - 2, 258, tx + 2, 284], fill=(212, 164, 92, 255))
    d.ellipse([tx - 4, 250, tx + 4, 258], fill=(255, 220, 140, 255))
    # two small slit windows down the tower
    for wy in (392, 428):
        d.rectangle([tx - 4, wy, tx + 4, wy + 16], fill=(58, 34, 74, 255))
    # glow halo around the bell chamber, then redraw the bell crisp on top
    halo = radial_glow(150, (255, 190, 100), (255, 150, 80))
    base.alpha_composite(halo, (tx - 75, 340 - 75))
    d = ImageDraw.Draw(base)
    d.pieslice([tx - 13, 332, tx + 13, 358], 180, 360, fill=(255, 196, 110, 255))
    d.rectangle([tx - 13, 346, tx + 13, 366], fill=(255, 196, 110, 255))
    d.polygon([(tx - 7, 352), (tx + 7, 352), (tx + 4, 340), (tx - 4, 340)],
              fill=(70, 44, 30, 255))
    d.ellipse([tx - 3, 351, tx + 3, 357], fill=(70, 44, 30, 255))

# ------------------------------------------------------------------ boat
def draw_boat(base):
    d = ImageDraw.Draw(base)
    bx, by = 268, 742            # waterline under the boat
    # hull
    d.polygon([(bx - 34, by), (bx + 34, by), (bx + 22, by + 12),
               (bx - 22, by + 12)], fill=(30, 20, 56, 255))
    # mast and two white sails, lit warm on one edge
    d.line([bx, by - 62, bx, by], fill=(30, 20, 56, 255), width=3)
    d.polygon([(bx + 3, by - 60), (bx + 3, by - 6), (bx + 34, by - 6)],
              fill=(255, 240, 214, 255))
    d.polygon([(bx - 3, by - 52), (bx - 3, by - 6), (bx - 28, by - 6)],
              fill=(238, 214, 178, 255))
    # small reflection under the hull
    d.line([bx - 26, by + 18, bx + 26, by + 18], fill=(255, 210, 150, 90), width=3)
    d.line([bx - 16, by + 26, bx + 16, by + 26], fill=(255, 210, 150, 60), width=2)

# ------------------------------------------------------------- typography
def draw_text(base):
    d = ImageDraw.Draw(base)
    here = os.path.dirname(os.path.abspath(__file__))

    # the place name, large, centred near the top
    name_font = font(os.path.join(here, "fonts", "Cinzel.ttf"), 148, 700)
    name = "VESPERA"
    nw = name_font.getlength(name)
    nx, ny = (W - nw) / 2, 66
    # soft shadow so the letters hold against the violet sky
    d.text((nx + 3, ny + 4), name, font=name_font, fill=(24, 14, 52, 200))
    d.text((nx, ny), name, font=name_font, fill=CREAM + (255,))

    # small ornament: thin rule, diamond, thin rule under the name
    oy = 252
    d.line([W // 2 - 190, oy, W // 2 - 22, oy], fill=CREAM + (220,), width=2)
    d.line([W // 2 + 22, oy, W // 2 + 190, oy], fill=CREAM + (220,), width=2)
    cx = W // 2
    d.polygon([(cx, oy - 9), (cx + 9, oy), (cx, oy + 9), (cx - 9, oy)],
              fill=CREAM + (255,))

    # one short tagline at the bottom, letterspaced small caps
    tag_font = font(os.path.join(here, "fonts", "Cinzel.ttf"), 34, 400)
    tag = "WHERE DUSK NEVER ENDS"
    tracking = 10
    widths = [tag_font.getlength(ch) for ch in tag]
    total = sum(widths) + tracking * (len(tag) - 1)
    x = (W - total) / 2
    y = 936
    for ch, w in zip(tag, widths):
        if ch != " ":
            d.text((x + 1, y + 2), ch, font=tag_font, fill=(20, 12, 46, 180))
            d.text((x, y), ch, font=tag_font, fill=CREAM_DIM + (255,))
        x += w + tracking

# ------------------------------------------------------------------ frame
def draw_frame(base):
    d = ImageDraw.Draw(base)
    d.rectangle([26, 26, W - 27, H - 27], outline=CREAM + (210,), width=3)
    d.rectangle([38, 38, W - 39, H - 39], outline=CREAM + (120,), width=1)

# -------------------------------------------------------------------- main
def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/output/entry.png"
    img = Image.new("RGBA", (W, H), (28, 18, 64, 255))
    draw_sky(img)
    draw_sea(img)
    draw_cliff_and_tower(img)
    draw_boat(img)
    draw_text(img)
    draw_frame(img)
    img = img.convert("RGB")
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    img.save(out, format="PNG", optimize=True)
    print(f"wrote {out} ({os.path.getsize(out)} bytes)")

if __name__ == "__main__":
    main()
