#!/usr/bin/env python3
"""Generate the Yoru live strip SVG: Nairobi local time, date and weather.

Usage: python3 scripts/generate_live_strip.py [output_path]

Designed for .github/workflows/live-strip.yml: runs on a schedule, writes the
SVG, and force-pushes it to the orphan `live` branch so the README can embed it
via raw.githubusercontent.com without depending on any third-party service.
Weather: open-meteo.com (free, no API key). Timezone: Africa/Nairobi (EAT, UTC+3).
"""

import html
import json
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Africa/Nairobi")
LAT, LON = -1.2921, 36.8219  # Nairobi, KE

# WMO weather codes -> (description, emoji)
WMO = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤"),
    2: ("Partly cloudy", "🌤"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫"),
    48: ("Rime fog", "🌫"),
    51: ("Light drizzle", "🌦"),
    53: ("Drizzle", "🌦"),
    55: ("Dense drizzle", "🌧"),
    56: ("Freezing drizzle", "🌧"),
    57: ("Freezing drizzle", "🌧"),
    61: ("Light rain", "🌧"),
    63: ("Rain", "🌧"),
    65: ("Heavy rain", "🌧"),
    66: ("Freezing rain", "🌧"),
    67: ("Freezing rain", "🌧"),
    71: ("Light snow", "🌨"),
    73: ("Snow", "🌨"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Rain showers", "🌦"),
    81: ("Rain showers", "🌧"),
    82: ("Violent showers", "⛈"),
    85: ("Snow showers", "🌨"),
    86: ("Snow showers", "🌨"),
    95: ("Thunderstorm", "⛈"),
    96: ("Storm with hail", "⛈"),
    99: ("Storm with hail", "⛈"),
}


def fetch_weather():
    """Return (temp_text, description, emoji) — degrades gracefully on errors."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,weather_code&timezone=Africa%2FNairobi"
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            current = json.load(resp)["current"]
        code = current.get("weather_code", -1)
        desc, emoji = WMO.get(code, ("Unknown", "🌡"))
        temp = f"{round(current['temperature_2m'])}\u00b0C"
        return temp, desc, emoji
    except Exception as exc:  # network issues must not break the strip
        print(f"weather fetch failed: {exc}", file=sys.stderr)
        return "\u2014", "weather unavailable", "\U0001f327"


def build_svg():
    now = datetime.now(TZ)
    time_str = now.strftime("%H:%M")
    date_str = f"{now:%a, %b} {now.day}"
    temp, desc, emoji = fetch_weather()

    def esc(s):
        return html.escape(s, quote=False)

    # label segments: fixed x for the first three, end-anchored weather block
    segments = [
        (26, "start", "\U0001f4cd Nairobi, Kenya", "#F0DFD8"),
        (276, "start", f"\U0001f550 {time_str} EAT", None),  # accented below
        (494, "start", f"\U0001f4c5 {date_str}", "#F0DFD8"),
    ]
    seps = [252, 470, 668]

    seg_svg = ""
    for x, anchor, text, fill in segments:
        if fill is None:
            # time value in peach accent, surrounding glyphs cream
            icon, rest = text.split(" ", 1)
            t, _, tail = rest.partition(" ")
            seg_svg += (
                f'<text x="{x}" y="34" font-size="15" fill="#F0DFD8">'
                f'{icon} <tspan fill="#FFB692">{esc(t)}</tspan> {esc(tail)}</text>\n'
            )
        else:
            seg_svg += f'<text x="{x}" y="34" font-size="15" fill="{fill}">{esc(text)}</text>\n'
    sep_svg = "".join(
        f'<line x1="{x}" y1="14" x2="{x}" y2="42" stroke="#463E37" stroke-width="1"/>\n'
        for x in seps
    )
    weather = (
        f'<text x="936" y="34" font-size="15" text-anchor="end" fill="#F0DFD8">'
        f'{emoji} <tspan fill="#FFB692">{esc(temp)}</tspan> &#183; {esc(desc)}</text>'
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 56" width="960" height="56" role="img" aria-label="Nairobi: local time, date and weather">
  <style>text{{font-family:'GoMono Nerd Font Mono','JetBrains Mono','Go Mono',ui-monospace,monospace;font-weight:400;text-rendering:geometricPrecision;white-space:pre}}</style>
  <rect x="0.5" y="0.5" width="959" height="55" rx="10" fill="#1A120E"/>
  {seg_svg}{sep_svg}  {weather}
</svg>
"""


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "now.svg"
    svg = build_svg()
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {out} ({len(svg)} bytes)")
