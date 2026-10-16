#!/usr/bin/env python3
"""Level-aware recolor of a github-profile-3d-contrib SVG to the Yoru palette.

How it works:
- Each 3D bar is a <g> of 3 rects: a light top face plus two darker
  side faces. Bars are grouped per <g>, the top face determines the
  contribution level (ranked by luminance), and all three faces are
  repainted from a fixed discrete Yoru triple. This preserves the 3D
  shading exactly while hitting deliberate colors.
- Discrete 5-stop scale (GitHub-style, reads instantly):
    L0 empty -> #241a15, L1 -> #52443d, L2 -> #a08d85,
    L3 -> #e6beac, L4 -> #ffb692 (peach)
- Tallest ~10% of bars get a #ffd9c4 peak glow.
- Radar polygon (#47a042) -> peach, labels #eeeeff -> warm white,
  background #00000f -> Yoru surface #1a120e.
- Hex language-donut colors are left untouched.

Usage: recolor-3d.py <svg-file> [svg-file ...]
"""

import re
import sys

# Per-level top-face colors (dark -> light).
LEVELS = [
    (0x24, 0x1A, 0x15),  # L0 empty
    (0x52, 0x44, 0x3D),  # L1
    (0xA0, 0x8D, 0x85),  # L2
    (0xE6, 0xBE, 0xAC),  # L3
    (0xFF, 0xB6, 0x92),  # L4 peach
]
# Shading ratios (top, left side, right side), measured from stock art.
SHADE = (1.0, 0.84, 0.70)
PEAK = (0xFF, 0xD9, 0xC4)  # glow for the tallest bars

GROUP_RE = re.compile(r'<g transform="translate\([^)]*\)">(.*?)</g>', re.DOTALL)
RECT_RE = re.compile(r"<rect\b[^>]*>")
FILL_RE = re.compile(r'fill="([^"]*)"')
TRANSFORM_RE = re.compile(r'transform="([^"]*)"')
HEIGHT_RE = re.compile(r'height="([\d.]+)"')
RGB_RE = re.compile(r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)")


def parse_rgb(value):
    m = RGB_RE.fullmatch(value.strip())
    return tuple(int(v) for v in m.groups()) if m else None


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def shade(rgb, ratio):
    return tuple(min(255, round(c * ratio)) for c in rgb)


def fmt(rgb):
    return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"


def classify(transform):
    if "skewX" in transform:
        return "top"
    if "translate(" in transform:
        return "side2"
    return "side1"


def recolor(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # 1. Collect top-face colors to establish levels.
    tops = []
    for m in GROUP_RE.finditer(text):
        rects = RECT_RE.findall(m.group(1))
        for rect in rects:
            tm = TRANSFORM_RE.search(rect)
            fm = FILL_RE.search(rect)
            if tm and fm and classify(tm.group(1)) == "top":
                rgb = parse_rgb(fm.group(1))
                if rgb:
                    tops.append(rgb)
    if not tops:
        print(f"{path}: no bars found, skipping")
        return
    ordered = sorted(set(tops), key=luminance)
    level_of = {c: i for i, c in enumerate(ordered)}
    n_levels = len(ordered)

    def level_top(level):
        # Map generator levels onto Yoru stops (both dark -> light).
        idx = round(level * (len(LEVELS) - 1) / max(n_levels - 1, 1))
        return LEVELS[idx]

    # 2. Peak-glow threshold: tallest ~10% of nonzero bars.
    heights = []
    for m in GROUP_RE.finditer(text):
        for rect in RECT_RE.findall(m.group(1)):
            tm = TRANSFORM_RE.search(rect)
            hm = HEIGHT_RE.search(rect)
            if tm and hm and classify(tm.group(1)) == "side1":
                h = float(hm.group(1))
                if h > 3.0:
                    heights.append(h)
    heights.sort()
    peak_at = heights[int(len(heights) * 0.9)] if heights else float("inf")

    # 3. Repaint bars group by group.
    def repaint_group(m):
        body = m.group(1)
        rects = RECT_RE.findall(body)
        roles = {}
        for rect in rects:
            tm = TRANSFORM_RE.search(rect)
            fm = FILL_RE.search(rect)
            if not (tm and fm):
                continue
            role = classify(tm.group(1))
            rgb = parse_rgb(fm.group(1))
            if rgb and role not in roles:
                roles[role] = (rect, rgb)
        if "top" not in roles or len(roles) < 3:
            return m.group(0)  # not a bar group; leave alone
        level = level_of.get(roles["top"][1], 0)
        top = level_top(level)
        # Peak glow check via side1 height.
        hm = HEIGHT_RE.search(roles["side1"][0])
        if hm and float(hm.group(1)) >= peak_at and level == n_levels - 1:
            top = PEAK
        paints = {
            "top": fmt(top),
            "side1": fmt(shade(top, SHADE[1])),
            "side2": fmt(shade(top, SHADE[2])),
        }

        def repaint_rect(rm):
            rect = rm.group(0)
            tm = TRANSFORM_RE.search(rect)
            role = classify(tm.group(1))
            if role in paints:
                rect = FILL_RE.sub(f'fill="{paints[role]}"', rect, count=1)
            return rect

        new_body = RECT_RE.sub(repaint_rect, body)
        start = m.start(1) - m.start(0)
        end = m.end(1) - m.start(0)
        return m.group(0)[:start] + new_body + m.group(0)[end:]

    text = GROUP_RE.sub(repaint_group, text)

    # 4. Radar, labels, background.
    text = re.sub(r"#47a042", "#ffb692", text, flags=re.IGNORECASE)
    text = re.sub(r"#eeeeff", "#f0dfd8", text, flags=re.IGNORECASE)
    text = re.sub(r"#00000f", "#1a120e", text, flags=re.IGNORECASE)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{path}: {len(ordered)} levels repainted to Yoru (peak at height {peak_at:.1f})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: recolor-3d.py <svg-file> [...]")
    for target in sys.argv[1:]:
        recolor(target)
