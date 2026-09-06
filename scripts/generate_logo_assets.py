"""
Derives every logo/icon asset the site uses from the single official source
render at scripts/logo-source/prime-finds-logo-master.png (gold "P/F"
monogram + "PRIME.FINDS" wordmark + tagline, on a black square).

Run this only when the master source image changes. Output goes straight to
public/assets/logo/ -- re-run scripts/build.py afterwards to be safe (the
generated HTML references these by fixed filename, so nothing else changes).

    py scripts/generate_logo_assets.py
"""
import os
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts", "logo-source", "prime-finds-logo-master.png")
LOGO_DIR = os.path.join(ROOT, "public", "assets", "logo")
BRAND_BG = (10, 10, 11)  # matches --color-bg: #0a0a0b

# Luminance band the background (solid near-black) fades to transparent
# over. Kept low so real dark-gold shadow tones in the artwork survive.
ALPHA_LOW, ALPHA_HIGH = 20, 70

# Vertical bands (in source-image px) each lockup element sits in. Re-measure
# these (e.g. with a quick min/max-alpha-row scan) if the source is replaced
# with a differently laid-out render.
MARK_BAND = (270, 665)
TEXT_BAND = (720, 822)
TAGLINE_BAND = (840, 975)


def cutout_from_black(rgb_img):
    """Alpha-key a render-on-solid-black image without rescaling color
    (rescaling by coverage washes gold out toward pale yellow), then remove
    isolated compression-noise specks with a morphological open."""
    gray = rgb_img.convert("L")
    alpha = gray.point(
        lambda m: 0 if m <= ALPHA_LOW
        else (255 if m >= ALPHA_HIGH else round((m - ALPHA_LOW) / (ALPHA_HIGH - ALPHA_LOW) * 255))
    )
    alpha = alpha.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
    return Image.merge("RGBA", (*rgb_img.split(), alpha))


def bbox_in_band(cut, y0, y1, alpha_thresh=120):
    w, h = cut.size
    px = cut.load()
    min_x, max_x, min_y, max_y = w, 0, h, 0
    found = False
    for y in range(y0, min(y1, h - 1) + 1):
        for x in range(w):
            if px[x, y][3] > alpha_thresh:
                found = True
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
    if not found:
        raise RuntimeError(f"no content found in band {y0}-{y1}")
    return (min_x, min_y, max_x, max_y)


def crop_padded(cut, box, pad):
    w, h = cut.size
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w - 1, x1 + pad), min(h - 1, y1 + pad)
    return cut.crop((x0, y0, x1 + 1, y1 + 1))


def square_canvas(im, size, margin_frac=0.12, bg=None):
    canvas = Image.new("RGBA", (size, size), (bg + (255,)) if bg else (0, 0, 0, 0))
    avail = size * (1 - margin_frac * 2)
    scale = min(avail / im.width, avail / im.height)
    nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    resized = im.resize((nw, nh), Image.LANCZOS)
    canvas.alpha_composite(resized, ((size - nw) // 2, (size - nh) // 2))
    return canvas


def main():
    os.makedirs(LOGO_DIR, exist_ok=True)
    source = Image.open(SRC).convert("RGB")
    cut = cutout_from_black(source)

    mark_box = bbox_in_band(cut, *MARK_BAND)
    mark = crop_padded(cut, mark_box, 18)

    text_box = bbox_in_band(cut, *TEXT_BAND)
    x0 = min(mark_box[0], text_box[0]); x1 = max(mark_box[2], text_box[2])
    wordmark = crop_padded(cut, (x0, mark_box[1], x1, text_box[3]), 20)

    tagline_box = bbox_in_band(cut, *TAGLINE_BAND)
    fx0 = min(x0, tagline_box[0]); fx1 = max(x1, tagline_box[2])
    full_lockup = crop_padded(cut, (fx0, mark_box[1], fx1, tagline_box[3]), 24)

    mark.save(os.path.join(LOGO_DIR, "mark.png"))
    wordmark.save(os.path.join(LOGO_DIR, "wordmark.png"))
    full_lockup.save(os.path.join(LOGO_DIR, "full-lockup.png"))

    # Favicons / app icons: transparent, mark-only, square.
    favicon_imgs = {}
    for s in (512, 192, 32, 16):
        im = square_canvas(mark, s, margin_frac=0.1)
        favicon_imgs[s] = im
        im.save(os.path.join(LOGO_DIR, f"favicon-{s}.png"))
    ico_48 = square_canvas(mark, 48, margin_frac=0.1)
    favicon_imgs[16].save(
        os.path.join(LOGO_DIR, "favicon.ico"),
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[favicon_imgs[32], ico_48],
    )

    # apple-touch-icon / maskable icon need an opaque background.
    square_canvas(mark, 180, margin_frac=0.16, bg=BRAND_BG).convert("RGB").save(
        os.path.join(LOGO_DIR, "apple-touch-icon.png")
    )
    square_canvas(mark, 512, margin_frac=0.22, bg=BRAND_BG).convert("RGB").save(
        os.path.join(LOGO_DIR, "maskable-icon-512.png")
    )

    # Social/OG share image (1200x630, opaque) -- uses the mark+wordmark
    # lockup, not the full lockup, since the tagline turns to mush at this
    # output size once downscaled.
    og_w, og_h = 1200, 630
    og = Image.new("RGB", (og_w, og_h), BRAND_BG)
    scale = (og_w * 0.6) / wordmark.width
    fw, fh = round(wordmark.width * scale), round(wordmark.height * scale)
    resized = wordmark.resize((fw, fh), Image.LANCZOS)
    og.paste(resized, ((og_w - fw) // 2, (og_h - fh) // 2), resized)
    og.save(os.path.join(LOGO_DIR, "og-image.jpg"), quality=92)

    print("Wrote logo assets to", LOGO_DIR)


if __name__ == "__main__":
    main()
