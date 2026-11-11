#!/usr/bin/env python3
"""Makes the site's images from the app's design assets (run once after the icon changes).

    python3 tools/make_images.py

Reads ../research/design/assets/icon.svg and icon-512.png and writes:
    assets/img/hero.svg            hero banner: the series' cobalt tile, a white-red sash and the compass rose
    assets/img/icon-32/180/192/512.png, favicon.ico
    assets/img/og-image.png        1200x630 social card (rendered by headless Chrome from tools/og.html)
Needs Pillow and Google Chrome.
"""
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT.parent / "research" / "design" / "assets"
IMG = ROOT / "assets" / "img"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def compass_markup():
    """The compass rose and tulip of the icon (everything after the frame's corner leaves)."""
    svg = (DESIGN / "icon.svg").read_text("utf-8")
    start = svg.index('<circle cx="512.0" cy="542.72" r="344.7"')
    end = svg.rindex("</svg>")
    return svg[start:end]


def hero_svg():
    w, h = 1920, 720
    cx, cy, s = 1380, 320, 0.6  # compass centre in the banner and its scale (icon units are 1024)
    sash_angle = -24
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice">
<defs>
<radialGradient id="tile" cx="68%" cy="45%" r="75%"><stop offset="0" stop-color="#1E3F7A"/><stop offset="1" stop-color="#132a54"/></radialGradient>
<pattern id="hatch" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="14" stroke="#F4ECDC" stroke-opacity="0.06" stroke-width="2.4"/></pattern>
</defs>
<rect width="{w}" height="{h}" fill="url(#tile)"/>
<rect width="{w}" height="{h}" fill="url(#hatch)"/>
<g transform="rotate({sash_angle} {cx} {cy})">
<rect x="-1400" y="{cy - 58}" width="5200" height="58" fill="#FFFFFF"/>
<rect x="-1400" y="{cy}" width="5200" height="58" fill="#DC143C"/>
<rect x="-1400" y="{cy + 51}" width="5200" height="7" fill="#B01030"/>
</g>
<g transform="translate({cx - 512 * s} {cy - 542.72 * s}) scale({s})">
{compass_markup()}
</g>
</svg>
'''


def icons():
    src = Image.open(DESIGN / "icon-512.png").convert("RGB")
    for size in (32, 180, 192, 512):
        out = src if size == 512 else src.resize((size, size), Image.LANCZOS)
        out.save(IMG / f"icon-{size}.png", optimize=True)
    src.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])


def og_image():
    out = IMG / "og-image.png"
    tmp = Path(tempfile.mkdtemp())
    shot = tmp / "og.png"
    prof = tmp / "profile"
    url = (ROOT / "tools" / "og.html").as_uri()
    p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                          "--no-default-browser-check", "--allow-file-access-from-files",
                          f"--user-data-dir={prof}", "--window-size=1200,630", "--force-device-scale-factor=1",
                          "--virtual-time-budget=4000", f"--screenshot={shot}", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0, last = time.time(), -1
    while time.time() - t0 < 40 and p.poll() is None:
        if shot.exists():
            size = shot.stat().st_size
            if size > 0 and size == last:
                break
            last = size
        time.sleep(0.7)
    p.kill()
    p.wait()
    im = Image.open(shot).convert("RGB")
    if im.size != (1200, 630):
        im = im.crop((0, 0, 1200, 630))
    im.save(out, optimize=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print("wrote", out.relative_to(ROOT), im.size, out.stat().st_size // 1024, "KB")


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    (IMG / "hero.svg").write_text(hero_svg(), "utf-8")
    print("wrote assets/img/hero.svg")
    icons()
    print("wrote icons and favicon.ico")
    og_image()


if __name__ == "__main__":
    main()
