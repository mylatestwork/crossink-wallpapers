#!/usr/bin/env python3
"""Validate CrossInk artwork and build deterministic release archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUSTOM_DIR = ROOT / "assets" / "x4" / "custom"
OVERLAY_DIR = ROOT / "assets" / "x4" / "page-overlays"
DIST_DIR = ROOT / "dist"
TARGET_WIDTH = 480
TARGET_HEIGHT = 800
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
CUSTOM_NAME = re.compile(r"custom-(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.bmp")
OVERLAY_NAME = re.compile(r"overlay-(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.png")


class ValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AssetInfo:
    name: str
    mode: str
    number: int
    width: int
    height: int
    format: str
    detail: str
    size: int
    sha256: str


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_dimensions(path: Path, width: int, height: int) -> None:
    if (width, height) != (TARGET_WIDTH, TARGET_HEIGHT):
        raise ValidationError(
            f"{path.relative_to(ROOT)} is {width}x{height}; expected "
            f"{TARGET_WIDTH}x{TARGET_HEIGHT}"
        )


def asset_number(path: Path, pattern: re.Pattern[str]) -> int:
    match = pattern.fullmatch(path.name)
    if not match:
        raise ValidationError(
            f"{path.relative_to(ROOT)} does not follow the numbered filename pattern"
        )
    return int(match.group(1))


def inspect_bmp(path: Path) -> AssetInfo:
    data = path.read_bytes()
    if len(data) < 54 or data[:2] != b"BM":
        raise ValidationError(f"{path.relative_to(ROOT)} is not a Windows BMP")

    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size < 40:
        raise ValidationError(f"{path.relative_to(ROOT)} has unsupported DIB header {dib_size}")

    width, raw_height = struct.unpack_from("<ii", data, 18)
    planes, bits_per_pixel = struct.unpack_from("<HH", data, 26)
    compression = struct.unpack_from("<I", data, 30)[0]
    height = abs(raw_height)

    validate_dimensions(path, width, height)
    if planes != 1:
        raise ValidationError(f"{path.relative_to(ROOT)} has {planes} BMP planes; expected 1")
    if bits_per_pixel not in {1, 4, 8, 24}:
        raise ValidationError(
            f"{path.relative_to(ROOT)} uses unsupported {bits_per_pixel}-bit custom BMP"
        )
    if compression != 0:
        raise ValidationError(
            f"{path.relative_to(ROOT)} is compressed (BMP compression={compression})"
        )

    return AssetInfo(
        name=path.name,
        mode="custom",
        number=asset_number(path, CUSTOM_NAME),
        width=width,
        height=height,
        format="BMP",
        detail=f"{bits_per_pixel}-bit uncompressed",
        size=path.stat().st_size,
        sha256=digest(path),
    )


def inspect_png(path: Path) -> AssetInfo:
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != PNG_SIGNATURE:
        raise ValidationError(f"{path.relative_to(ROOT)} is not a PNG")
    if struct.unpack_from(">I", data, 8)[0] != 13 or data[12:16] != b"IHDR":
        raise ValidationError(f"{path.relative_to(ROOT)} has an invalid PNG IHDR")

    width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack_from(
        ">IIBBBBB", data, 16
    )
    validate_dimensions(path, width, height)
    if bit_depth != 8:
        raise ValidationError(f"{path.relative_to(ROOT)} uses PNG bit depth {bit_depth}; expected 8")
    if color_type not in {3, 4, 6}:
        raise ValidationError(
            f"{path.relative_to(ROOT)} has PNG color type {color_type}; an alpha-capable PNG is required"
        )
    if compression != 0 or filtering != 0 or interlace != 0:
        raise ValidationError(
            f"{path.relative_to(ROOT)} must use standard compression/filtering and be non-interlaced"
        )

    has_transparency = color_type in {4, 6}
    offset = 8
    while offset + 12 <= len(data):
        chunk_length = struct.unpack_from(">I", data, offset)[0]
        chunk_type = data[offset + 4 : offset + 8]
        if chunk_type == b"tRNS":
            has_transparency = True
        offset += 12 + chunk_length
        if chunk_type in {b"IDAT", b"IEND"}:
            break
    if not has_transparency:
        raise ValidationError(f"{path.relative_to(ROOT)} has no PNG transparency")

    color_names = {3: "indexed + transparency", 4: "grayscale + alpha", 6: "RGBA"}
    return AssetInfo(
        name=path.name,
        mode="page-overlay",
        number=asset_number(path, OVERLAY_NAME),
        width=width,
        height=height,
        format="PNG",
        detail=f"8-bit {color_names[color_type]}, non-interlaced",
        size=path.stat().st_size,
        sha256=digest(path),
    )


def validate() -> list[AssetInfo]:
    custom_files = sorted(CUSTOM_DIR.glob("*.bmp"))
    overlay_files = sorted(OVERLAY_DIR.glob("*.png"))
    if not custom_files:
        raise ValidationError("No custom BMP files found")
    if not overlay_files:
        raise ValidationError("No page-overlay PNG files found")

    unexpected = [
        path
        for folder, suffix in ((CUSTOM_DIR, ".bmp"), (OVERLAY_DIR, ".png"))
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() != suffix
    ]
    if unexpected:
        names = ", ".join(str(path.relative_to(ROOT)) for path in unexpected)
        raise ValidationError(f"Unexpected asset types: {names}")

    custom_numbers = [asset_number(path, CUSTOM_NAME) for path in custom_files]
    overlay_numbers = [asset_number(path, OVERLAY_NAME) for path in overlay_files]
    expected_custom = list(range(1, len(custom_numbers) + 1))
    expected_overlay = list(range(1, len(overlay_numbers) + 1))
    if custom_numbers != expected_custom:
        raise ValidationError(
            "Custom filenames must be consecutive from custom-001-<name>.bmp; "
            f"found {custom_numbers}"
        )
    if overlay_numbers != expected_overlay:
        raise ValidationError(
            "Overlay filenames must be consecutive from overlay-001-<name>.png; "
            f"found {overlay_numbers}"
        )
    if len(custom_numbers) != len(overlay_numbers):
        raise ValidationError(
            "Custom and Page Overlay collections must contain the same number of files; "
            f"found {len(custom_numbers)} and {len(overlay_numbers)}"
        )
    if len(custom_numbers) % 2 or len(overlay_numbers) % 2:
        raise ValidationError(
            "Both collections must contain an even number of files; "
            f"found {len(custom_numbers)} and {len(overlay_numbers)}"
        )

    assets = [inspect_bmp(path) for path in custom_files]
    assets.extend(inspect_png(path) for path in overlay_files)
    return assets


def zip_entry(archive: zipfile.ZipFile, source: Path, destination: str) -> None:
    info = zipfile.ZipInfo(destination, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, source.read_bytes(), compresslevel=9)


def zip_text(archive: zipfile.ZipFile, destination: str, contents: str) -> None:
    info = zipfile.ZipInfo(destination, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, contents.encode("utf-8"), compresslevel=9)


def build_archive(filename: str, source_dir: Path, mode: str) -> Path:
    destination = DIST_DIR / filename
    install = (
        "CrossInk X4/X4 Pro sleep-screen pack\n\n"
        f"Mode: {mode}\n"
        "Copy the enclosed .sleep folder to the root of the SD card.\n"
        "Do not merge this pack with the other mode's pack.\n"
        "See the repository README for complete instructions.\n"
        "Creator and source attribution are included in CREDITS.txt.\n"
    )
    with zipfile.ZipFile(destination, "w") as archive:
        zip_text(archive, "INSTALL.txt", install)
        zip_entry(archive, ROOT / "CREDITS.txt", "CREDITS.txt")
        zip_entry(archive, ROOT / "LICENSE-ASSETS", "LICENSE-ASSETS.txt")
        for source in sorted(source_dir.iterdir()):
            if source.is_file():
                zip_entry(archive, source, f".sleep/{source.name}")
    return destination


def build() -> tuple[list[AssetInfo], list[Path]]:
    assets = validate()
    DIST_DIR.mkdir(exist_ok=True)
    archives = [
        build_archive("CrossInk-Custom-X4.zip", CUSTOM_DIR, "Custom"),
        build_archive("CrossInk-Page-Overlays-X4.zip", OVERLAY_DIR, "Page Overlay"),
    ]
    manifest = {
        "target": {"firmware": "CrossInk", "devices": ["X4", "X4 Pro"], "width": 480, "height": 800},
        "assets": [asdict(asset) for asset in assets],
        "archives": [
            {"name": archive.name, "size": archive.stat().st_size, "sha256": digest(archive)}
            for archive in archives
        ],
    }
    (DIST_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return assets, archives


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "build"))
    args = parser.parse_args()

    try:
        if args.command == "check":
            assets = validate()
            print(f"OK: {sum(item.mode == 'custom' for item in assets)} custom BMPs")
            print(f"OK: {sum(item.mode == 'page-overlay' for item in assets)} page-overlay PNGs")
            print(
                f"OK: {sum(item.mode == 'custom' for item in assets)} "
                "balanced numbered entries per mode"
            )
            nonpreferred = [item for item in assets if item.mode == "custom" and not item.detail.startswith("24-bit")]
            for item in nonpreferred:
                print(f"NOTE: {item.name} is valid but uses {item.detail}; 24-bit is preferred")
        else:
            assets, archives = build()
            print(f"Validated {len(assets)} assets")
            for archive in archives:
                print(f"Built {archive.relative_to(ROOT)} ({archive.stat().st_size} bytes)")
            print("Wrote dist/manifest.json")
    except (OSError, ValidationError, struct.error, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
