"""Generate 3 logo PNGs with theme-matched backgrounds (blue, light, dark)."""

from __future__ import annotations

import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("Install Pillow: pip install pillow")

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SOURCE = ASSETS / "logo-source.png"
OUT_SIZE = 512
MARK_SIZE = 320
ICON_SIZE = int(MARK_SIZE * 26 / 40)
RADIUS = int(MARK_SIZE * 12 / 40)

THEMES = {
    "logo-blue": {
        "page_bg": (10, 13, 22),       # --bg #0a0d16
        "mark_bg_top": (18, 22, 31),   # --surface #12161f
        "accent_soft": (77, 141, 255, 36),  # rgba accent-soft ~0.14
        "border": (35, 42, 58),        # --border #232a3a
    },
    "logo-light": {
        "page_bg": (241, 242, 246),    # --bg #f1f2f6
        "mark_bg_top": (255, 255, 255),  # --surface #ffffff
        "accent_soft": (77, 141, 255, 26),  # rgba accent-soft ~0.10
        "border": (226, 228, 236),     # --border #e2e4ec
    },
    "logo-dark": {
        "page_bg": (18, 18, 19),       # --bg #121213
        "mark_bg_top": (27, 27, 29),   # --surface #1b1b1d
        "accent_soft": (77, 141, 255, 26),
        "border": (44, 44, 47),        # --border #2c2c2f
    },
}


def rounded_rect_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def make_mark_layer(theme: dict) -> Image.Image:
    """Recreate .brand__mark: gradient + border + glow on transparent layer."""
    layer = Image.new("RGBA", (MARK_SIZE, MARK_SIZE), (0, 0, 0, 0))
    mask = rounded_rect_mask(MARK_SIZE, RADIUS)

    # Base fill (surface tone)
    base = Image.new("RGBA", (MARK_SIZE, MARK_SIZE), theme["mark_bg_top"] + (255,))
    layer.paste(base, mask=mask)

    # Diagonal accent gradient (155deg approx: top-left to bottom-right)
    gradient = Image.new("RGBA", (MARK_SIZE, MARK_SIZE), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    r, g, b, a = theme["accent_soft"]
    for y in range(MARK_SIZE):
        for x in range(MARK_SIZE):
            t = (x * 0.6 + y * 0.4) / MARK_SIZE
            alpha = int(a * max(0.0, 1.0 - t * 0.85))
            if alpha > 0:
                gradient.putpixel((x, y), (r, g, b, alpha))
    layer = Image.alpha_composite(layer, Image.composite(gradient, Image.new("RGBA", gradient.size, (0, 0, 0, 0)), mask))

    # Radial glow center
    glow = Image.new("RGBA", (MARK_SIZE, MARK_SIZE), (0, 0, 0, 0))
    cx, cy = MARK_SIZE // 2, MARK_SIZE // 2
    max_dist = MARK_SIZE * 0.55
    for y in range(MARK_SIZE):
        for x in range(MARK_SIZE):
            dist = math.hypot(x - cx, y - cy)
            if dist < max_dist:
                alpha = int(theme["accent_soft"][3] * (1 - dist / max_dist) * 0.5)
                if alpha > 0:
                    glow.putpixel((x, y), (r, g, b, alpha))
    layer = Image.alpha_composite(layer, Image.composite(glow, Image.new("RGBA", glow.size, (0, 0, 0, 0)), mask))

    # Border
    border_layer = Image.new("RGBA", (MARK_SIZE, MARK_SIZE), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(border_layer)
    br, bg, bb = theme["border"]
    bdraw.rounded_rectangle(
        (0, 0, MARK_SIZE - 1, MARK_SIZE - 1),
        radius=RADIUS,
        outline=(br, bg, bb, 255),
        width=3,
    )
    layer = Image.alpha_composite(layer, border_layer)
    return layer


def compose_logo(theme_name: str, theme: dict) -> Image.Image:
    canvas = Image.new("RGBA", (OUT_SIZE, OUT_SIZE), theme["page_bg"] + (255,))
    mark = make_mark_layer(theme)

    icon = Image.open(SOURCE).convert("RGBA")
    icon = icon.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)

    mx = (OUT_SIZE - MARK_SIZE) // 2
    my = (OUT_SIZE - MARK_SIZE) // 2
    canvas.alpha_composite(mark, (mx, my))

    ix = mx + (MARK_SIZE - ICON_SIZE) // 2
    iy = my + (MARK_SIZE - ICON_SIZE) // 2
    canvas.alpha_composite(icon, (ix, iy))
    return canvas


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source logo: {SOURCE}")

    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, theme in THEMES.items():
        out = ASSETS / f"{name}.png"
        img = compose_logo(name, theme)
        img.save(out, "PNG", optimize=True)
        print(f"Saved {out}")


if __name__ == "__main__":
    main()
