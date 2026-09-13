from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS_SIZE = (1080, 1920)


def _font_candidates() -> list[Path]:
    env_font = os.getenv("VIDEO_TEXT_FONT")
    candidates: list[Path] = []
    if env_font:
        candidates.append(Path(env_font))

    candidates.extend(
        [
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Helvetica.ttc"),
            Path("/System/Library/Fonts/Supplemental/Helvetica Bold.ttf"),
            Path("/Library/Fonts/Arial Bold.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
            Path("/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/local/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
    )
    return candidates


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in _font_candidates():
        if not font_path.is_file():
            continue
        try:
            return ImageFont.truetype(str(font_path), size=size, index=0)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _centered_text_position(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
) -> tuple[int, int, tuple[int, int, int, int]]:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (CANVAS_SIZE[0] - text_width) // 2 - bbox[0]
    return x, y, bbox


def create_short_overlay(
    output_path: Path,
    part_number: int,
    top_text: str | None = None,
    bottom_text: str = "Like and comment",
) -> Path:
    """Create a transparent 1080x1920 PNG containing top/bottom CTA text.

    The actual video remains untouched by the text renderer. FFmpeg only overlays
    this transparent image after fitting the source video into the 1080x1920
    canvas, so this works even when the installed FFmpeg build has no drawtext
    filter.
    """
    image = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    top = top_text or f"Part {part_number}"
    top_font = _load_font(72)
    bottom_font = _load_font(58)

    top_x, _, top_bbox = _centered_text_position(draw, top, top_font, 0)
    top_y = 72 - top_bbox[1]
    draw.text(
        (top_x, top_y),
        top,
        font=top_font,
        fill=(255, 255, 255, 255),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 220),
    )

    bottom_x, _, bottom_bbox = _centered_text_position(draw, bottom_text, bottom_font, 0)
    bottom_y = CANVAS_SIZE[1] - 86 - (bottom_bbox[3] - bottom_bbox[1]) - bottom_bbox[1]
    draw.text(
        (bottom_x, bottom_y),
        bottom_text,
        font=bottom_font,
        fill=(255, 255, 255, 255),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 220),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    return output_path
