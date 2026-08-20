"""Image pixel + byte guard. Derive-or-deny. Never auto-crop the top of a tall image."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
STEP_DOWN_DEFAULT = (1200, 1024, 900, 768)
DEFAULT_MAX_SOURCE_PIXELS = 40_000_000


@dataclass
class ImageDecision:
    action: str  # pass | derive_deny | deny
    reason: str
    source: str
    derived: str | None = None
    width: int = 0
    height: int = 0
    bytes: int = 0
    long_edge: int = 0
    tall: bool = False


def pillow_available() -> bool:
    try:
        from PIL import Image  # noqa: F401

        return True
    except Exception:
        return False


def looks_like_image_path(path: str | None) -> bool:
    if not path or not isinstance(path, str):
        return False
    suffix = Path(path).suffix.lower()
    return suffix in IMAGE_SUFFIXES


def extract_image_paths(tool_name: str, tool_input: Any) -> list[str]:
    """Conservative: only paths the model is about to Read / attach as pixels."""
    if not isinstance(tool_input, dict):
        return []
    paths: list[str] = []
    name = (tool_name or "").split("__")[-1]
    if name in {"Read", "read"}:
        candidate = tool_input.get("file_path") or tool_input.get("path")
        if looks_like_image_path(candidate) and Path(str(candidate)).is_file():
            paths.append(str(candidate))
    for key in ("file_path", "path", "image_path", "screenshot"):
        candidate = tool_input.get(key)
        if looks_like_image_path(candidate) and Path(str(candidate)).is_file():
            paths.append(str(candidate))
    seen: set[str] = set()
    out: list[str] = []
    for item in paths:
        resolved = str(Path(item))
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(resolved)
    return out


def source_identity(path: Path) -> str:
    """Stable 12-char digest so two files sharing a basename do not collide."""
    digest = hashlib.sha256()
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path)
    digest.update(resolved.encode("utf-8", errors="replace"))
    try:
        stat = path.stat()
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    except OSError:
        pass
    try:
        with path.open("rb") as handle:
            digest.update(b"\0")
            digest.update(handle.read(8192))
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            if size > 8192:
                handle.seek(max(0, size - 8192))
                digest.update(handle.read(8192))
    except OSError:
        pass
    return digest.hexdigest()[:12]


def _probe(path: Path) -> tuple[int, int, int]:
    size = path.stat().st_size
    if not pillow_available():
        return 0, 0, size
    from PIL import Image

    with Image.open(path) as img:
        width, height = img.size
    return int(width), int(height), int(size)


def _is_tall(width: int, height: int) -> bool:
    if width <= 0 or height <= 0:
        return False
    return height > width * 2 and height > 1600


def _save_under_caps(
    img,
    dest: Path,
    *,
    max_bytes: int,
    qualities: list[int],
) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for quality in qualities:
        tmp = dest.with_suffix(".jpg")
        img.convert("RGB").save(tmp, format="JPEG", quality=int(quality), optimize=True)
        if tmp.stat().st_size <= max_bytes:
            if dest.suffix.lower() != ".jpg":
                final = dest.with_suffix(".jpg")
                os.replace(tmp, final)
            else:
                os.replace(tmp, dest)
                final = dest
            os.chmod(final, 0o600)
            return True
        tmp.unlink(missing_ok=True)
    return False


def derive_image(
    source: str,
    dest_dir: Path,
    *,
    max_long_edge: int = 1200,
    max_bytes: int = 393216,
    step_down: list[int] | tuple[int, ...] | None = None,
    qualities: list[int] | None = None,
    max_source_pixels: int = DEFAULT_MAX_SOURCE_PIXELS,
) -> ImageDecision:
    path = Path(source)
    if not path.is_file():
        return ImageDecision("deny", "IMAGE_MISSING", source)
    try:
        width, height, size = _probe(path)
    except Exception:
        return ImageDecision("deny", "IMAGE_UNREADABLE", source)

    long_edge = max(width, height)
    tall = _is_tall(width, height)

    # Unknown dimensions are never safe — width==0 must not pass the pixel cap.
    if width <= 0 or height <= 0:
        reason = "DEGRADED_NO_IMAGE_RESIZER" if not pillow_available() else "IMAGE_UNKNOWN_DIMENSIONS"
        if not pillow_available() and size > max_bytes:
            reason = "DEGRADED_NO_IMAGE_RESIZER"
        elif not pillow_available():
            reason = "IMAGE_UNKNOWN_DIMENSIONS"
        return ImageDecision(
            "deny",
            reason,
            source,
            width=width,
            height=height,
            bytes=size,
            long_edge=long_edge,
            tall=tall,
        )

    source_pixels = int(width) * int(height)
    if source_pixels > int(max_source_pixels):
        return ImageDecision(
            "deny",
            "IMAGE_SOURCE_PIXEL_CAP",
            source,
            width=width,
            height=height,
            bytes=size,
            long_edge=long_edge,
            tall=tall,
        )

    under_px = long_edge <= max_long_edge
    under_bytes = size <= max_bytes
    if under_px and under_bytes:
        return ImageDecision(
            "pass",
            "IMAGE_SAFE",
            source,
            width=width,
            height=height,
            bytes=size,
            long_edge=long_edge,
            tall=tall,
        )

    if not pillow_available():
        return ImageDecision(
            "deny",
            "DEGRADED_NO_IMAGE_RESIZER",
            source,
            width=width,
            height=height,
            bytes=size,
            long_edge=long_edge,
            tall=tall,
        )

    from PIL import Image

    steps = list(step_down or STEP_DOWN_DEFAULT)
    if max_long_edge not in steps:
        steps = [max_long_edge] + steps
    qualities = qualities or [85, 75, 65, 55]
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(dest_dir, 0o700)
    stem = path.stem[:40]
    dest = dest_dir / f"{stem}-{source_identity(path)}-guard.jpg"

    try:
        with Image.open(path) as original:
            # Source-pixel cap already enforced; convert only after that check.
            rgb = original.convert("RGB")
            for edge in steps:
                if edge <= 0:
                    continue
                work = rgb.copy()
                work.thumbnail((edge, edge))  # preserve aspect; never crop
                if _save_under_caps(work, dest, max_bytes=max_bytes, qualities=qualities):
                    final = dest if dest.is_file() else dest.with_suffix(".jpg")
                    if not final.is_file():
                        continue
                    fw, fh, fs = _probe(final)
                    if fw > 0 and fh > 0 and fw <= max_long_edge and fh <= max_long_edge and fs <= max_bytes:
                        return ImageDecision(
                            "derive_deny",
                            "IMAGE_DERIVED_RETRY",
                            source,
                            derived=str(final),
                            width=fw,
                            height=fh,
                            bytes=fs,
                            long_edge=max(fw, fh),
                            tall=tall,
                        )
    except Exception:
        return ImageDecision(
            "deny",
            "IMAGE_TRANSFORM_FAILED",
            source,
            width=width,
            height=height,
            bytes=size,
            long_edge=long_edge,
            tall=tall,
        )

    return ImageDecision(
        "deny",
        "IMAGE_CAPS_EXCEEDED",
        source,
        width=width,
        height=height,
        bytes=size,
        long_edge=long_edge,
        tall=tall,
    )


def deny_message(decision: ImageDecision) -> str:
    if decision.action == "derive_deny" and decision.derived:
        extra = ""
        if decision.tall:
            extra = (
                " This is a tall screenshot. Do not crop the top automatically. "
                "Read the derived overview first, then a targeted crop in a later batch."
            )
        return (
            "Context Guard denied the raw image. Retry Read on the derived file only: "
            f"{decision.derived} ({decision.width}x{decision.height}, {decision.bytes} bytes)."
            f"{extra} One image per agentic tool batch. Prefer DOM/a11y/console before more pixels."
        )
    if decision.reason == "DEGRADED_NO_IMAGE_RESIZER":
        return (
            "Context Guard denied the oversized image (Pillow not installed; no resizer). "
            "Do not Read the raw file. Prefer DOM/a11y/console, or a smaller image already under "
            "1200px long edge and 384KiB. One image per agentic tool batch."
        )
    if decision.reason == "IMAGE_UNKNOWN_DIMENSIONS":
        return (
            "Context Guard denied the image (unknown dimensions; fail closed). "
            "Do not Read the raw file. Prefer DOM/a11y/console before pixels. "
            "One image per agentic tool batch."
        )
    if decision.reason == "IMAGE_SOURCE_PIXEL_CAP":
        return (
            "Context Guard denied the image (source pixel cap). "
            "Do not Read the raw file. Prefer DOM/a11y/console or a smaller source. "
            "One image per agentic tool batch."
        )
    if decision.reason == "IMAGE_SECOND_IN_BATCH":
        return (
            "Context Guard denied a second image in this agentic tool batch. "
            "Finish this batch, then Read one more image in the next batch. "
            "Sequential A → analyze → B in one user turn is allowed."
        )
    return (
        f"Context Guard denied the image ({decision.reason}). "
        "Do not Read the raw oversized file. Prefer DOM/a11y/console before pixels."
    )
