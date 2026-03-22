#!/usr/bin/env python3
"""Convert a PNG image to Launchpad Mini MK3 pixel art format (.txt).

Usage: python3 png2launchpad.py input.png [output.txt]

The script:
- Validates the image is square and max 400x400
- Downscales to 8x8 using weighted majority-vote quantization
- Each source pixel is mapped to its nearest palette colour first,
  then for each output cell the most represented palette index wins
"""

import sys
import struct
import zlib
import math
import os

# Full Launchpad Mini MK3 palette (128 entries, indices 0-127)
PALETTE_HEX = [
    "#000000", "#505050", "#a0a0a0", "#f0f0f0",
    "#ff9185", "#ff230a", "#e61f09", "#cc1c08",
    "#ffc285", "#ff850a", "#e67709", "#cc6a08",
    "#fff385", "#ffe70a", "#e6cf09", "#ccb808",
    "#daff85", "#b6ff0a", "#a3e609", "#91cc08",
    "#a9ff85", "#54ff0a", "#4be609", "#43cc08",
    "#85ff91", "#0aff23", "#09e61f", "#08cc1c",
    "#85ffc2", "#0aff85", "#09e677", "#08cc6a",
    "#85fff3", "#0affe7", "#09e6cf", "#08ccb8",
    "#85daff", "#0ab6ff", "#09a3e6", "#0891cc",
    "#85a9ff", "#0a54ff", "#094be6", "#0843cc",
    "#9185ff", "#230aff", "#1f09e6", "#1c08cc",
    "#c285ff", "#850aff", "#7709e6", "#6a08cc",
    "#f385ff", "#e70aff", "#cf09e6", "#b808cc",
    "#ff85da", "#ff0ab6", "#e609a3", "#cc0891",
    "#f04115", "#bf6100", "#b18c00", "#859708",
    "#50a027", "#009d8e", "#0079c0", "#0000ff",
    "#2d50a4", "#6247b0", "#7b7b7b", "#3c3c3c",
    "#ff0000", "#bfbb64", "#a6c000", "#78c823",
    "#34c500", "#00c0af", "#00a2f1", "#527de7",
    "#8868e7", "#a447af", "#b93b69", "#975731",
    "#f86c00", "#befd00", "#82ff5d", "#00ff00",
    "#00ffa5", "#52ffe8", "#00e9ff", "#89c4ff",
    "#91a5ff", "#b989ff", "#da67e7", "#ff2cd6",
    "#ffa601", "#fff200", "#e3f600", "#dcc500",
    "#bf9e5f", "#88b57b", "#86c2ba", "#9ab3c5",
    "#84a5c3", "#c78b7a", "#f43c7f", "#ff93a5",
    "#ffa36f", "#ffef9a", "#d2e594", "#bad16f",
    "#a9a9a9", "#d3fee0", "#ccf1f9", "#b9c0e4",
    "#cdbae5", "#d0d0d0", "#dfe6e5", "#ffffff",
    "#f2210a", "#bf1a08", "#acf20a", "#88bf08",
    "#f2db0a", "#bfad08", "#f7a409", "#e06b41",
]


def hex_to_rgb(h):
    """Convert hex color string to (r, g, b) tuple."""
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


PALETTE_RGB = [hex_to_rgb(h) for h in PALETTE_HEX]


def color_distance_sq(c1, c2):
    """Weighted squared Euclidean distance in RGB (perceptual weights)."""
    dr = c1[0] - c2[0]
    dg = c1[1] - c2[1]
    db = c1[2] - c2[2]
    # Weights approximate human perception sensitivity
    return 2 * dr * dr + 4 * dg * dg + 3 * db * db


def nearest_palette_index(r, g, b):
    """Find the closest palette color index for given RGB."""
    best_idx = 0
    best_dist = float("inf")
    pixel = (r, g, b)
    for i, pc in enumerate(PALETTE_RGB):
        d = color_distance_sq(pixel, pc)
        if d < best_dist:
            best_dist = d
            best_idx = i
    return best_idx


# ── Minimal PNG reader (no external dependencies) ──


