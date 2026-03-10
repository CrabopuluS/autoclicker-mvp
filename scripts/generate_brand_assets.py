"""Generate branding assets for AutoClicker MVP.

This script creates:
- app icon PNGs (1024/512/256)
- multi-size ICO for Windows executable
- wordmark image for README
- social preview banner
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "branding"


def _rounded_gradient_icon(size: int) -> Image.Image:
    """Builds a rounded-square gradient icon with a click spark glyph."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(size):
        t = y / max(1, size - 1)
        r = int(30 + (37 - 30) * t)
        g = int(93 + (99 - 93) * t)
        b = int(240 + (235 - 240) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255), width=1)

    radius = int(size * 0.22)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    img.putalpha(mask)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (int(size * 0.12), int(size * 0.15), int(size * 0.88), int(size * 0.86)),
        radius=int(size * 0.17),
        fill=(7, 18, 66, 70),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.03))
    img.alpha_composite(shadow)

    glyph = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glyph_draw = ImageDraw.Draw(glyph)

    cursor_points = [
        (size * 0.33, size * 0.22),
        (size * 0.33, size * 0.72),
        (size * 0.50, size * 0.58),
        (size * 0.60, size * 0.80),
        (size * 0.73, size * 0.74),
        (size * 0.61, size * 0.53),
        (size * 0.80, size * 0.51),
    ]
    glyph_draw.polygon(cursor_points, fill=(255, 255, 255, 255))

    spark = [
        (size * 0.64, size * 0.28),
        (size * 0.72, size * 0.35),
        (size * 0.66, size * 0.38),
        (size * 0.74, size * 0.46),
        (size * 0.62, size * 0.43),
        (size * 0.56, size * 0.49),
        (size * 0.58, size * 0.38),
        (size * 0.50, size * 0.35),
        (size * 0.60, size * 0.33),
    ]
    glyph_draw.polygon(spark, fill=(186, 230, 253, 245))

    img.alpha_composite(glyph)
    return img


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads a system font with a safe fallback."""
    candidates = [
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wordmark(icon: Image.Image) -> Image.Image:
    """Creates a wide wordmark image for README and release pages."""
    width, height = 1280, 360
    img = Image.new("RGBA", (width, height), (241, 246, 255, 255))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        t = y / max(1, height - 1)
        r = int(241 + (230 - 241) * t)
        g = int(246 + (240 - 246) * t)
        b = int(255 + (255 - 255) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    panel = (70, 58, width - 70, height - 58)
    draw.rounded_rectangle(panel, radius=36, fill=(255, 255, 255, 235), outline=(206, 223, 255, 255), width=3)

    icon_resized = icon.resize((180, 180), Image.Resampling.LANCZOS)
    img.alpha_composite(icon_resized, (120, 90))

    title_font = _load_font(72, bold=True)
    subtitle_font = _load_font(30)
    badge_font = _load_font(26, bold=True)

    draw.text((340, 108), "AutoClicker MVP", font=title_font, fill=(17, 24, 39, 255))
    draw.text((343, 196), "Fast. Reliable. Windows-native.", font=subtitle_font, fill=(55, 65, 81, 255))

    badge_rect = (342, 246, 800, 304)
    draw.rounded_rectangle(badge_rect, radius=16, fill=(37, 99, 235, 255))
    draw.text((366, 258), "F6 Start  •  F7 Stop  •  F8 Pause", font=badge_font, fill=(255, 255, 255, 255))
    return img


def _social_preview(icon: Image.Image) -> Image.Image:
    """Creates a social preview banner for GitHub/Open Graph."""
    width, height = 1280, 640
    img = Image.new("RGBA", (width, height), (11, 18, 32, 255))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        t = y / max(1, height - 1)
        r = int(11 + (30 - 11) * t)
        g = int(18 + (64 - 18) * t)
        b = int(32 + (175 - 32) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((760, 80, 1320, 640), fill=(59, 130, 246, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img.alpha_composite(glow)

    icon_resized = icon.resize((260, 260), Image.Resampling.LANCZOS)
    img.alpha_composite(icon_resized, (112, 188))

    title_font = _load_font(86, bold=True)
    subtitle_font = _load_font(34)

    draw.text((420, 214), "AutoClicker MVP", font=title_font, fill=(243, 244, 246, 255))
    draw.text((423, 330), "Production-like Windows auto clicker", font=subtitle_font, fill=(191, 219, 254, 255))
    draw.text((423, 384), "PySide6 • Global Hotkeys • High Speed Engine", font=subtitle_font, fill=(147, 197, 253, 255))
    return img


def main() -> None:
    """Entry point."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    icon_1024 = _rounded_gradient_icon(1024)
    icon_512 = icon_1024.resize((512, 512), Image.Resampling.LANCZOS)
    icon_256 = icon_1024.resize((256, 256), Image.Resampling.LANCZOS)

    icon_1024.save(OUT_DIR / "app_icon_1024.png")
    icon_512.save(OUT_DIR / "app_icon_512.png")
    icon_256.save(OUT_DIR / "app_icon_256.png")

    icon_1024.save(
        OUT_DIR / "app_icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    _wordmark(icon_512).save(OUT_DIR / "wordmark.png")
    _social_preview(icon_512).save(OUT_DIR / "social_preview.png")
    print("Brand assets generated.")


if __name__ == "__main__":
    main()
