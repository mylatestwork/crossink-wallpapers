#!/usr/bin/env python3
"""Build the static CrossInk Wallpapers gallery for local preview and GitHub Pages."""

from __future__ import annotations

import json
import re
import struct
import shutil
import zlib
from binascii import crc32
from pathlib import Path

import release


ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "site"
SITE_OUTPUT = ROOT / "site-dist"
CATALOG_SOURCE = ROOT / "catalog" / "packs.json"
THUMBNAIL_WIDTH = 240


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def asset_url(mode: str, name: str) -> str:
    folder = "custom" if mode == "custom" else "page-overlays"
    return f"./assets/x4/{folder}/{name}"


def asset_label(asset_names: dict, mode: str, number: int) -> str:
    key = f"{number:03d}"
    try:
        return asset_names[mode][key]
    except KeyError as error:
        raise ValueError(f"Missing artwork name for {mode} {key}") from error


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def thumbnail_url(mode: str, name: str) -> str:
    if mode == "custom":
        return f"./thumbs/custom/{Path(name).stem}.png"
    return asset_url(mode, name)


def build_catalog(release_manifest: dict) -> dict:
    source = load_json(CATALOG_SOURCE)
    asset_names = source.get("assetNames", {})
    assets_by_mode: dict[str, list[dict]] = {"custom": [], "page-overlay": []}

    for asset in release_manifest["assets"]:
        mode = asset["mode"]
        item = dict(asset)
        item["url"] = asset_url(mode, asset["name"])
        item["previewUrl"] = thumbnail_url(mode, asset["name"])
        item["label"] = asset_label(asset_names, mode, asset["number"])
        if not Path(item["name"]).stem.endswith(f"-{slugify(item['label'])}"):
            raise ValueError(
                f"Artwork name does not match filename: {item['name']} / {item['label']}"
            )
        assets_by_mode[mode].append(item)

    archives = {item["name"]: item for item in release_manifest["archives"]}
    packs = []
    for pack in source["packs"]:
        built_pack = {key: value for key, value in pack.items() if key != "modes"}
        built_pack["modes"] = {}
        for mode, metadata in pack["modes"].items():
            archive = archives[metadata["archive"]]
            built_pack["modes"][mode] = {
                **metadata,
                "archiveUrl": f"./downloads/{metadata['archive']}",
                "archiveSize": archive["size"],
                "archiveSha256": archive["sha256"],
                "count": len(assets_by_mode[mode]),
                "assets": assets_by_mode[mode],
            }
        packs.append(built_pack)

    return {
        "schemaVersion": source["schemaVersion"],
        "collection": source["collection"],
        "target": release_manifest["target"],
        "packs": packs,
    }


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True)


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = crc32(kind)
    checksum = crc32(payload, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def bmp_grayscale_rows(path: Path) -> tuple[int, int, list[bytes]]:
    data = path.read_bytes()
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    width, raw_height = struct.unpack_from("<ii", data, 18)
    bits_per_pixel = struct.unpack_from("<H", data, 28)[0]
    colors_used = struct.unpack_from("<I", data, 46)[0] if dib_size >= 40 else 0
    height = abs(raw_height)
    top_down = raw_height < 0
    row_size = ((width * bits_per_pixel + 31) // 32) * 4

    palette: list[int] = []
    if bits_per_pixel <= 8:
        palette_count = colors_used or (1 << bits_per_pixel)
        palette_offset = 14 + dib_size
        for index in range(palette_count):
            blue, green, red, _ = data[palette_offset + index * 4 : palette_offset + index * 4 + 4]
            palette.append((299 * red + 587 * green + 114 * blue) // 1000)

    rows = []
    for output_y in range(height):
        source_y = output_y if top_down else height - 1 - output_y
        row = data[pixel_offset + source_y * row_size : pixel_offset + (source_y + 1) * row_size]
        pixels = bytearray(width)
        if bits_per_pixel == 24:
            for x in range(width):
                blue, green, red = row[x * 3 : x * 3 + 3]
                pixels[x] = (299 * red + 587 * green + 114 * blue) // 1000
        elif bits_per_pixel == 8:
            for x in range(width):
                pixels[x] = palette[row[x]]
        elif bits_per_pixel == 4:
            for x in range(width):
                packed = row[x // 2]
                index = packed >> 4 if x % 2 == 0 else packed & 0x0F
                pixels[x] = palette[index]
        elif bits_per_pixel == 1:
            for x in range(width):
                index = (row[x // 8] >> (7 - (x % 8))) & 1
                pixels[x] = palette[index]
        else:
            raise ValueError(f"Unsupported BMP depth for thumbnail: {bits_per_pixel}")
        rows.append(bytes(pixels))
    return width, height, rows


def build_bmp_thumbnail(source: Path, destination: Path) -> None:
    width, height, rows = bmp_grayscale_rows(source)
    scale = max(1, width // THUMBNAIL_WIDTH)
    output_width = width // scale
    output_rows = [row[::scale][:output_width] for row in rows[::scale]]
    output_height = len(output_rows)
    scanlines = b"".join(b"\x00" + row for row in output_rows)
    header = struct.pack(">IIBBBBB", output_width, output_height, 8, 0, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
        + png_chunk(b"IEND", b"")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(png)


def build_thumbnails() -> None:
    for source in sorted((ROOT / "assets" / "x4" / "custom").glob("*.bmp")):
        build_bmp_thumbnail(
            source,
            SITE_OUTPUT / "thumbs" / "custom" / f"{source.stem}.png",
        )


def validate_output(catalog: dict) -> None:
    urls = {
        "./index.html",
        "./styles.css",
        "./app.js",
        "./favicon.png",
        "./media/book-page.png",
        "./media/crossink-logo.png",
        "./media/device.png",
        "./media/social-preview.png",
    }
    for pack in catalog["packs"]:
        for mode in pack["modes"].values():
            urls.add(mode["archiveUrl"])
            for asset in mode["assets"]:
                urls.add(asset["url"])
                urls.add(asset["previewUrl"])

    missing = []
    for url in sorted(urls):
        if not url.startswith("./"):
            raise ValueError(f"Catalog URL must be relative: {url}")
        path = SITE_OUTPUT / url.removeprefix("./")
        if not path.is_file():
            missing.append(str(path.relative_to(ROOT)))
    if missing:
        raise FileNotFoundError("Missing site output: " + ", ".join(missing))


def build() -> None:
    release.build()
    release_manifest = load_json(ROOT / "dist" / "manifest.json")
    catalog = build_catalog(release_manifest)

    if SITE_OUTPUT.exists():
        shutil.rmtree(SITE_OUTPUT)
    SITE_OUTPUT.mkdir()

    copy_tree(SITE_SOURCE, SITE_OUTPUT)
    copy_tree(ROOT / "assets", SITE_OUTPUT / "assets")
    build_thumbnails()
    (SITE_OUTPUT / "downloads").mkdir()
    for archive in release_manifest["archives"]:
        shutil.copy2(ROOT / "dist" / archive["name"], SITE_OUTPUT / "downloads" / archive["name"])

    (SITE_OUTPUT / "catalog.json").write_text(
        json.dumps(catalog, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (SITE_OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    validate_output(catalog)
    count = sum(
        len(mode["assets"])
        for pack in catalog["packs"]
        for mode in pack["modes"].values()
    )
    print(f"Built {SITE_OUTPUT.relative_to(ROOT)}/ with {count} catalog entries")


if __name__ == "__main__":
    build()
