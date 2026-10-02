#!/usr/bin/env python3
"""Generate the GitHub profile README and outlined SVG modules.

One content source: content.json
Font files stay outside the repository. Pass the directory that contains
IBMPlexMono-Regular.otf, IBMPlexMono-Medium.otf, and IBMPlexMono-Bold.otf.

    python3 scripts/generate.py --font /path/to/otf
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

BG = "#201d1d"
TEXT = "#fdfcfc"
MUTED = "#9a9898"
DIM = "#6e6e73"
ACCENT = "#007aff"
DIVIDER = (253, 252, 252, 0.10)

ASCENT = 1025  # hhea, covers the tallest glyph we draw
DESCENT = 275
UPEM = 1000

EMAIL = "junguang.jia@columbia.edu"
ROOT = Path(__file__).resolve().parents[1]

DESKTOP = {
    "name": "desktop",
    "width": 960,
    "pad": 22,
    "title": 22,
    "body": 14,
    "heading": 14,
    "tag": 12,
    "group": 13,
}
MOBILE = {
    "name": "mobile",
    "width": 340,
    "pad": 14,
    "title": 20,
    "body": 13,
    "heading": 13,
    "tag": 12,
    "group": 13,
}

ICONS = ROOT / "icons"
CHIP_H = 26
CHIP_LOGO = 13
CHIP_PAD = 8
CHIP_GAP = 6
CHIP_TEXT = 12
CHIP_RADIUS = 3

# Brand color is limited to the logo or the chip fill. Labels stay in IBM Plex Mono.
BADGE_STYLE = {
    "typescript": {"icon": "typescript", "fill": "#3178C6", "mark": "#fdfcfc", "ink": "#fdfcfc"},
    "swift": {"icon": "swift", "fill": "#F05138", "mark": "#ffffff", "ink": "#ffffff"},
    "python": {"icon": "python", "fill": "#302c2c", "mark": "#FFD43B", "ink": "#fdfcfc"},
    "julia": {"icon": "julia", "fill": "#9558B2", "mark": "#ffffff", "ink": "#ffffff"},
    "r": {"icon": "r", "fill": "#302c2c", "mark": "#276DC3", "ink": "#fdfcfc"},
    "sql": {"icon": "sql", "fill": "#302c2c", "mark": "#fdfcfc", "ink": "#fdfcfc"},
    "react": {"icon": "react", "fill": "#302c2c", "mark": "#61DAFB", "ink": "#fdfcfc"},
    "nextjs": {"icon": "nextdotjs", "fill": "#302c2c", "mark": "#fdfcfc", "ink": "#fdfcfc"},
    "postgresql": {"icon": "postgresql", "fill": "#336791", "mark": "#ffffff", "ink": "#ffffff"},
    "web": {"icon": "web", "fill": "#302c2c", "mark": "#007aff", "ink": "#fdfcfc"},
    "macos": {"icon": None, "fill": "#302c2c", "mark": None, "ink": "#fdfcfc"},
    "linux": {"icon": "linux", "fill": "#302c2c", "mark": "#FCC624", "ink": "#fdfcfc"},
    "docker": {"icon": "docker", "fill": "#2496ED", "mark": "#ffffff", "ink": "#ffffff"},
    "githubactions": {"icon": "githubactions", "fill": "#302c2c", "mark": "#2088FF", "ink": "#fdfcfc"},
    "website": {"icon": "web", "fill": "#302c2c", "mark": "#007aff", "ink": "#fdfcfc"},
    "email": {"icon": "mail", "fill": "#302c2c", "mark": "#007aff", "ink": "#fdfcfc"},
}


def round_path(commands: str) -> str:
    def repl(match: re.Match[str]) -> str:
        value = float(match.group())
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        if text == "-0":
            return "0"
        return text

    return re.sub(r"-?\d+\.\d+", repl, commands)


class Face:
    def __init__(self, path: Path) -> None:
        self.font = TTFont(str(path))
        self.glyph_set = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        if self.font["head"].unitsPerEm != UPEM:
            raise SystemExit(f"{path.name} has an unexpected units-per-em")
        self.family = self._name(16) or self._name(1)
        self.style = self._name(17) or self._name(2)
        self.license = self._name(13)
        self.fs_type = int(self.font["OS/2"].fsType)
        self._paths: dict[str, str] = {}
        self._bounds: dict[str, tuple[float, float, float, float] | None] = {}

    def _name(self, name_id: int) -> str:
        for record in self.font["name"].names:
            if record.nameID == name_id:
                return record.toUnicode()
        return ""

    def require(self, text: str) -> None:
        missing = sorted({ch for ch in text if ch != "\n" and ord(ch) not in self.cmap})
        if missing:
            shown = ", ".join(repr(ch) for ch in missing)
            raise SystemExit(f"{self.family} {self.style} is missing {shown}")

    def width(self, text: str, size: float) -> float:
        scale = size / UPEM
        total = 0.0
        for ch in text:
            total += self.glyph_set[self.cmap[ord(ch)]].width * scale
        return total

    def path(self, ch: str) -> str:
        if ch in self._paths:
            return self._paths[ch]
        pen = SVGPathPen(self.glyph_set)
        self.glyph_set[self.cmap[ord(ch)]].draw(pen)
        commands = round_path(pen.getCommands() or "")
        self._paths[ch] = commands
        return commands

    def bounds(self, ch: str) -> tuple[float, float, float, float] | None:
        if ch in self._bounds:
            return self._bounds[ch]
        pen = BoundsPen(self.glyph_set)
        self.glyph_set[self.cmap[ord(ch)]].draw(pen)
        self._bounds[ch] = pen.bounds
        return pen.bounds


class Fonts:
    def __init__(self, directory: Path) -> None:
        files = {
            "regular": "IBMPlexMono-Regular.otf",
            "medium": "IBMPlexMono-Medium.otf",
            "bold": "IBMPlexMono-Bold.otf",
        }
        self.faces = {}
        for weight, name in files.items():
            path = directory / name
            if not path.is_file():
                raise SystemExit(f"Missing {path}. Pass the official IBM Plex Mono OTF directory.")
            self.faces[weight] = Face(path)
        family = {face.family for face in self.faces.values()}
        if family != {"IBM Plex Mono"}:
            raise SystemExit(f"Expected IBM Plex Mono, found {family}")

    def face(self, weight: str) -> Face:
        return self.faces[weight]

    def require(self, text: str) -> None:
        for face in self.faces.values():
            face.require(text)


TYPE_STEP = 0.035
BLOCK_GAP = 0.12


def reveal_animation(when: float) -> str:
    # begin= keeps the element hidden until this time. A discrete keyTimes
    # timeline was showing the later blocks while the title was still typing.
    return (
        f'<animate attributeName="opacity" begin="{max(when, 0):.3f}s" '
        f'from="0" to="1" dur="0.01s" fill="freeze"/>'
    )


def nest(canvas: "Canvas", spec: dict, level: int) -> None:
    unit = 16 if spec["name"] == "desktop" else 10
    canvas.pad = spec["pad"] + level * unit


def shell_pad(spec: dict) -> float:
    return 36 if spec["name"] == "desktop" else 22


class Canvas:
    def __init__(self, fonts: Fonts, spec: dict) -> None:
        self.fonts = fonts
        self.width = spec["width"]
        self.pad = spec["pad"]
        self.edge = spec["pad"]
        self.y = 0.0
        self.parts: list[str] = []
        self.ink: list[tuple[float, float, float, float]] = []
        self.typing = False
        self.clock = 0.0
        self.step = TYPE_STEP
        self.stops: list[tuple[float, float]] = []
        self.reveal_at: float | None = None
        self.shell = "mid"

    def measure(self, text: str, size: float, weight: str) -> float:
        return self.fonts.face(weight).width(text, size)

    def spacer(self, amount: float) -> None:
        self.y += amount

    def rule(self) -> None:
        y = round(self.y + 0.5, 2)
        x1 = self.pad
        x2 = self.width - self.edge
        self.parts.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
            'stroke="#fdfcfc" stroke-opacity="0.10" stroke-width="1"/>'
        )
        self.y += 1

    def line(self, runs: list[tuple[str, str, str]], size: float, leading: float = 1.45) -> float:
        """Draw one line. runs are (text, fill, weight). Returns the end x."""
        box = max(size * leading, size * (ASCENT + DESCENT) / UPEM)
        baseline = self.y + (box - size * DESCENT / UPEM)
        x = float(self.pad)
        for text, fill, weight in runs:
            x = self.draw(text, x, baseline, size, weight, fill)
        if x > self.width - self.edge + 0.4:
            preview = "".join(text for text, _, _ in runs)
            raise SystemExit(
                f"Line is {x:.1f}px wide on a {self.width}px canvas: {preview}"
            )
        self.y += box
        return x

    def draw(
        self,
        text: str,
        x: float,
        baseline: float,
        size: float,
        weight: str,
        fill: str,
        animate: bool = False,
    ) -> float:
        face = self.fonts.face(weight)
        scale = size / UPEM
        for ch in text:
            glyph_width = face.glyph_set[face.cmap[ord(ch)]].width * scale
            commands = face.path(ch)
            bounds = face.bounds(ch)
            if bounds:
                xmin, ymin, xmax, ymax = bounds
                self.ink.append(
                    (
                        x + xmin * scale,
                        baseline - ymax * scale,
                        x + xmax * scale,
                        baseline - ymin * scale,
                    )
                )
            reveal_at = None
            if self.typing:
                self.stops.append((x, baseline))
                reveal_at = self.clock
                self.clock += self.step
            if commands:
                transform = f"translate({x:.2f},{baseline:.2f}) scale({scale:.5f},{-scale:.5f})"
                animation = ""
                group_id = ""
                if animate:
                    group_id = ' id="cursor"'
                    animation = (
                        '<animate attributeName="opacity" values="1;0" keyTimes="0;0.5" '
                        'dur="1.1s" repeatCount="indefinite" calcMode="discrete"/>'
                    )
                elif reveal_at is not None:
                    animation = reveal_animation(reveal_at)
                hidden = ' opacity="0"' if reveal_at is not None else ""
                self.parts.append(
                    f'<g{group_id} transform="{transform}"{hidden}>{animation}'
                    f'<path d="{commands}" fill="{fill}"></path></g>'
                )
            x += glyph_width
        return x

    def draw_cursor(self, x: float, baseline: float, size: float, blink: bool) -> None:
        face = self.fonts.face("bold")
        scale = size / UPEM
        commands = face.path("_")
        bounds = face.bounds("_")
        if bounds:
            xmin, ymin, xmax, ymax = bounds
            self.ink.append(
                (
                    x + xmin * scale,
                    baseline - ymax * scale,
                    x + xmax * scale,
                    baseline - ymin * scale,
                )
            )
        blink_anim = ""
        if blink:
            blink_anim = (
                '<animate attributeName="opacity" values="1;0" keyTimes="0;0.5" '
                'dur="1.1s" repeatCount="indefinite" calcMode="discrete"/>'
            )
        motion = ""
        transform = f'translate({x:.2f},{baseline:.2f})'
        if blink and len(self.stops) > 1:
            stops = [*self.stops, (x, baseline)]
            count = len(stops) - 1
            values = ";".join(f"{sx:.2f},{sy:.2f}" for sx, sy in stops)
            key_times = ";".join(f"{i / count:.4f}" for i in range(count + 1))
            dur = count * self.step
            motion = (
                f'<animateTransform attributeName="transform" type="translate" '
                f'values="{values}" keyTimes="{key_times}" dur="{dur:.3f}s" '
                f'begin="0s" fill="freeze" calcMode="discrete"/>'
            )
        self.parts.append(
            f'<g id="cursor" transform="{transform}">{motion}'
            f'<g transform="scale({scale:.5f},{-scale:.5f})">'
            f'<path d="{commands}" fill="{MUTED}">{blink_anim}</path></g></g>'
        )

    def wrapped(self, text: str, size: float, weight: str, fill: str, leading: float) -> None:
        max_width = self.width - self.pad - self.edge
        lines: list[str] = []
        current = ""
        for word in text.split():
            trial = word if not current else f"{current} {word}"
            if self.measure(trial, size, weight) <= max_width:
                current = trial
                continue
            if not current:
                raise SystemExit(f"Word does not fit: {word}")
            lines.append(current)
            current = word
        if current:
            lines.append(current)
        if len(lines) >= 2:
            last_words = lines[-1].split()
            previous_words = lines[-2].split()
            if len(last_words) == 1 and len(previous_words) >= 2 and len(last_words[0]) < 14:
                moved = previous_words[-1]
                trial = f"{moved} {lines[-1]}"
                if self.measure(trial, size, weight) <= max_width:
                    lines[-2] = " ".join(previous_words[:-1])
                    lines[-1] = trial
        for line in lines:
            self.line([(line, fill, weight)], size, leading)

    def tags(self, tags: list[str], size: float) -> None:
        max_width = self.width - self.pad - self.edge
        gap = round(size * 0.85, 2)
        lines: list[list[str]] = []
        current: list[str] = []
        used = 0.0
        for tag in tags:
            width = self.measure(f"[{tag}]", size, "medium")
            extra = width if not current else gap + width
            if current and used + extra > max_width:
                lines.append(current)
                current = [tag]
                used = width
            else:
                current.append(tag)
                used += extra
        if current:
            lines.append(current)
        for line in lines:
            box = size * 1.7
            baseline = self.y + (box - size * DESCENT / UPEM)
            x = float(self.pad)
            for index, tag in enumerate(line):
                if index:
                    x += gap
                x = self.draw("[", x, baseline, size, "medium", DIM)
                x = self.draw(tag, x, baseline, size, "medium", MUTED)
                x = self.draw("]", x, baseline, size, "medium", DIM)
            self.y += box

    def finish(self, bottom: float, label: str = "") -> str:
        self.y += bottom
        height = int(round(self.y))
        for left, top, right, bottom_edge in self.ink:
            if left < -0.4 or top < -0.4 or right > self.width + 0.4 or bottom_edge > height + 0.4:
                raise SystemExit(
                    f"Glyph clipped in {label}: "
                    f"box=({left:.1f},{top:.1f},{right:.1f},{bottom_edge:.1f}) "
                    f"canvas={self.width}x{height}"
                )
        body = "".join(self.parts)
        if self.reveal_at is not None:
            body = f'<g opacity="0">{body}{reveal_animation(self.reveal_at)}</g>'
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{height}" '
            f'viewBox="0 0 {self.width} {height}">'
            f"{self.shell_frame(height)}{body}</svg>\n"
        )

    def shell_frame(self, height: int) -> str:
        w = self.width
        h = height
        r = 12
        stroke = "#4a4646"
        if self.shell == "top":
            fill = (
                f'<path d="M0,{h}H{w}V{r}Q{w},0 {w - r},0H{r}Q0,0 0,{r}Z" fill="{BG}"/>'
            )
            edge = (
                f'<path d="M0.5,{h}V{r}Q0.5,0.5 {r},0.5H{w - r}Q{w - 0.5},0.5 {w - 0.5},{r}V{h}" '
                f'fill="none" stroke="{stroke}" stroke-width="1"/>'
            )
        elif self.shell == "bottom":
            fill = (
                f'<path d="M0,0H{w}V{h - r}Q{w},{h} {w - r},{h}H{r}Q0,{h} 0,{h - r}Z" fill="{BG}"/>'
            )
            edge = (
                f'<path d="M0.5,0V{h - r}Q0.5,{h - 0.5} {r},{h - 0.5}H{w - r}'
                f'Q{w - 0.5},{h - 0.5} {w - 0.5},{h - r}V0" '
                f'fill="none" stroke="{stroke}" stroke-width="1"/>'
            )
        else:
            fill = f'<rect width="{w}" height="{h}" fill="{BG}"/>'
            edge = (
                f'<path d="M0.5,0V{h}M{w - 0.5},0V{h}" fill="none" stroke="{stroke}" stroke-width="1"/>'
            )
        return fill + edge


def icon_paths(icon: str) -> list[str]:
    if icon == "sql":
        return [
            "M12 3c-4.5 0-8 1.4-8 3.2v11.6c0 1.8 3.5 3.2 8 3.2s8-1.4 8-3.2V6.2C20 4.4 16.5 3 12 3zm0 2.2c3.4 0 6 .8 6 1.6s-2.6 1.6-6 1.6-6-.8-6-1.6 2.6-1.6 6-1.6z"
        ]
    if icon == "web":
        return [
            "M12 2.2a9.8 9.8 0 1 0 0 19.6 9.8 9.8 0 0 0 0-19.6zm0 1.8c1.7 0 3.2 2.5 3.6 6H8.4c.4-3.5 1.9-6 3.6-6zM4.4 12c.2-1.2.7-2.3 1.4-3.2h2.3c-.2 1-.3 2.1-.3 3.2s.1 2.2.3 3.2H5.8A8 8 0 0 1 4.4 12zm4 0c0-1.2.1-2.3.3-3.2h6.6c.2.9.3 2 .3 3.2s-.1 2.3-.3 3.2H8.7c-.2-.9-.3-2-.3-3.2zm7.5 3.2c.2-1 .3-2.1.3-3.2s-.1-2.2-.3-3.2h2.3c.7.9 1.2 2 1.4 3.2a8 8 0 0 1-1.4 3.2h-2.3zM12 20c-1.7 0-3.2-2.5-3.6-6h7.2c-.4 3.5-1.9 6-3.6 6z"
        ]
    if icon == "mail":
        return ["M3 6.5h18V18H3V6.5zm1.6 1.4 7.4 5 7.4-5V8l-7.4 5L4.6 8v-.1z"]
    path = ICONS / f"{icon}.svg"
    if not path.is_file():
        raise SystemExit(f"Missing icon {path}")
    found = re.findall(r'\bd="([^"]+)"', path.read_text(encoding="utf-8"))
    if not found:
        raise SystemExit(f"{path} has no path")
    return found


def chip_width(fonts: Fonts, label: str, has_icon: bool) -> float:
    text = fonts.face("medium").width(label, CHIP_TEXT)
    if has_icon:
        return CHIP_PAD + CHIP_LOGO + 6 + text + CHIP_PAD
    return 12 + text + 12


def draw_chip(canvas: Canvas, fonts: Fonts, label: str, style: dict, x: float, y: float) -> float:
    has_icon = bool(style["icon"])
    width = chip_width(fonts, label, has_icon)
    canvas.parts.append(
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{CHIP_H}" '
        f'rx="{CHIP_RADIUS}" fill="{style["fill"]}"/>'
    )
    text_x = x + (CHIP_PAD + CHIP_LOGO + 6 if has_icon else 12)
    if has_icon:
        scale = CHIP_LOGO / 24
        icon_x = x + CHIP_PAD
        icon_y = y + (CHIP_H - CHIP_LOGO) / 2
        transform = f'translate({icon_x:.2f},{icon_y:.2f}) scale({scale:.5f})'
        if style["icon"] == "mail":
            canvas.parts.append(
                f'<g transform="{transform}">'
                f'<path d="M3 6h18v12H3z" fill="{style["mark"]}"/>'
                f'<path d="M4.2 8.1 12 13.2 19.8 8.1" fill="none" stroke="{style["fill"]}" '
                f'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
                f'</g>'
            )
        else:
            paths = "".join(
                f'<path d="{commands}" fill="{style["mark"]}"/>' for commands in icon_paths(style["icon"])
            )
            canvas.parts.append(f'<g transform="{transform}">{paths}</g>')
    baseline = y + (CHIP_H + 0.70 * CHIP_TEXT) / 2
    canvas.draw(label, text_x, baseline, CHIP_TEXT, "medium", style["ink"])
    return width


def build_title(fonts: Fonts, content: dict, spec: dict, animate: bool) -> str:
    canvas = Canvas(fonts, spec)
    canvas.shell = "top"
    canvas.typing = animate
    size = spec["title"]
    box = max(size * 1.15, size * (ASCENT + DESCENT) / UPEM)
    above_caps = box - size * DESCENT / UPEM - size * 0.70
    canvas.spacer(max(8, shell_pad(spec) - above_caps))
    lines = content["heading"][spec["name"]]
    for index, line in enumerate(lines):
        end = canvas.line([(line, TEXT, "bold")], size, 1.15)
        if index != len(lines) - 1:
            continue
        box = max(size * 1.15, size * (ASCENT + DESCENT) / UPEM)
        baseline = canvas.y - box + (box - size * DESCENT / UPEM)
        limit = spec["width"] - canvas.edge
        canvas.typing = False
        canvas.draw_cursor(end, baseline, size, blink=animate)
        cursor_end = end + fonts.face("bold").width("_", size)
        if cursor_end > limit + 0.4:
            raise SystemExit(
                f"Heading does not fit the {spec['name']} module "
                f"({cursor_end:.1f}px > {limit:.1f}px)."
            )
    canvas.spacer(4 if spec["name"] == "desktop" else 4)
    return canvas.finish(2, "title")


def build_intro(fonts: Fonts, content: dict, spec: dict, reveal: float | None) -> str:
    canvas = Canvas(fonts, spec)
    canvas.reveal_at = reveal
    nest(canvas, spec, 1)
    canvas.spacer(4)
    canvas.wrapped(content["intro"], spec["body"], "regular", TEXT, 1.6)
    canvas.spacer(2)
    return canvas.finish(4 if spec["name"] == "desktop" else 4, "intro")


def build_group(
    fonts: Fonts, content: dict, group: dict, spec: dict, reveal: float | None, shell: str = "mid"
) -> str:
    canvas = Canvas(fonts, spec)
    canvas.shell = shell
    canvas.reveal_at = reveal
    nest(canvas, spec, 2)
    canvas.spacer(2)
    canvas.line([(group["label"], TEXT, "bold")], spec["group"], 1.25)
    canvas.spacer(6)
    nest(canvas, spec, 3)
    x = float(canvas.pad)
    y = canvas.y
    limit = spec["width"] - canvas.edge
    row_bottom = y + CHIP_H
    for item_id in group["items"]:
        if item_id not in content["badges"] or item_id not in BADGE_STYLE:
            raise SystemExit(f"Unknown badge {item_id}")
        label = content["badges"][item_id]
        style = BADGE_STYLE[item_id]
        width = chip_width(fonts, label, bool(style["icon"]))
        if x > canvas.pad and x + width > limit + 0.4:
            y = row_bottom + CHIP_GAP
            x = float(canvas.pad)
            row_bottom = y + CHIP_H
        draw_chip(canvas, fonts, label, style, x, y)
        x += width + CHIP_GAP
    canvas.y = row_bottom
    bottom = shell_pad(spec) if canvas.shell == "bottom" else 6
    return canvas.finish(bottom, group["id"])


def build_contact(fonts: Fonts, content: dict, contact: dict, spec: dict, reveal: float | None) -> str:
    canvas = Canvas(fonts, spec)
    canvas.reveal_at = reveal
    nest(canvas, spec, 1)
    size = spec["body"]
    canvas.spacer(1)
    end = canvas.line(
        [
            (contact["prompt"], ACCENT, "medium"),
            (" > ", DIM, "regular"),
            (contact["text"], TEXT, "medium"),
        ],
        size,
        1.35,
    )
    box = max(size * 1.35, size * (ASCENT + DESCENT) / UPEM)
    baseline = canvas.y - box + (box - size * DESCENT / UPEM)
    prefix = (
        fonts.face("medium").width(contact["prompt"], size)
        + fonts.face("regular").width(" > ", size)
    )
    underline_y = round(baseline + max(3, size * 0.22), 2)
    canvas.parts.append(
        f'<line x1="{canvas.pad + prefix:.2f}" y1="{underline_y}" x2="{end:.2f}" y2="{underline_y}" '
        'stroke="#fdfcfc" stroke-width="1"/>'
    )
    # The email row must be at least as tall as GitHub's link line box,
    # or the browser underline opens a light gap before the next image.
    bottom = 14 if contact["id"] == "email" else 8
    return canvas.finish(bottom, contact["id"])


def build_heading(fonts: Fonts, label: str, spec: dict, first_gap: float, reveal: float | None) -> str:
    canvas = Canvas(fonts, spec)
    canvas.reveal_at = reveal
    nest(canvas, spec, 1)
    canvas.spacer(first_gap)
    size = spec["heading"]
    canvas.line([("# ", MUTED, "regular"), (label, TEXT, "bold")], size, 1.35)
    canvas.spacer(4)
    canvas.rule()
    return canvas.finish(6 if spec["name"] == "desktop" else 6, "heading")


def build_project(fonts: Fonts, project: dict, spec: dict, reveal: float | None) -> str:
    canvas = Canvas(fonts, spec)
    canvas.reveal_at = reveal
    nest(canvas, spec, 2)
    canvas.spacer(8 if spec["name"] == "desktop" else 6)
    size = spec["heading"]
    canvas.line([("## ", MUTED, "regular"), (project["name"], TEXT, "bold")], size, 1.3)
    canvas.spacer(4)
    nest(canvas, spec, 3)
    canvas.wrapped(project["description"], spec["body"], "regular", TEXT, 1.45)
    canvas.spacer(4)
    canvas.tags(project["tags"], spec["tag"])
    return canvas.finish(6 if spec["name"] == "desktop" else 4, "project")


def picture(
    desktop: str,
    mobile: str,
    alt: str,
    sources: list[tuple[str, str]] | None = None,
    full: bool = True,
) -> str:
    extra = ""
    if sources:
        extra = "".join(f'<source media="{media}" srcset="{src}">' for media, src in sources)
    width = ' width="100%"' if full else ""
    return (
        f'<picture>{extra}'
        f'<source media="(max-width: 720px)" srcset="{mobile}">'
        f'<img src="{desktop}"{width} align="top" alt="{html.escape(alt, quote=True)}">'
        f"</picture>"
    )


def linked(href: str, title: str, inner: str) -> str:
    return (
        f'<a href="{html.escape(href, quote=True)}" title="{html.escape(title, quote=True)}">'
        f"{inner}</a>"
    )


ASSET_REV = "6"


def asset(path: str) -> str:
    return f"{path}?v={ASSET_REV}"


def module(name: str, alt: str) -> str:
    return picture(
        asset(f"readme/{name}.svg"),
        asset(f"readme/mobile/{name}.svg"),
        alt,
        [
            (
                "(max-width: 720px) and (prefers-reduced-motion: reduce)",
                asset(f"readme/mobile/{name}-static.svg"),
            ),
            ("(prefers-reduced-motion: reduce)", asset(f"readme/{name}-static.svg")),
        ],
    )


def contact_line(contact: dict) -> str:
    return f"{contact['prompt']} > {contact['text']}"


def build_readme(content: dict) -> str:
    heading = "software · systems · machine learning"
    contacts = []
    for contact in content["contacts"]:
        contacts.append(
            linked(
                contact["href"],
                contact["title"],
                module(f"contact-{contact['id']}", contact_line(contact)),
            )
        )
    parts = [
        "<!-- Outlined with IBM Plex Mono. Edit content.json and regenerate. -->",
        "<p>",
        module("title", heading),
        module("intro", content["intro"]),
        "".join(contacts),
        module("heading-selected", "Selected"),
    ]
    for project in content["selected"]["projects"]:
        parts.append(linked(project["href"], project["alt"], module(f"project-{project['id']}", project["alt"])))
    parts.append(module("heading-stack", "Stack"))
    for group in content["stack"]["groups"]:
        labels = ", ".join(content["badges"][item] for item in group["items"])
        parts.append(module(f"group-{group['id']}", f"{group['label']}: {labels}"))
    parts.append("</p>")
    parts.append(text_version(content))
    return "\n".join(parts) + "\n"


def text_version(content: dict) -> str:
    blocks = [
        "<details>",
        "<summary>Text version</summary>",
        "<p>software · systems · machine learning</p>",
        f"<p>{html.escape(content['intro'])}</p>",
        "<p>"
        + "<br>".join(
            f'{html.escape(contact["prompt"])} &gt; '
            f'<a href="{html.escape(contact["href"], quote=True)}">{html.escape(contact["text"])}</a>'
            for contact in content["contacts"]
        )
        + "</p>",
        "<p># selected</p>",
    ]
    for project in content["selected"]["projects"]:
        tags = " · ".join(project["tags"])
        blocks.append(
            "<p>## "
            f'<a href="{html.escape(project["href"], quote=True)}">{html.escape(project["name"])}</a>'
            f"<br>{html.escape(project['description'])}<br>{html.escape(tags)}</p>"
        )
    blocks.append("<p># stack</p>")
    for group in content["stack"]["groups"]:
        labels = " · ".join(content["badges"][item] for item in group["items"])
        blocks.append(f"<p>{html.escape(group['label'])}<br>{html.escape(labels)}</p>")
    blocks.append("</details>")
    return "\n".join(blocks)


def corpus(content: dict) -> str:
    chunks = [
        content["intro"],
        content["email"],
        "software · systems · machine learning",
        "# ## _ [ ] · & .",
    ]
    chunks.append(content["selected"]["label"])
    for project in content["selected"]["projects"]:
        chunks.extend([project["name"], project["description"], project["alt"], *project["tags"]])
    chunks.append(content["stack"]["label"])
    for group in content["stack"]["groups"]:
        chunks.append(group["label"])
        chunks.extend(content["badges"][item] for item in group["items"])
    for contact in content["contacts"]:
        chunks.extend([contact["prompt"], contact["text"], " > ", contact["title"]])
    return "\n".join(chunks)


def schedule(content: dict, spec: dict) -> dict[str, float]:
    count = sum(len(line) for line in content["heading"][spec["name"]])
    cursor = count * TYPE_STEP + 0.28
    times: dict[str, float] = {}

    def take() -> float:
        nonlocal cursor
        times_now = cursor
        cursor += BLOCK_GAP
        return times_now

    times["intro"] = take()
    for contact in content["contacts"]:
        times[contact["id"]] = take()
    times["selected"] = take()
    for project in content["selected"]["projects"]:
        times[project["id"]] = take()
    times["stack"] = take()
    for group in content["stack"]["groups"]:
        times[group["id"]] = take()
    return times


def render_all(fonts: Fonts, content: dict, spec: dict) -> dict[str, str]:
    assets: dict[str, str] = {}
    times = schedule(content, spec)
    for motion in (True, False):
        suffix = "" if motion else "-static"
        reveal = (lambda key: times[key]) if motion else (lambda key: None)
        assets[f"title{suffix}.svg"] = build_title(fonts, content, spec, animate=motion)
        assets[f"intro{suffix}.svg"] = build_intro(fonts, content, spec, reveal("intro"))
        assets[f"heading-selected{suffix}.svg"] = build_heading(
            fonts, content["selected"]["label"], spec, 14, reveal("selected")
        )
        assets[f"heading-stack{suffix}.svg"] = build_heading(
            fonts, content["stack"]["label"], spec, 12, reveal("stack")
        )
        for group in content["stack"]["groups"]:
            last_group = content["stack"]["groups"][-1]["id"]
            assets[f"group-{group['id']}{suffix}.svg"] = build_group(
                fonts,
                content,
                group,
                spec,
                reveal(group["id"]),
                "bottom" if group["id"] == last_group else "mid",
            )
        for contact in content["contacts"]:
            assets[f"contact-{contact['id']}{suffix}.svg"] = build_contact(
                fonts, content, contact, spec, reveal(contact["id"])
            )
        for project in content["selected"]["projects"]:
            assets[f"project-{project['id']}{suffix}.svg"] = build_project(
                fonts, project, spec, reveal(project["id"])
            )
    return assets


def validate(root: Path, content: dict) -> None:
    email = content["email"]
    if email != EMAIL:
        raise SystemExit(f"Email must be exactly {EMAIL}")
    if content["heading"]["desktop"] != ["software · systems · machine learning"]:
        raise SystemExit("Desktop heading must be exactly software · systems · machine learning")
    if content["heading"]["mobile"] != ["software · systems", "machine learning"]:
        raise SystemExit("Mobile heading must break before machine learning")
    if content["intro"] != "I build full-stack applications, native tools, and computational software.":
        raise SystemExit("Introductory sentence does not match")
    readme = (root / "README.md").read_text(encoding="utf-8")
    if readme.count(f'href="mailto:{email}"') != 2:
        raise SystemExit("mailto target must appear on the email line and in the text version")
    if 'alt="&gt; junguangjia"' in readme:
        raise SystemExit("The header still repeats the username")
    if 'alt="Website"' in readme or 'alt="Email"' in readme:
        raise SystemExit("Contact lines should be the typed address, not a badge label")
    if "Photography" in readme or "junguang-jia-gallery" in readme or "> photos" in readme:
        raise SystemExit("Photography is still in the profile")
    if "Linux" not in readme:
        raise SystemExit("Linux is missing from the profile")
    for banned in ("Yoyi", "Moya", "lorem", "Berkeley Mono", "Convex", "Tailwind", "shadcn"):
        visible = readme.replace("moya-inscriptions-web", "")
        if banned in visible:
            raise SystemExit(f"Unexpected visible copy: {banned}")
    names = [project["name"] for project in content["selected"]["projects"]]
    if names != ["ArtVenn", "Audio Transcribe", "Stochastic Trace Estimation"]:
        raise SystemExit(f"Unexpected project list: {names}")
    svgs = list((root / "readme").rglob("*.svg"))
    if len(svgs) < 10:
        raise SystemExit("Too few SVG assets")
    for path in svgs:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for banned in ("<text", "<font", "@font-face", "<script", "font-family", "<style", "base64", "woff", ".ttf", ".otf"):
            if banned in lowered:
                raise SystemExit(f"{path} contains {banned}")
        if "href=" in lowered or "url(" in lowered or "xlink:" in lowered:
            raise SystemExit(f"{path} references an external resource")
        if "<path " not in text:
            raise SystemExit(f"{path} has no outlined text")
        if path.stat().st_size > 180_000:
            raise SystemExit(f"{path} is {path.stat().st_size} bytes")
    animated = (root / "readme" / "title.svg").read_text(encoding="utf-8")
    static = (root / "readme" / "title-static.svg").read_text(encoding="utf-8")
    intro = (root / "readme" / "intro.svg").read_text(encoding="utf-8")
    intro_static = (root / "readme" / "intro-static.svg").read_text(encoding="utf-8")
    if 'dur="1.1s"' not in animated or "<animate " not in animated or 'id="cursor"' not in animated:
        raise SystemExit("Heading cursor animation is missing")
    if animated.count("<animate ") < 10:
        raise SystemExit("Heading is not typed out character by character")
    if "<animate " in static or "<animate " in intro_static:
        raise SystemExit("Reduced-motion assets still animate")
    if "<animate " not in intro:
        raise SystemExit("The introduction does not appear after the command")
    if 'stroke="#007aff"' in animated:
        raise SystemExit("The heading is still underlined")
    font_files = list(root.rglob("*.otf")) + list(root.rglob("*.ttf")) + list(root.rglob("*.woff")) + list(root.rglob("*.woff2"))
    if font_files:
        raise SystemExit(f"Font files must not be committed: {font_files}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the profile README assets.")
    parser.add_argument("--font", required=True, type=Path, help="Directory of IBM Plex Mono OTF files")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    root = args.root.resolve()
    content = json.loads((root / "content.json").read_text(encoding="utf-8"))
    if content["email"] != EMAIL:
        raise SystemExit(f"content.json email must be exactly {EMAIL}")
    fonts = Fonts(args.font.resolve())
    fonts.require(corpus(content))
    regular = fonts.face("regular")
    if "SIL Open Font License" not in regular.license or regular.fs_type != 0:
        raise SystemExit("Refusing to outline a font whose license or embedding bits are unexpected")

    old_assets = root / "assets"
    if old_assets.exists():
        shutil.rmtree(old_assets)
    assets = root / "readme"
    if assets.exists():
        shutil.rmtree(assets)
    (assets / "mobile").mkdir(parents=True)
    for name, svg in render_all(fonts, content, DESKTOP).items():
        (assets / name).write_text(svg, encoding="utf-8")
    for name, svg in render_all(fonts, content, MOBILE).items():
        (assets / "mobile" / name).write_text(svg, encoding="utf-8")
    (root / "README.md").write_text(build_readme(content), encoding="utf-8")
    validate(root, content)

    print(f"IBM Plex Mono {fonts.face('bold').font['name'].getDebugName(5)}")
    total = sum(path.stat().st_size for path in (root / "readme").rglob("*.svg"))
    print(f"svg bytes: {total}")


if __name__ == "__main__":
    main()
