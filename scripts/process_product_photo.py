"""
Turns a raw product photo (typically a white-background Amazon-style shot)
into the site's standard square product image: background cut away, the
product recomposed on the brand's dark backdrop with a soft vignette, a warm
gold glow, and a grounding contact shadow -- the same treatment for every
product so nothing needs a bespoke design.

Usage:
    py scripts/process_product_photo.py <source-image> <slug> [source-image-2 slug-alt1 ...]

Writes public/assets/images/products/<slug>.jpg (and <slug>-alt1.jpg, -alt2.jpg, ...
for any extra images given after the first pair).
"""
import math
import os
import sys
from collections import deque

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "public", "assets", "images", "products")

CANVAS = 1200
MARGIN_FRAC = 0.11
WHITE_THRESH = 246  # a pixel counts as background-candidate if every channel >= this

BG_DARK = (10, 10, 11)       # --color-bg
BG_ELEVATED = (24, 24, 27)   # --color-bg-elevated
GOLD = (201, 162, 75)        # --color-gold


def cut_white_background(im_rgb):
    """Removes near-white background -- both the outer background (flood-fill
    from the image border) and any white pocket fully enclosed by the product
    itself (e.g. the negative space inside a handle or between grips), which
    a border-only flood-fill would miss since it never touches the edge.
    A product that's itself partly white/light survives either way, since
    it's not made of pixels this bright to begin with.

    The candidate test runs against a lightly blurred copy, not the raw
    pixels: a smooth curved edge on the product (a controller's shell, say)
    sits right at the white/not-white cutoff for a band of pixels, and JPEG
    noise there flips individual pixels across the threshold at random --
    unblurred, that reads as a jagged bite taken out of the product along
    the whole curve instead of a clean edge."""
    w, h = im_rgb.size
    bpx = im_rgb.filter(ImageFilter.GaussianBlur(1.1)).load()

    def is_bg_candidate(x, y):
        r, g, b = bpx[x, y]
        return r >= WHITE_THRESH and g >= WHITE_THRESH and b >= WHITE_THRESH

    def flood(seeds):
        """Flood-fills one connected component and returns the pixels in it,
        without committing them to bg_mask yet."""
        seen = set(seeds)
        dq = deque(seeds)
        while dq:
            x, y = dq.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and is_bg_candidate(nx, ny):
                    seen.add((nx, ny))
                    dq.append((nx, ny))
        return seen

    bg_mask = bytearray(w * h)
    visited = bytearray(w * h)

    # Pass 1: the true background, reached by flood-filling from the border.
    border_seeds = [
        (x, y) for x in range(w) for y in (0, h - 1)
        if is_bg_candidate(x, y)
    ] + [
        (x, y) for y in range(h) for x in (0, w - 1)
        if is_bg_candidate(x, y)
    ]
    for x, y in flood(border_seeds):
        bg_mask[y * w + x] = 1
        visited[y * w + x] = 1

    # Pass 2: any white pocket left over must be enclosed by the product
    # (pass 1 already claimed everything reachable from the edge) -- remove
    # those too, but only sizeable ones. A product that's itself pale/white
    # (chrome, white plastic) has plenty of small near-white pixel clusters
    # from JPEG noise and specular highlights; treating every one of those as
    # a "hole" pockmarks the product with static. A real enclosed gap (finger
    # grip, handle, vent) is a lot bigger than that.
    MIN_HOLE_PX = 700
    for y in range(h):
        row = y * w
        for x in range(w):
            idx = row + x
            if not visited[idx] and is_bg_candidate(x, y):
                component = flood([(x, y)])
                for cx, cy in component:
                    visited[cy * w + cx] = 1
                if len(component) >= MIN_HOLE_PX:
                    for cx, cy in component:
                        bg_mask[cy * w + cx] = 1

    alpha = Image.new("L", (w, h), 255)
    apx = alpha.load()
    for y in range(h):
        row = y * w
        for x in range(w):
            if bg_mask[row + x]:
                apx[x, y] = 0
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))

    out = im_rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def cut_pale_background(im_rgb, thresh=208):
    """For source photos on a pale gradient/graphic background (not flat
    white) rather than a clean product-only shot -- e.g. a marketing image
    with soft color washes. A plain per-pixel threshold flicks on and off
    across such a gradient (JPEG noise sits right at the cutoff), leaving a
    speckled/static edge, so this tests a blurred copy of the image instead
    (smooths the gradient noise away) and despeckles the resulting mask.
    Pre-crop the source tightly around the product yourself first -- this
    still won't cleanly separate a background patch that's genuinely the
    same tone as part of the product; crop that patch out instead."""
    w, h = im_rgb.size
    blurred = im_rgb.filter(ImageFilter.GaussianBlur(2.2))
    bpx = blurred.load()

    def is_bg_candidate(x, y):
        r, g, b = bpx[x, y]
        return r >= thresh and g >= thresh and b >= thresh

    bg_mask = bytearray(w * h)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg_candidate(x, y) and not bg_mask[y * w + x]:
                bg_mask[y * w + x] = 1
                dq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg_candidate(x, y) and not bg_mask[y * w + x]:
                bg_mask[y * w + x] = 1
                dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if not bg_mask[idx] and is_bg_candidate(nx, ny):
                    bg_mask[idx] = 1
                    dq.append((nx, ny))

    alpha = Image.new("L", (w, h), 255)
    apx = alpha.load()
    for y in range(h):
        row = y * w
        for x in range(w):
            if bg_mask[row + x]:
                apx[x, y] = 0
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.0))

    out = im_rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def radial_backdrop(size):
    bg = Image.new("RGB", (size, size), BG_DARK)
    cx, cy = size / 2, size * 0.56
    max_r = math.hypot(size, size) * 0.62
    px = bg.load()
    for y in range(size):
        for x in range(size):
            t = min(1.0, math.hypot(x - cx, y - cy) / max_r) ** 2
            px[x, y] = tuple(round(BG_ELEVATED[i] + (BG_DARK[i] - BG_ELEVATED[i]) * t) for i in range(3))

    glow = Image.new("L", (size, size), 0)
    gd = ImageDraw.Draw(glow)
    gw, gh = size * 0.55, size * 0.30
    gd.ellipse((cx - gw / 2, cy - gh / 2, cx + gw / 2, cy + gh / 2), fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.09))
    return Image.composite(Image.new("RGB", (size, size), GOLD), bg, glow), (cx, cy)


