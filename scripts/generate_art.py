"""
Deterministic placeholder-art generator for PRIME.FINDS demo data.

Generates abstract, on-brand (black / graphite / metallic-gold) SVG tiles for
every demo product, category, and the homepage hero — so the site has
consistent, premium-looking visuals without using stock photography or real
product photos. Purely for development/demo purposes.

Real product photography (or real category imagery) can simply overwrite the
files this script writes under public/assets/images/ — the HTML/CSS reference
those paths directly and don't care how the file was produced.

Run via: python scripts/generate_art.py
"""
import hashlib
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
IMAGES_DIR = os.path.join(ROOT, "public", "assets", "images")

GOLD = "#c9a24b"
GOLD_LIGHT = "#e8cf8a"
GOLD_DIM = "#8a6f34"
INK = "#0a0a0b"
GRAPHITE = "#17181a"
GRAPHITE_2 = "#222325"
LINE = "#3a3a3d"


def seeded_rand(seed_str, index):
    h = hashlib.sha256(f"{seed_str}:{index}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


CATEGORY_ICON_PATHS = {
    "tech": "M -18 -14 h 36 v 22 h -36 z M -8 12 h 16",
    "home": "M -20 0 L 0 -18 L 20 0 M -14 0 V 16 H 14 V 0",
    "gaming": "M -20 4 a 8 8 0 0 1 8 -8 h 24 a 8 8 0 0 1 8 8 l 2 10 a 6 6 0 0 1 -10 5 l -6 -7 h -10 l -6 7 a 6 6 0 0 1 -10 -5 z",
    "travel": "M -14 -6 h 28 v 20 a 4 4 0 0 1 -4 4 h -20 a 4 4 0 0 1 -4 -4 z M -6 -6 v -6 a 4 4 0 0 1 4 -4 h 4 a 4 4 0 0 1 4 4 v 6",
    "desk": "M -20 -10 h 40 v 6 h -40 z M -14 -4 v 18 M 14 -4 v 18",
    "gift": "M -18 -4 h 36 v 22 h -36 z M -18 -4 v -6 h 36 v 6 M 0 -10 v 26 M 0 -10 c -4 -10 -16 -8 -14 0 c 2 6 10 4 14 0 c 4 -10 16 -8 14 0 c -2 6 -10 4 -14 0",
    "value": "M 0 -20 a 20 20 0 1 0 0.1 0 z M -6 -6 h 12 v 4 h -12 z M -6 2 h 12 v 4 h -12 z",
}


def svg_header(w, h):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-hidden="true">'


def base_defs(uid):
    return f"""
  <defs>
    <linearGradient id="bg-{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{GRAPHITE}"/>
      <stop offset="100%" stop-color="{INK}"/>
    </linearGradient>
    <linearGradient id="gold-{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{GOLD_LIGHT}"/>
      <stop offset="55%" stop-color="{GOLD}"/>
      <stop offset="100%" stop-color="{GOLD_DIM}"/>
    </linearGradient>
    <radialGradient id="glow-{uid}" cx="50%" cy="35%" r="70%">
      <stop offset="0%" stop-color="{GOLD}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
    </radialGradient>
  </defs>
"""


def product_tile(seed, width=800, height=800):
    uid = hashlib.sha1(seed.encode()).hexdigest()[:8]
    cx, cy = width / 2, height / 2
    r1 = seeded_rand(seed, 1)
    r2 = seeded_rand(seed, 2)
    r3 = seeded_rand(seed, 3)
    r4 = seeded_rand(seed, 4)

    angle = r1 * 360
    ring_r = 140 + r2 * 90
    dot_x = cx + math.cos(angle * math.pi / 180) * (width * 0.30)
    dot_y = cy + math.sin(angle * math.pi / 180) * (height * 0.22)
    line_rot = r3 * 360
    accent_shape = "circle" if r4 < 0.34 else ("ring" if r4 < 0.67 else "arc")

    shapes = []
    shapes.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#bg-{uid})"/>')
    shapes.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#glow-{uid})"/>')

    for i in range(3):
        gy = height * (0.2 + i * 0.28)
        shapes.append(
            f'<line x1="0" y1="{gy:.1f}" x2="{width}" y2="{gy:.1f}" stroke="{LINE}" stroke-width="1" opacity="0.35"/>'
        )

    if accent_shape == "circle":
        shapes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring_r:.1f}" fill="none" stroke="url(#gold-{uid})" stroke-width="2.5" opacity="0.9"/>')
        shapes.append(f'<circle cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="10" fill="url(#gold-{uid})"/>')
    elif accent_shape == "ring":
        shapes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring_r:.1f}" fill="none" stroke="url(#gold-{uid})" stroke-width="1.5" opacity="0.6"/>')
        shapes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring_r * 0.62:.1f}" fill="none" stroke="{GOLD_DIM}" stroke-width="1" opacity="0.5"/>')
        shapes.append(f'<circle cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="8" fill="url(#gold-{uid})"/>')
    else:
        shapes.append(
            f'<path d="M {cx - ring_r} {cy} A {ring_r} {ring_r} 0 0 1 {cx + ring_r} {cy}" '
            f'fill="none" stroke="url(#gold-{uid})" stroke-width="2.5" opacity="0.85" '
            f'transform="rotate({line_rot:.1f} {cx} {cy})"/>'
        )
        shapes.append(f'<circle cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="9" fill="url(#gold-{uid})"/>')

    shapes.append(
        f'<rect x="{width * 0.08:.1f}" y="{height * 0.08:.1f}" width="{width * 0.84:.1f}" height="{height * 0.84:.1f}" '
        f'fill="none" stroke="{LINE}" stroke-width="1" opacity="0.5"/>'
    )
    shapes.append(
        f'<text x="{width * 0.10:.1f}" y="{height * 0.92:.1f}" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="{width * 0.028:.1f}" letter-spacing="3" fill="{GOLD_DIM}">PRIME.FINDS</text>'
    )

    svg = svg_header(width, height) + base_defs(uid) + "".join(shapes) + "</svg>"
    return svg


