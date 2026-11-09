"""
Builds every logo and icon for "שודדים את אמזון": a coral bandit mask plus the
Hebrew name set in Frank Ruhl Libre (the site's display font).

The artwork is drawn as HTML/SVG and rendered by headless Chrome, because
Chrome shapes Hebrew correctly and loads the web font. Pillow then trims and
resizes the results. Needs Chrome, Pillow and an internet connection.

    py scripts/generate_logo_assets.py

Output goes to public/assets/logo/. The site references these fixed filenames.
"""
import os
import subprocess
import tempfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR = os.path.join(ROOT, "public", "assets", "logo")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

NAVY = "#14213d"
CREAM = "#fbf5e6"
CORAL = "#ff6f61"
NAVY_RGB = (20, 33, 61)

MASK_PATH = (
    "M150 30C175 20 215 16 250 24C258 26 262 34 260 42C254 78 232 104 196 104"
    "C174 104 160 92 150 78C140 92 126 104 104 104C68 104 46 78 40 42"
    "C38 34 42 26 50 24C85 16 125 20 150 30Z"
    "M168 62L228 46C226 70 208 84 190 82C178 81 170 73 168 62Z"
    "M132 62L72 46C74 70 92 84 110 82C122 81 130 73 132 62Z"
)
KNOT_PATH = (
    "M42 30C28 16 14 10 2 14C10 24 12 32 10 42C20 38 32 38 42 44Z"
    "M42 40C30 48 22 64 6 74C20 78 36 72 44 52Z"
)


def mask_svg(color=CORAL, pupil=CREAM, style=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 264 110" style="{style}">'
        f'<path fill="{color}" d="{KNOT_PATH}"/>'
        f'<path fill="{color}" fill-rule="evenodd" d="{MASK_PATH}"/>'
        f'<circle fill="{pupil}" cx="199" cy="65" r="8"/><circle fill="{pupil}" cx="115" cy="65" r="8"/></svg>'
    )


def name_html(first=CREAM, second=CORAL):
    return f'<span style="color:{first}">שודדים את</span> <span style="color:{second}">אמזון</span>'


def page(body, bg="transparent"):
    return f"""<!doctype html><html dir="rtl" lang="he"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@900&display=block" rel="stylesheet">
<style>html,body{{margin:0;width:100%;height:100%;background:{bg};overflow:hidden}}
body{{display:flex;align-items:center;justify-content:center;font-family:'Frank Ruhl Libre',serif;font-weight:900}}
</style></head><body>{body}</body></html>"""


def horizontal(first, second, pupil=CREAM):
    return page(
        f'<div style="display:flex;align-items:center;gap:44px;white-space:nowrap;line-height:1">'
        f'{mask_svg(pupil=pupil, style="width:340px;display:block")}'
        f'<div style="font-size:200px">{name_html(first, second)}</div></div>'
    )


def stacked(size_mask, size_text, gap, bg=NAVY):
    return page(
        f'<div style="display:flex;flex-direction:column;align-items:center;gap:{gap}px;line-height:1.05;text-align:center">'
        f'{mask_svg(style=f"width:{size_mask}px;display:block")}'
        f'<div style="font-size:{size_text}px;white-space:nowrap">{name_html()}</div></div>',
        bg,
    )


def render(html, w, h, tmp, name):
    src = os.path.join(tmp, name + ".html")
    out = os.path.join(tmp, name + ".png")
    with open(src, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--user-data-dir={os.path.join(tmp, 'profile')}",
         "--default-background-color=00000000", "--virtual-time-budget=8000",
         f"--window-size={w},{h}", f"--screenshot={out}", "file:///" + src.replace("\\", "/")],
        check=True, capture_output=True, timeout=120,
    )
    return Image.open(out).convert("RGBA")


def trim(im, pad=8):
    x0, y0, x1, y1 = im.getchannel("A").getbbox()
    return im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))


def main():
    os.makedirs(LOGO_DIR, exist_ok=True)
    save = lambda im, name, **kw: im.save(os.path.join(LOGO_DIR, name), **kw)
    with open(os.path.join(LOGO_DIR, "mark.svg"), "w", encoding="utf-8") as f:
        f.write(mask_svg())

    with tempfile.TemporaryDirectory() as tmp:
        on_dark = trim(render(horizontal(CREAM, CORAL), 2200, 500, tmp, "dark"))
        on_light = trim(render(horizontal(NAVY, "#b93a2a", NAVY), 2200, 500, tmp, "light"))
        compact = trim(render(stacked(520, 150, 14, "transparent"), 1300, 700, tmp, "compact"))
        mark = trim(render(page(mask_svg(style="width:960px;display:block")), 1024, 620, tmp, "mark"))
        tile = render(page(mask_svg(style="width:930px;display:block"), NAVY), 1024, 1024, tmp, "tile")
        safe = render(page(mask_svg(style="width:680px;display:block"), NAVY), 1024, 1024, tmp, "safe")
        profile = render(stacked(620, 132, 40), 1080, 1080, tmp, "profile")
        og = render(stacked(380, 112, 34), 1200, 630, tmp, "og")

    save(on_dark, "wordmark.png")
    save(compact, "wordmark-compact.png")
    save(on_light, "wordmark-on-light.png")
    save(mark, "mark.png")
    save(profile.convert("RGB"), "profile-1080.png")
    save(og.convert("RGB"), "og-image.jpg", quality=92)

    # Rounded navy tile, so the icon stands out on light and dark browser tabs.
    corners = Image.new("L", (4096, 4096), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(corners).rounded_rectangle((0, 0, 4095, 4095), 880, fill=255)
    rounded = tile.copy()
    rounded.putalpha(corners.resize(tile.size, Image.LANCZOS))

    sizes = {s: rounded.resize((s, s), Image.LANCZOS) for s in (512, 192, 48, 32, 16)}
    for s in (512, 192, 32, 16):
        save(sizes[s], f"favicon-{s}.png")
    sizes[48].save(os.path.join(LOGO_DIR, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    save(tile.convert("RGB").resize((180, 180), Image.LANCZOS), "apple-touch-icon.png")
    save(safe.convert("RGB").resize((512, 512), Image.LANCZOS), "maskable-icon-512.png")
    print("wordmark", on_dark.size, "compact", compact.size, "mark", mark.size)


if __name__ == "__main__":
    main()