def compose(cutout, size=CANVAS, margin_frac=MARGIN_FRAC):
    bbox = cutout.getbbox()
    content = cutout.crop(bbox) if bbox else cutout
    cw, ch = content.size

    bg, (cx, cy) = radial_backdrop(size)

    avail = size * (1 - margin_frac * 2)
    scale = min(avail / cw, avail / ch)
    nw, nh = round(cw * scale), round(ch * scale)
    content_resized = content.resize((nw, nh), Image.LANCZOS)

    shadow = Image.new("L", (size, size), 0)
    sd = ImageDraw.Draw(shadow)
    sx = size / 2
    sy = (size - nh) / 2 + nh * 0.94
    sw, sh = nw * 0.62, nh * 0.10
    sd.ellipse((sx - sw / 2, sy - sh / 2, sx + sw / 2, sy + sh / 2), fill=130)
    shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.02))
    bg = Image.composite(Image.new("RGB", (size, size), (0, 0, 0)), bg, shadow)

    out = bg.convert("RGBA")
    out.alpha_composite(content_resized, ((size - nw) // 2, (size - nh) // 2))
    return out.convert("RGB")


def process_one(src_path, out_slug, pale=False):
    im = Image.open(src_path).convert("RGB")
    cutout = cut_pale_background(im) if pale else cut_white_background(im)
    final = compose(cutout)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"{out_slug}.jpg")
    final.save(out_path, quality=93)
    print(f"wrote {out_path} ({final.size[0]}x{final.size[1]})")
    return f"/assets/images/products/{out_slug}.jpg"


def main():
    args = sys.argv[1:]
    pale = "--pale" in args
    if pale:
        args = [a for a in args if a != "--pale"]
    if len(args) < 2 or len(args) % 2 != 0:
        print(__doc__)
        print("\nAdd --pale (anywhere in the args) for a source photo on a pale gradient/graphic")
        print("background rather than flat white. Pre-crop tightly around the product yourself")
        print("first, cropping out any patch that's the same tone as part of the product itself.")
        sys.exit(1)
    for i in range(0, len(args), 2):
        process_one(args[i], args[i + 1], pale=pale)


if __name__ == "__main__":
    main()
