from __future__ import annotations

from pathlib import Path

from PIL import Image

MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024
MAX_THUMBNAIL_SIZE = (2160, 3840)


def prepare_thumbnail(source: Path, output_dir: Path) -> tuple[str, Path]:
    """Normalize a custom thumbnail to a YouTube-friendly JPEG under 2 MB."""
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail(MAX_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        target = output_dir / "thumbnail.jpg"
        quality = 92
        while quality >= 55:
            image.save(target, format="JPEG", quality=quality, optimize=True, progressive=True)
            if target.stat().st_size <= MAX_THUMBNAIL_BYTES:
                return target.name, target
            quality -= 5

        # Last resort: reduce dimensions until the file is comfortably below the API limit.
        while image.width > 640 and image.height > 640 and target.stat().st_size > MAX_THUMBNAIL_BYTES:
            image.thumbnail((max(640, image.width * 3 // 4), max(640, image.height * 3 // 4)), Image.Resampling.LANCZOS)
            image.save(target, format="JPEG", quality=70, optimize=True, progressive=True)

        if target.stat().st_size > MAX_THUMBNAIL_BYTES:
            raise ValueError("Thumbnail could not be reduced below YouTube's 2 MB limit.")
        return target.name, target
