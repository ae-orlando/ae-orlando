#!/usr/bin/env python3
"""Recolor a github-profile-3d-contrib SVG to the Yoru palette.

Maps every rgb() fill by luminance onto a warm gradient
(#1a120e -> #52443d -> #a08d85 -> #e6beac -> #ffb692),
preserving the relative shading that gives the 3D effect.
Background #00000f becomes Yoru surface #1a120e.
Hex language-legend colors are left untouched.

Usage: recolor-3d.py <svg-file> [svg-file ...]
"""

import re
import sys

RGB_RE = re.compile(r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)")

# Yoru gradient stops (dark -> light).
STOPS = [
    (0x1A, 0x12, 0x0E),  # surface
    (0x52, 0x44, 0x3D),  # surface variant
    (0xA0, 0x8D, 0x85),  # outline
    (0xE6, 0xBE, 0xAC),  # secondary
    (0xFF, 0xB6, 0x92),  # primary peach
]


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def lerp(a, b, t):
    return round(a + (b - a) * t)


def gradient(t):
    """Interpolate STOPS at position t in [0, 1]."""
    t = min(max(t, 0.0), 1.0)
    seg = t * (len(STOPS) - 1)
    i = min(int(seg), len(STOPS) - 2)
    f = seg - i
    return tuple(lerp(STOPS[i][c], STOPS[i + 1][c], f) for c in range(3))


def recolor(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    colors = {tuple(int(v) for v in m.groups()) for m in RGB_RE.finditer(text)}
    if not colors:
        print(f"{path}: no rgb() fills found, skipping")
        return

    ordered = sorted(colors, key=luminance)
    lo = luminance(ordered[0])
    hi = luminance(ordered[-1])
    span = (hi - lo) or 1.0
    mapping = {
        c: gradient((luminance(c) - lo) / span) for c in ordered
    }

    def replace(m):
        old = tuple(int(v) for v in m.groups())
        r, g, b = mapping[old]
        return f"rgb({r}, {g}, {b})"

    text = RGB_RE.sub(replace, text)
    # Yoru surface background (case-insensitive).
    text = re.sub(r"#00000[fF]", "#1a120e", text)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{path}: remapped {len(mapping)} rgb() shades to Yoru")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: recolor-3d.py <svg-file> [...]")
    for target in sys.argv[1:]:
        recolor(target)