def category_tile(slug, width=1200, height=900):
    uid = hashlib.sha1(("cat-" + slug).encode()).hexdigest()[:8]
    cx, cy = width * 0.72, height * 0.5
    path = CATEGORY_ICON_PATHS.get(slug, CATEGORY_ICON_PATHS["value"])
    scale = width * 0.12

    shapes = []
    shapes.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#bg-{uid})"/>')
    shapes.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#glow-{uid})"/>')
    shapes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{width * 0.22:.1f}" fill="none" stroke="{LINE}" stroke-width="1" opacity="0.6"/>')
    shapes.append(
        f'<g transform="translate({cx:.1f} {cy:.1f}) scale({scale/20:.3f})" '
        f'stroke="url(#gold-{uid})" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{path}"/></g>'
    )
    for i in range(4):
        y = height * (0.15 + i * 0.22)
        shapes.append(f'<line x1="0" y1="{y:.1f}" x2="{width * 0.34:.1f}" y2="{y:.1f}" stroke="{LINE}" stroke-width="1" opacity="0.4"/>')

    svg = svg_header(width, height) + base_defs(uid) + "".join(shapes) + "</svg>"
    return svg


def hero_art(width=1920, height=1080):
    uid = "hero"
    shapes = []
    shapes.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#bg-{uid})"/>')
    shapes.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#glow-{uid})"/>')
    cx, cy = width * 0.5, height * 0.46
    for i, r in enumerate([0.16, 0.24, 0.33, 0.44]):
        shapes.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{width * r:.1f}" fill="none" '
            f'stroke="{"url(#gold-" + uid + ")" if i == 0 else LINE}" stroke-width="{2.2 if i == 0 else 1}" opacity="{0.85 if i == 0 else 0.28}"/>'
        )
    import random
    rnd = random.Random(42)
    for _ in range(28):
        x = rnd.uniform(0, width)
        y = rnd.uniform(0, height)
        r = rnd.uniform(1, 2.6)
        o = rnd.uniform(0.15, 0.6)
        shapes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{GOLD}" opacity="{o:.2f}"/>')
    svg = svg_header(width, height) + base_defs(uid) + "".join(shapes) + "</svg>"
    return svg


def main():
    os.makedirs(os.path.join(IMAGES_DIR, "products"), exist_ok=True)
    os.makedirs(os.path.join(IMAGES_DIR, "categories"), exist_ok=True)
    os.makedirs(os.path.join(IMAGES_DIR, "hero"), exist_ok=True)

    with open(os.path.join(DATA_DIR, "products.json"), encoding="utf-8") as f:
        products = json.load(f)
    with open(os.path.join(DATA_DIR, "categories.json"), encoding="utf-8") as f:
        categories = json.load(f)

    count = 0
    for p in products:
        for path in [p["image"]] + p.get("additionalImages", []):
            filename = os.path.basename(path)
            seed = filename
            out_path = os.path.join(ROOT, "public", path.lstrip("/"))
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(product_tile(seed))
            count += 1

    for c in categories:
        out_path = os.path.join(IMAGES_DIR, "categories", f"{c['slug']}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(category_tile(c["slug"]))
        count += 1

    with open(os.path.join(IMAGES_DIR, "hero", "hero.svg"), "w", encoding="utf-8") as f:
        f.write(hero_art())
    count += 1

    print(f"Generated {count} placeholder art files.")


if __name__ == "__main__":
    main()
