#!/usr/bin/env python3
"""Generate test PNG images for png2launchpad.py validation."""

import struct
import zlib
import math
import os
import sys

def write_png(filepath, width, height, pixels):
    """Write an RGBA PNG file. pixels is list of rows, each row list of (r,g,b,a)."""
    with open(filepath, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        def write_chunk(ctype, data):
            f.write(struct.pack(">I", len(data)))
            f.write(ctype)
            f.write(data)
            f.write(struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF))
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        write_chunk(b"IHDR", ihdr)
        raw = b""
        for row in pixels:
            raw += b"\x00"
            for r, g, b, a in row:
                raw += bytes([r, g, b, a])
        write_chunk(b"IDAT", zlib.compress(raw))
        write_chunk(b"IEND", b"")


def solid(size, color):
    return [[color] * size for _ in range(size)]


def circles(size):
    """Red circle with yellow inside on white."""
    px = []
    cx, cy = size / 2, size / 2
    r_big, r_small = size * 0.4, size * 0.2
    for y in range(size):
        row = []
        for x in range(size):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d <= r_small:
                row.append((255, 255, 0, 255))
            elif d <= r_big:
                row.append((255, 0, 0, 255))
            else:
                row.append((255, 255, 255, 255))
        px.append(row)
    return px


def quadrants(size):
    """4 quadrants: red, green, blue, yellow."""
    half = size // 2
    px = []
    for y in range(size):
        row = []
        for x in range(size):
            if y < half and x < half:     row.append((255, 0, 0, 255))
            elif y < half:                row.append((0, 255, 0, 255))
            elif x < half:                row.append((0, 0, 255, 255))
            else:                         row.append((255, 255, 0, 255))
        px.append(row)
    return px


def stripes_h(size):
    """Horizontal stripes: red, white, blue, white."""
    colors = [(255,0,0,255), (255,255,255,255), (0,0,255,255), (255,255,255,255)]
    stripe = size // 8
    return [[colors[(y // stripe) % len(colors)]] * size for y in range(size)]


def diagonal(size):
    """White + red diagonal."""
    px = []
    for y in range(size):
        row = []
        for x in range(size):
            if abs(x - y) < size // 8:
                row.append((255, 0, 0, 255))
            else:
                row.append((255, 255, 255, 255))
        px.append(row)
    return px


def gradient_rg(size):
    """Red-green gradient (R increases right, G increases down)."""
    px = []
    for y in range(size):
        row = []
        for x in range(size):
            r = int(255 * x / (size - 1))
            g = int(255 * y / (size - 1))
            row.append((r, g, 0, 255))
        px.append(row)
    return px


def checkerboard(size):
    """Black and white checkerboard, 8 divisions."""
    cell = size // 8
    px = []
    for y in range(size):
        row = []
        for x in range(size):
            if ((x // cell) + (y // cell)) % 2 == 0:
                row.append((255, 255, 255, 255))
            else:
                row.append((0, 0, 0, 255))
        px.append(row)
    return px


def red_square_center(size):
    """White bg with centered red square (50% area)."""
    q1, q3 = size // 4, 3 * size // 4
    px = []
    for y in range(size):
        row = []
        for x in range(size):
            if q1 <= x < q3 and q1 <= y < q3:
                row.append((255, 0, 0, 255))
            else:
                row.append((255, 255, 255, 255))
        px.append(row)
    return px


def tricolor_v(size):
    """3 vertical stripes: green, white, red (like Italian flag)."""
    third = size // 3
    px = []
    for y in range(size):
        row = []
        for x in range(size):
            if x < third:       row.append((0, 128, 0, 255))
            elif x < 2 * third: row.append((255, 255, 255, 255))
            else:               row.append((255, 0, 0, 255))
        px.append(row)
    return px


def concentric_squares(size):
    """Nested squares: blue outer, green middle, red inner on white."""
    px = []
    for y in range(size):
        row = []
        for x in range(size):
            dx = abs(x - size // 2)
            dy = abs(y - size // 2)
            m = max(dx, dy)
            if m < size * 0.125:
                row.append((255, 0, 0, 255))
            elif m < size * 0.25:
                row.append((0, 255, 0, 255))
            elif m < size * 0.375:
                row.append((0, 0, 255, 255))
            else:
                row.append((255, 255, 255, 255))
        px.append(row)
    return px


outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")

tests = {
    "test-circles-64": (circles, 64),
    "test-circles-200": (circles, 200),
    "test-quadrants": (quadrants, 64),
    "test-stripes": (stripes_h, 64),
    "test-diagonal": (diagonal, 64),
    "test-gradient": (gradient_rg, 64),
    "test-checkerboard": (checkerboard, 64),
    "test-redsquare": (red_square_center, 64),
    "test-solid-red": (lambda s: solid(s, (255, 0, 0, 255)), 64),
    "test-solid-white": (lambda s: solid(s, (255, 255, 255, 255)), 64),
    "test-solid-blue": (lambda s: solid(s, (0, 0, 255, 255)), 64),
    "test-solid-green": (lambda s: solid(s, (0, 255, 0, 255)), 64),
    "test-solid-yellow": (lambda s: solid(s, (255, 255, 0, 255)), 64),
    "test-solid-black": (lambda s: solid(s, (0, 0, 0, 255)), 64),
    "test-tricolor": (tricolor_v, 64),
    "test-concentric": (concentric_squares, 64),
}

for name, (func, size) in sorted(tests.items()):
    pixels = func(size)
    path = os.path.join(outdir, f"{name}.png")
    write_png(path, size, size, pixels)
    print(f"Created {path} ({size}x{size})")