def _read_png(filepath):
    """Read a PNG file and return (width, height, rows) where rows is list of
    lists of (r, g, b, a) tuples. Supports 8-bit RGB and RGBA, non-interlaced."""
    with open(filepath, "rb") as f:
        sig = f.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Not a valid PNG file")

        chunks = {}
        idat_data = b""
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            length = struct.unpack(">I", hdr[:4])[0]
            ctype = hdr[4:8]
            data = f.read(length)
            _crc = f.read(4)
            if ctype == b"IHDR":
                chunks["IHDR"] = data
            elif ctype == b"PLTE":
                chunks["PLTE"] = data
            elif ctype == b"tRNS":
                chunks["tRNS"] = data
            elif ctype == b"IDAT":
                idat_data += data
            elif ctype == b"IEND":
                break

    ihdr = chunks["IHDR"]
    width = struct.unpack(">I", ihdr[0:4])[0]
    height = struct.unpack(">I", ihdr[4:8])[0]
    bit_depth = ihdr[8]
    color_type = ihdr[9]
    compression = ihdr[10]
    filter_method = ihdr[11]
    interlace = ihdr[12]

    if bit_depth != 8:
        raise ValueError(f"Unsupported bit depth: {bit_depth} (only 8-bit supported)")
    if interlace != 0:
        raise ValueError("Interlaced PNGs not supported")
    if color_type not in (0, 2, 3, 4, 6):
        raise ValueError(f"Unsupported color type: {color_type}")

    raw = zlib.decompress(idat_data)

    # Determine bytes per pixel
    if color_type == 0:    # Grayscale
        bpp = 1
    elif color_type == 2:  # RGB
        bpp = 3
    elif color_type == 3:  # Indexed
        bpp = 1
    elif color_type == 4:  # Grayscale + Alpha
        bpp = 2
    elif color_type == 6:  # RGBA
        bpp = 4

    stride = width * bpp
    pos = 0
    prev_row = bytes(stride)
    rows = []

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        elif pb <= pc:
            return b
        return c

    for y in range(height):
        ftype = raw[pos]
        pos += 1
        scanline = bytearray(raw[pos : pos + stride])
        pos += stride

        if ftype == 1:    # Sub
            for i in range(stride):
                left = scanline[i - bpp] if i >= bpp else 0
                scanline[i] = (scanline[i] + left) & 0xFF
        elif ftype == 2:  # Up
            for i in range(stride):
                scanline[i] = (scanline[i] + prev_row[i]) & 0xFF
        elif ftype == 3:  # Average
            for i in range(stride):
                left = scanline[i - bpp] if i >= bpp else 0
                scanline[i] = (scanline[i] + (left + prev_row[i]) // 2) & 0xFF
        elif ftype == 4:  # Paeth
            for i in range(stride):
                left = scanline[i - bpp] if i >= bpp else 0
                up = prev_row[i]
                up_left = prev_row[i - bpp] if i >= bpp else 0
                scanline[i] = (scanline[i] + paeth(left, up, up_left)) & 0xFF

        prev_row = bytes(scanline)

        # Convert scanline to RGBA pixels
        row_pixels = []
        if color_type == 0:  # Grayscale
            for x in range(width):
                g = scanline[x]
                row_pixels.append((g, g, g, 255))
        elif color_type == 2:  # RGB
            for x in range(width):
                r, g, b = scanline[x*3], scanline[x*3+1], scanline[x*3+2]
                row_pixels.append((r, g, b, 255))
        elif color_type == 3:  # Indexed (palette)
            plte = chunks.get("PLTE", b"")
            trns = chunks.get("tRNS", b"")
            for x in range(width):
                idx = scanline[x]
                r = plte[idx * 3] if idx * 3 < len(plte) else 0
                g = plte[idx * 3 + 1] if idx * 3 + 1 < len(plte) else 0
                b = plte[idx * 3 + 2] if idx * 3 + 2 < len(plte) else 0
                a = trns[idx] if idx < len(trns) else 255
                row_pixels.append((r, g, b, a))
        elif color_type == 4:  # Grayscale + Alpha
            for x in range(width):
                g, a = scanline[x*2], scanline[x*2+1]
                row_pixels.append((g, g, g, a))
        elif color_type == 6:  # RGBA
            for x in range(width):
                r, g, b, a = scanline[x*4], scanline[x*4+1], scanline[x*4+2], scanline[x*4+3]
                row_pixels.append((r, g, b, a))

        rows.append(row_pixels)

    return width, height, rows


def quantize_to_8x8(width, height, rows):
    """Quantize image to 8x8 grid of palette indices using weighted majority vote.

    Each source pixel is first mapped to its nearest palette colour.  For each
    output cell the palette index whose source pixels cover the largest total
    area wins.  This avoids creating intermediate RGB values that have no good
    match in the limited Launchpad palette.
    """
    out = []
    for oy in range(8):
        row = []
        sy_start = oy * height / 8.0
        sy_end = (oy + 1) * height / 8.0
        for ox in range(8):
            sx_start = ox * width / 8.0
            sx_end = (ox + 1) * width / 8.0

            votes: dict[int, float] = {}

            y0 = int(math.floor(sy_start))
            y1 = int(math.ceil(sy_end))
            x0 = int(math.floor(sx_start))
            x1 = int(math.ceil(sx_end))

            for py in range(y0, min(y1, height)):
                wy_lo = max(py, sy_start)
                wy_hi = min(py + 1, sy_end)
                wy = wy_hi - wy_lo
                if wy <= 0:
                    continue
                for px in range(x0, min(x1, width)):
                    wx_lo = max(px, sx_start)
                    wx_hi = min(px + 1, sx_end)
                    wx = wx_hi - wx_lo
                    if wx <= 0:
                        continue
                    w = wx * wy
                    pr, pg, pb, pa = rows[py][px]
                    alpha = pa / 255.0
                    w *= alpha
                    if w <= 0:
                        continue
                    idx = nearest_palette_index(pr, pg, pb)
                    votes[idx] = votes.get(idx, 0.0) + w

            if votes:
                best_idx = max(votes, key=votes.get)
            else:
                best_idx = 0
            row.append(best_idx)
        out.append(row)
    return out


def convert(input_path, output_path):
    """Main conversion: PNG -> Launchpad .txt format."""
    width, height, rows = _read_png(input_path)

    if width != height:
        print(f"Error: Image must be square (currently {width}x{height}).")
        sys.exit(1)

    if width > 400 or height > 400:
        print(f"Error: Maximum image size is 400x400 (currently {width}x{height}).")
        sys.exit(1)

    # Quantize to 8x8 with majority vote
    grid_rows = quantize_to_8x8(width, height, rows)

    # Write output in Launchpad editor format
    with open(output_path, "w") as f:
        f.write("# Launchpad Mini MK3 pixel art\n")
        f.write("delay 100\n")
        for row_indices in grid_rows:
            f.write(" ".join(str(i) for i in row_indices) + "\n")

    print(f"Saved: {output_path}")
    print("8x8 grid preview (color indices):")
    for row_indices in grid_rows:
        print("  " + " ".join(f"{i:>3}" for i in row_indices))


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("png2launchpad – Convert PNG images to Launchpad Mini MK3 pixel art format")
        print()
        print("Usage: python3 png2launchpad.py <input.png> [output.txt]")
        print()
        print("Converts a PNG image to an 8x8 grid of Launchpad color indices (0-127).")
        print("The image must be square, max 400x400 pixels. Each pixel is mapped to the")
        print("nearest color in the Launchpad palette using perceptual color matching.")
        print()
        print("If output path is omitted, the input filename with .txt extension is used.")
        print()
        print("The output file can be opened in the web editor (index.html) or played")
        print("on hardware with: ./launchpad_grid.py output.txt")
        sys.exit(0)

    input_path = sys.argv[1]
    if not os.path.isfile(input_path):
        print(f"Error: File '{input_path}' not found.")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base = os.path.splitext(input_path)[0]
        output_path = base + ".txt"

    convert(input_path, output_path)


if __name__ == "__main__":
    main()
