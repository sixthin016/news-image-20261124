#!/usr/bin/env python3
"""THE WORLD TODAY - Tuesday 24 November 2026, summed up in one image.

A newspaper front page drawn entirely in code (Python standard library
only, no network, no randomness, no wall-clock time): a masthead, a
headline strip, a numbers strip, three lead stories with painted scenes,
ten picture panels, a world map with thirteen numbered pins, and twenty-two
more stories in two columns - 35 stories from 7 regions, every one first
reported on 24 November 2026.

Run:  python3 main.py
Writes: output/entry.png (1024 x 1024, deterministic PNG).
Set MAKEFUN_OUTPUT_DIR to choose another output directory.
"""

import hashlib
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (244, 236, 214)   # newsprint cream
PAPER_D = (232, 222, 194)  # darker cream for panels
INK = (18, 18, 18)        # near-black ink
RED = (176, 28, 34)       # headline red
RED_D = (140, 18, 24)
NAVY = (27, 42, 82)
BLUE = (52, 96, 158)
SKY = (178, 208, 224)     # sea on the map
LAND = (106, 143, 90)     # land on the map
LAND_D = (84, 118, 70)
GREEN = (46, 125, 50)
GOLD = (212, 160, 32)
ORANGE = (224, 110, 32)
GREY = (120, 120, 116)
GREY_L = (200, 200, 192)
WHITE = (250, 250, 246)


class Canvas:
    """A plain RGB pixel buffer with small drawing primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg[0] for _ in range(w * h * 3))
        # fill properly (bytearray trick above only sets one channel pattern)
        buf = bytearray(w * h * 3)
        for i in range(w * h):
            buf[i * 3] = bg[0]
            buf[i * 3 + 1] = bg[1]
            buf[i * 3 + 2] = bg[2]
        self.px = buf

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def get(self, x, y):
        i = (y * self.w + x) * 3
        return (self.px[i], self.px[i + 1], self.px[i + 2])

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def frame(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx, cy, r, c, t=1):
        for yy in range(cy - r - 1, cy + r + 2):
            for xx in range(cx - r - 1, cx + r + 2):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - t) ** 2 <= d <= r * r:
                    self.set(xx, yy, c)

    def tri(self, ax, ay, bx, by, cx, cy, c):
        """Filled triangle via scanline interpolation."""
        pts = sorted([(ax, ay), (bx, by), (cx, cy)], key=lambda p: p[1])
        (x0, y0), (x1, y1), (x2, y2) = pts
        if y0 == y2:
            return
        for y in range(y0, y2 + 1):
            if y < y1:
                xa = x0 + (x1 - x0) * (y - y0) / max(1, (y1 - y0))
                xb = x0 + (x2 - x0) * (y - y0) / max(1, (y2 - y0))
            else:
                xa = x1 + (x2 - x1) * (y - y1) / max(1, (y2 - y1))
                xb = x0 + (x2 - x0) * (y - y0) / max(1, (y2 - y0))
            lo, hi = sorted([int(round(xa)), int(round(xb))])
            self.rect(lo, y, hi - lo + 1, 1, c)

    def poly(self, pts, c):
        """Filled polygon (convex-ish) via scanline fill."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            if len(xs) >= 2:
                xs.sort()
                self.rect(int(round(xs[0])), y,
                          int(round(xs[-1])) - int(round(xs[0])) + 1, 1, c)


def png_bytes(canvas):
    """Encode the canvas as a PNG (filter 0, zlib level 9)."""
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ------------------------------------------------------------------- font
# Hand-built 5x7 all-caps bitmap font. Each glyph is 7 rows of 5 bits.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "=": ("00000", "00000", "01110", "00000", "01110", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "\u2014": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "\u2019": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "\u00b0": ("01100", "10010", "10010", "01100", "00000", "00000", "00000"),
    "\u00d7": ("00000", "10001", "01010", "00100", "01010", "10001", "00000"),
}

CHAR_W = 6  # 5 pixels + 1 pixel gap, times scale


def text_w(s, scale):
    return len(s) * CHAR_W * scale - scale


def draw_text(c, x, y, s, scale, color):
    """Draw uppercase text (lowercase is uppercased) at scale."""
    s = s.upper()
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT["?"])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    c.rect(cx + col * scale, y + row * scale,
                           scale, scale, color)
        cx += CHAR_W * scale
    return cx


def text_center(c, cx, y, s, scale, color):
    draw_text(c, cx - text_w(s, scale) // 2, y, s, scale, color)


def wrap(s, width, scale):
    """Greedy word wrap; returns list of lines fitting pixel width."""
    max_chars = max(1, width // (CHAR_W * scale))
    words = s.upper().split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            # hard-split a word longer than the line
            while len(w) > max_chars:
                lines.append(w[:max_chars])
                w = w[max_chars:]
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_para(c, x, y, w, s, scale, color, leading=None):
    """Draw a wrapped paragraph; returns y just below the last line."""
    lh = leading if leading is not None else 7 * scale + 3
    for line in wrap(s, w, scale):
        draw_text(c, x, y, line, scale, color)
        y += lh
    return y


# ------------------------------------------------------------- lead scenes
def scene_nvidia(c, x, y, w, h):
    """A chip on a dark board, its price line rocketing upward."""
    c.rect(x, y, w, h, (16, 22, 44))
    # circuit traces
    for i in range(6):
        yy = y + 8 + i * 16
        c.hline(x + 6, yy, w - 12, (38, 52, 96))
        c.disc(x + 6, yy, 2, GOLD)
        c.disc(x + w - 7, yy, 2, GOLD)
    # the chip
    cx, cy = x + w // 2 - 38, y + 26
    c.rect(cx - 8, cy + 10, 10, 3, GOLD)
    c.rect(cx + 56, cy + 10, 10, 3, GOLD)
    c.rect(cx - 8, cy + 34, 10, 3, GOLD)
    c.rect(cx + 56, cy + 34, 10, 3, GOLD)
    c.rect(cx, cy, 56, 56, (22, 90, 44))
    c.frame(cx, cy, 56, 56, GOLD, 2)
    c.rect(cx + 14, cy + 14, 28, 28, (30, 120, 60))
    draw_text(c, cx + 18, cy + 21, "NV", 2, WHITE)
    # rising price line, green, with an arrowhead
    pts = [(x + 8, y + h - 14), (x + 40, y + h - 30), (x + 70, y + h - 26),
           (x + 105, y + h - 52), (x + 140, y + h - 44), (x + 175, y + h - 74),
           (x + 215, y + h - 66), (x + 250, y + h - 96), (x + w - 10, y + 12)]
    for a, b in zip(pts, pts[1:]):
        c.line(a[0], a[1], b[0], b[1], (74, 222, 128))
        c.line(a[0], a[1] + 1, b[0], b[1] + 1, (74, 222, 128))
    for px, py in pts[1:-1]:
        c.disc(px, py, 3, (74, 222, 128))
    c.tri(x + w - 22, y + 8, x + w - 6, y + 10, x + w - 14, y + 24, (74, 222, 128))


def scene_dymer(c, x, y, w, h):
    """Night over a shelled apartment block: a drone, smoke, one lit window."""
    c.rect(x, y, w, h, (12, 16, 38))
    for sx, sy in [(20, 12), (60, 26), (120, 8), (200, 20), (260, 10), (300, 30)]:
        c.disc(x + sx, y + sy, 1, WHITE)
    c.disc(x + w - 40, y + 18, 12, (232, 226, 196))
    # apartment block, left half collapsed
    bx, by = x + 24, y + 36
    c.rect(bx, by, 120, 56, (74, 74, 84))
    c.rect(bx + 120, by + 22, 56, 34, (58, 58, 66))
    c.tri(bx + 96, by, bx + 120, by, bx + 120, by + 22, (58, 58, 66))
    for wy in range(by + 8, by + 48, 16):
        for wx in range(bx + 8, bx + 108, 20):
            c.rect(wx, wy, 10, 11, (16, 16, 22))
    c.rect(bx + 28, by + 24, 10, 11, GOLD)  # lit windows
    c.rect(bx + 68, by + 8, 10, 11, GOLD)
    # rubble
    c.tri(bx + 120, y + h - 2, bx + 168, y + h - 2, bx + 148, y + h - 26, GREY)
    c.tri(bx + 148, y + h - 2, bx + 196, y + h - 2, bx + 176, y + h - 18, (90, 90, 96))
    # drone with blinking lights
    dx, dy = x + w - 78, y + 28
    c.rect(dx - 16, dy, 32, 3, INK)
    c.rect(dx - 2, dy - 8, 4, 18, INK)
    c.disc(dx - 16, dy, 4, GREY_L)
    c.disc(dx + 16, dy, 4, GREY_L)
    c.disc(dx, dy, 5, RED)
    # smoke columns, kept inside the scene
    for sx, sy, r in [(bx + 56, y + 16, 10), (bx + 88, y + 10, 10),
                      (bx + 120, y + 18, 9)]:
        c.disc(sx, sy, r, (150, 150, 148))
        c.disc(sx + 5, sy - 3, r - 4, (170, 170, 166))
    # searchlight beam
    c.line(x + 30, y + h, x + 150, y + 20, (240, 230, 170))
    c.line(x + 34, y + h, x + 154, y + 20, (240, 230, 170))


def scene_cop(c, x, y, w, h):
    """A cracked globe above empty negotiation chairs."""
    c.rect(x, y, w, h, (24, 38, 66))
    for sx, sy in [(16, 10), (90, 22), (180, 8), (250, 26), (300, 12)]:
        c.disc(x + sx, y + sy, 1, WHITE)
    cx, cy, r = x + w // 2, y + 26, 24
    c.disc(cx, cy, r, (64, 130, 196))
    # continents as blobs
    c.disc(cx - 13, cy - 9, 7, GREEN)
    c.disc(cx - 4, cy - 13, 6, GREEN)
    c.disc(cx + 9, cy + 3, 8, GREEN)
    c.disc(cx + 13, cy + 13, 5, GREEN)
    c.disc(cx - 15, cy + 9, 5, GREEN)
    c.ring(cx, cy, r, WHITE, 2)
    # the crack: a red zigzag splitting the globe
    crack = [(cx - 3, cy - r + 1), (cx + 5, cy - 13), (cx - 2, cy - 3),
             (cx + 6, cy + 7), (cx - 3, cy + 16), (cx + 2, cy + r - 1)]
    for a, b in zip(crack, crack[1:]):
        c.line(a[0], a[1], b[0], b[1], RED)
        c.line(a[0] + 1, a[1], b[0] + 1, b[1], RED)
    # empty chairs row at the bottom
    for i in range(5):
        chx = x + 28 + i * 56
        c.rect(chx + 4, y + h - 38, 26, 12, (150, 112, 52))
        c.rect(chx, y + h - 26, 34, 4, (120, 90, 40))
        c.rect(chx + 4, y + h - 22, 4, 18, (120, 90, 40))
        c.rect(chx + 26, y + h - 22, 4, 18, (120, 90, 40))


# ------------------------------------------------------------ small scenes
def scene_fire(c, x, y, w, h):
    """Factory fire: orange sky, black sheds, flame triangles, smoke."""
    for i in range(h):
        t = i / max(1, h - 1)
        col = (int(240 - 90 * t), int(140 - 40 * t), int(40 + 40 * t))
        c.hline(x, y + i, w, col)
    c.rect(x, y + h - 34, w, 34, (30, 26, 24))
    c.rect(x + 14, y + h - 58, 60, 26, (44, 38, 34))
    c.rect(x + 96, y + h - 48, 44, 16, (44, 38, 34))
    c.rect(x + 150, y + h - 62, 10, 30, (44, 38, 34))
    for fx in (30, 62, 96, 132, 168):
        c.tri(x + fx, y + h - 34, x + fx + 18, y + h - 34,
              x + fx + 9, y + h - 66, (255, 190, 40))
        c.tri(x + fx + 5, y + h - 34, x + fx + 14, y + h - 34,
              x + fx + 9, y + h - 50, (255, 90, 20))
    for sx, sy, r in [(50, y + 12, 10), (80, y + 6, 13), (140, y + 10, 11)]:
        c.disc(x + sx, sy, r, (70, 66, 62))


def scene_tanker(c, x, y, w, h):
    """A tanker on a burning sea under missile streaks."""
    c.rect(x, y, w, h // 2, (22, 34, 66))
    for sx, sy in [(14, 8), (70, 18), (150, 10), (190, 22)]:
        c.disc(x + sx, y + sy, 1, WHITE)
    c.rect(x, y + h // 2, w, h // 2, (18, 64, 110))
    for i in range(4):
        c.hline(x, y + h // 2 + 8 + i * 10, w, (40, 96, 150))
    # tanker hull + bridge
    c.rect(x + 30, y + h - 44, 140, 20, (60, 58, 54))
    c.rect(x + 140, y + h - 66, 26, 24, (210, 210, 205))
    c.rect(x + 40, y + h - 56, 90, 12, RED_D)
    c.line(x + 20, y + 12, x + 90, y + h - 40, ORANGE)
    c.line(x + 24, y + 12, x + 94, y + h - 40, ORANGE)
    c.tri(x + 84, y + h - 44, x + 104, y + h - 44, x + 94, y + h - 64, GOLD)
    c.tri(x + 118, y + h - 44, x + 136, y + h - 44, x + 127, y + h - 58, (255, 120, 30))


def scene_robot(c, x, y, w, h):
    """A grey robot head over a UN-blue floor, its eyes crossed out."""
    c.rect(x, y, w, h, (36, 52, 96))
    c.rect(x, y + h - 24, w, 24, (22, 34, 66))
    c.rect(x + w // 2 - 44, y + 8, 88, 44, (188, 192, 196))
    c.frame(x + w // 2 - 44, y + 8, 88, 44, GREY, 2)
    c.rect(x + w // 2 - 40, y + 2, 16, 6, (160, 164, 168))
    c.rect(x + w // 2 + 24, y + 2, 16, 6, (160, 164, 168))
    c.rect(x + w // 2 - 26, y + 22, 16, 10, (20, 20, 26))
    c.rect(x + w // 2 + 10, y + 22, 16, 10, (20, 20, 26))
    c.line(x + w // 2 - 26, y + 22, x + w // 2 - 10, y + 32, RED)
    c.line(x + w // 2 - 10, y + 22, x + w // 2 - 26, y + 32, RED)
    c.line(x + w // 2 + 10, y + 22, x + w // 2 + 26, y + 32, RED)
    c.line(x + w // 2 + 26, y + 22, x + w // 2 + 10, y + 32, RED)
    c.rect(x + w // 2 - 18, y + 42, 36, 3, (20, 20, 26))
    for i in range(7):
        c.disc(x + 16 + i * 26, y + h - 12, 3, WHITE)


def scene_gavel(c, x, y, w, h):
    """A judge's gavel over a dark-red flag band."""
    c.rect(x, y, w, h, (66, 26, 30))
    c.rect(x, y + h - 30, w, 30, (24, 24, 24))
    c.rect(x, y, w, 10, GOLD)
    # gavel head + handle, diagonal
    c.line(x + 60, y + 18, x + 150, y + 62, (150, 112, 52))
    c.line(x + 60, y + 22, x + 150, y + 66, (150, 112, 52))
    c.line(x + 62, y + 20, x + 152, y + 64, (150, 112, 52))
    c.rect(x + 48, y + 8, 44, 22, (120, 90, 40))
    c.frame(x + 48, y + 8, 44, 22, (90, 66, 28), 2)
    c.rect(x + 148, y + 60, 26, 10, (120, 90, 40))
    # scales of justice, small, bottom right
    c.line(x + 168, y + h - 28, x + 168, y + h - 58, GOLD)
    c.line(x + 148, y + h - 54, x + 188, y + h - 54, GOLD)
    c.tri(x + 146, y + h - 54, x + 158, y + h - 54, x + 152, y + h - 40, GOLD)
    c.tri(x + 178, y + h - 54, x + 190, y + h - 54, x + 184, y + h - 40, GOLD)


def scene_school(c, x, y, w, h):
    """A school block with a warning envelope flying overhead."""
    c.rect(x, y, w, h, (150, 190, 220))
    c.disc(x + w - 30, y + 16, 12, (255, 240, 170))
    c.rect(x + 20, y + h - 56, 120, 56, (190, 120, 90))
    c.rect(x + 20, y + h - 70, 120, 14, (150, 80, 60))
    c.rect(x + 146, y + h - 40, 34, 40, (160, 96, 70))
    for wy in range(y + h - 50, y + h - 8, 14):
        for wx in range(x + 30, x + 128, 20):
            c.rect(wx, wy, 10, 9, (240, 240, 230))
    # flagpole + flag
    c.line(x + 80, y + h - 70, x + 80, y + 16, INK)
    c.tri(x + 80, y + 16, x + 112, y + 24, x + 80, y + 32, RED)
    # envelope with a red "!"
    ex, ey = x + w - 62, y + 34
    c.rect(ex, ey, 44, 30, WHITE)
    c.frame(ex, ey, 44, 30, INK, 2)
    c.line(ex, ey, ex + 22, ey + 16, INK)
    c.line(ex + 44, ey, ex + 22, ey + 16, INK)
    draw_text(c, ex + 18, ey + 14, "!", 1, RED)


def scene_chess(c, x, y, w, h):
    """An 8x8 board seen from the side, two kings facing off."""
    c.rect(x, y, w, h, (40, 44, 60))
    bs, ox, oy = 7, x + (w - 56) // 2, y + 4
    for r in range(8):
        for col in range(8):
            colr = (238, 232, 214) if (r + col) % 2 == 0 else (30, 30, 34)
            c.rect(ox + col * bs, oy + r * bs, bs, bs, colr)
    c.frame(ox, oy, 56, 56, GOLD, 2)
    # white king, left; black king, right
    for kx, colr in [(ox + 11, WHITE), (ox + 45, INK)]:
        c.rect(kx - 5, oy + 16, 10, 8, colr)
        c.rect(kx - 3, oy + 10, 6, 7, colr)
        c.rect(kx - 1, oy + 6, 2, 5, colr)
        c.rect(kx - 7, oy + 24, 14, 3, colr)
    c.rect(x, y + h - 4, w, 4, (24, 28, 44))


def scene_plane(c, x, y, w, h):
    """A grounded jet under a control tower, Thanksgiving dusk."""
    for i in range(h):
        t = i / max(1, h - 1)
        c.hline(x, y + i, w, (int(250 - 60 * t), int(190 - 40 * t), int(120 + 40 * t)))
    # control tower
    c.rect(x + w - 44, y + 10, 16, h - 40, (90, 90, 92))
    c.rect(x + w - 52, y + 6, 32, 14, (60, 90, 140))
    c.rect(x + w - 50, y + 8, 28, 10, (180, 220, 240))
    # runway
    c.rect(x, y + h - 18, w, 18, (40, 40, 44))
    for i in range(8):
        c.rect(x + 8 + i * 24, y + h - 10, 12, 3, GOLD)
    # jet silhouette
    c.rect(x + 24, y + h - 44, 110, 14, (250, 250, 246))
    c.tri(x + 134, y + h - 44, x + 164, y + h - 37, x + 134, y + h - 30, (250, 250, 246))
    c.tri(x + 60, y + h - 44, x + 78, y + h - 62, x + 92, y + h - 44, (220, 220, 214))
    c.tri(x + 100, y + h - 44, x + 118, y + h - 62, x + 126, y + h - 44, (220, 220, 214))
    for wx in range(36, 124, 12):
        c.rect(x + wx, y + h - 42, 6, 5, NAVY)
    # a small "STOP" sign
    c.disc(x + 170, y + h - 40, 12, RED)
    c.frame(x + 170 - 12, y + h - 52, 24, 24, WHITE, 1)


def scene_smog(c, x, y, w, h):
    """A smog-choked skyline: grey bands, a dim sun, tower blocks."""
    c.rect(x, y, w, h, (168, 158, 138))
    c.disc(x + w - 44, y + 22, 16, (226, 200, 130))
    c.rect(x + 16, y + h - 66, 30, 66, (96, 92, 86))
    c.rect(x + 52, y + h - 88, 34, 88, (80, 76, 70))
    c.rect(x + 92, y + h - 56, 26, 56, (104, 100, 94))
    c.rect(x + 124, y + h - 76, 30, 76, (88, 84, 78))
    c.rect(x + 160, y + h - 60, 26, 60, (100, 96, 90))
    for bx, bw in [(16, 30), (52, 34), (92, 26), (124, 30), (160, 26)]:
        for wy in range(y + h - 60, y + h - 6, 12):
            c.rect(x + bx + 5, wy, 6, 6, (200, 196, 180))
    c.rect(x, y + 52, w, 10, (150, 142, 122))
    c.rect(x, y + 84, w, 8, (140, 132, 114))
    draw_text(c, x + 8, y + h - 20, "AQI 500+", 1, (90, 30, 30))


def scene_moon(c, x, y, w, h):
    """A supermoon and the Pleiades cluster on a black sky."""
    c.rect(x, y, w, h, (8, 10, 26))
    for sx, sy in [(12, 60), (30, 20), (70, 70), (120, 14), (150, 60),
                   (180, 24), (40, 88), (100, 92)]:
        c.disc(x + sx, y + sy, 1, WHITE)
    c.disc(x + 52, y + 32, 20, (238, 232, 210))
    c.disc(x + 46, y + 27, 4, (210, 204, 182))
    c.disc(x + 60, y + 38, 3, (210, 204, 182))
    c.disc(x + 56, y + 22, 2, (210, 204, 182))
    # Pleiades: seven small stars in a dipper-ish cluster
    for sx, sy, r in [(140, 26, 2), (152, 20, 3), (164, 26, 2), (158, 36, 2),
                      (146, 38, 2), (172, 36, 2), (166, 48, 2)]:
        c.disc(x + sx, y + sy, r, (200, 220, 255))
    c.line(x + 140, y + 26, x + 172, y + 36, (120, 140, 180))
    c.line(x + 152, y + 20, x + 158, y + 36, (120, 140, 180))
    c.rect(x, y + h - 6, w, 6, (20, 24, 40))


def scene_seoul(c, x, y, w, h):
    """Seoul at dusk: tower, flags, and a new minister's podium."""
    for i in range(h):
        t = i / max(1, h - 1)
        c.hline(x, y + i, w, (int(60 + 120 * t), int(70 + 60 * t), int(140 - 60 * t)))
    # N Seoul Tower
    c.rect(x + w // 2 - 4, y + 8, 8, 60, (200, 200, 196))
    c.disc(x + w // 2, y + 12, 12, (220, 220, 214))
    c.disc(x + w // 2, y + 12, 6, (255, 200, 60))
    c.rect(x + w // 2 - 30, y + 66, 60, 8, (180, 180, 176))
    # skyline
    for bx, bh, bw in [(10, 46, 26), (44, 62, 30), (82, 40, 24),
                       (140, 58, 30), (176, 44, 24)]:
        c.rect(x + bx, y + h - bh, bw, bh, (30, 32, 52))
        for wy in range(y + h - bh + 8, y + h - 6, 12):
            c.rect(x + bx + 5, wy, 5, 5, GOLD)
    # two flags on poles
    for fx in (120, 150):
        c.line(x + fx, y + h - 30, x + fx, y + h - 62, INK)
        c.tri(x + fx, y + h - 62, x + fx + 24, y + h - 56, x + fx, y + h - 50,
              RED if fx == 120 else BLUE)


# ------------------------------------------------------------------- map
# Coarse continent outlines in (lon, lat); drawn equirectangular.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-120, 71), (-100, 72), (-85, 70), (-75, 72),
     (-65, 62), (-55, 52), (-60, 47), (-70, 42), (-75, 35), (-80, 26),
     (-85, 30), (-90, 21), (-97, 16), (-105, 20), (-115, 28), (-125, 40),
     (-125, 49), (-140, 60), (-155, 58), (-168, 66)],
    [(-58, 64), (-45, 60), (-30, 68), (-20, 70), (-35, 76), (-55, 76),
     (-58, 64)],
    [(-80, 10), (-75, 10), (-62, 10), (-52, 5), (-35, -8), (-40, -20),
     (-48, -28), (-58, -35), (-65, -41), (-70, -50), (-73, -53), (-70, -40),
     (-72, -20), (-80, -5), (-80, 10)],
    [(-10, 36), (-9, 43), (-2, 48), (0, 50), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (24, 58), (30, 60), (30, 66), (25, 70), (18, 69),
     (12, 65), (5, 60), (-5, 58), (-10, 50), (-10, 36)],
    [(-17, 15), (-15, 27), (-5, 35), (10, 37), (20, 32), (32, 31), (35, 28),
     (43, 12), (51, 11), (48, 0), (40, -10), (35, -20), (30, -29), (20, -35),
     (15, -30), (12, -18), (9, -5), (9, 4), (-8, 5), (-17, 15)],
    [(30, 66), (40, 68), (60, 70), (80, 73), (100, 76), (120, 73),
     (140, 72), (160, 70), (178, 66), (170, 60), (162, 56), (158, 52),
     (142, 50), (140, 40), (130, 35), (127, 40), (120, 32), (110, 20),
     (105, 10), (100, 8), (95, 15), (90, 22), (80, 15), (75, 8), (70, 20),
     (60, 25), (55, 26), (50, 30), (45, 30), (40, 35), (35, 36), (30, 36),
     (30, 42), (30, 66)],
    [(130, 31), (133, 34), (137, 35), (140, 38), (142, 42), (144, 44),
     (141, 45), (140, 40), (137, 37), (132, 33), (130, 31)],
    [(113, -22), (114, -30), (115, -35), (125, -32), (130, -32), (135, -35),
     (140, -38), (145, -38), (150, -37), (153, -32), (150, -25), (146, -20),
     (142, -15), (142, -11), (137, -12), (135, -15), (130, -13), (126, -14),
     (122, -17), (118, -20), (113, -22)],
    [(-5, 50), (-3, 53), (-5, 56), (-2, 58), (0, 53), (-5, 50)],
]

# (number, lon, lat) - one pin per numbered story on this page.
PINS = [
    (1, -122, 37), (2, 35, 55), (3, 28, 35), (4, 51, 26), (5, 110, -7),
    (6, 4, 47), (7, 15, 54), (8, 96, 20), (9, 74, 32), (10, 127, 38),
    (11, 23, 30), (12, -7, 53), (13, -88, 42),
]


def draw_map(c, x, y, w, h):
    c.rect(x, y, w, h, SKY)
    # graticule
    for gx in range(1, 12):
        c.vline(x + gx * w // 12, y, h, (150, 185, 205))
    for gy in range(1, 6):
        c.hline(x, y + gy * h // 6, w, (150, 185, 205))
    for poly in CONTINENTS:
        pts = [(x + int((lon + 180) / 360 * w),
                y + int((90 - lat) / 180 * h)) for lon, lat in poly]
        c.poly(pts, LAND)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            c.line(a[0], a[1], b[0], b[1], LAND_D)
    # pins: red disc, white ring, number
    for num, lon, lat in PINS:
        px = x + int((lon + 180) / 360 * w)
        py = y + int((90 - lat) / 180 * h)
        c.disc(px, py, 9, RED)
        c.ring(px, py, 9, WHITE, 2)
        label = str(num)
        draw_text(c, px - text_w(label, 1) // 2, py - 3, label, 1, WHITE)


# ------------------------------------------------------------------- data
NUMBERS = [
    ("+31%", "NVIDIA'S DAY"),
    ("11", "DEAD IN DYMER"),
    ("24", "DEAD IN JAVA FIRE"),
    ("700,000", "RUSSIAN DEAD"),
    ("450", "SCHOOLS THREATENED"),
    ("$952BN", "NVIDIA GAINED"),
]

LEADS = [
    dict(num="01", tag="HUANG RETURNS", scene=scene_nvidia,
         head="HUANG IS BACK, WALL ST ROARS",
         body=("NVIDIA +31% IN A DAY, ITS BEST SINCE 2003, AS HUANG "
               "CAME BACK."),
         src="CNN, REUTERS"),
    dict(num="02", tag="DYMER: 11 DEAD", scene=scene_dymer,
         head="KYIV BRACES AS TOLL RISES",
         body=("AN 11TH BODY WAS FOUND IN DYMER. KYIV ASKS ALLIES "
               "FOR PATRIOTS."),
         src="RFE/RL, AP"),
    dict(num="03", tag="COP31 FALLOUT", scene=scene_cop,
         head="AFTER THE COLLAPSE, NO PLAN B",
         body=("ERDOGAN: THE TALKS LAID GROUNDWORK. THE EU HAD "
               "REFUSED A WEAK TEXT."),
         src="REUTERS, CNN"),
]

PANELS = [
    dict(num="04", tag="JAVA FIRE", scene=scene_fire,
         head="FACTORY FIRE: 24 DEAD, MORE MISSING",
         src="NYT, AFP"),
    dict(num="05", tag="GULF WAR", scene=scene_tanker,
         head="IRAN THREATENS EU BASES WITH MISSILES",
         src="BBC, AFP"),
    dict(num="06", tag="KILLER ROBOTS", scene=scene_robot,
         head="UN TALKS ON LETHAL AI END WITH NO PACT",
         src="AP"),
    dict(num="07", tag="MYANMAR", scene=scene_gavel,
         head="UK SANCTIONS GENERALS AFTER ROHINGYA RULING",
         src="BBC"),
    dict(num="08", tag="GERMANY", scene=scene_school,
         head="450 SCHOOLS GET BOMB THREATS BY EMAIL",
         src="TOI, AFP"),
    dict(num="09", tag="CHESS", scene=scene_chess,
         head="GUKESH DEFENDS CROWN IN GENEVA",
         src="CHESS.COM"),
    dict(num="10", tag="O'HARE", scene=scene_plane,
         head="GROUND STOP IN THANKSGIVING RUSH",
         src="TOI"),
    dict(num="11", tag="LAHORE SMOG", scene=scene_smog,
         head="WORLD'S WORST AIR: AQI PAST 500",
         src="TOI"),
    dict(num="12", tag="SUPERMOON", scene=scene_moon,
         head="SUPERMOON MEETS THE SEVEN SISTERS",
         src="FORBES"),
    dict(num="13", tag="SEOUL", scene=scene_seoul,
         head="NEW MINISTERS, FIRST WOMAN SPY CHIEF",
         src="AFP"),
]

MORE = [
    ("14", "TRUMP: PENALISE FIRMS BUILDING DATA CENTRES ABROAD", "AFP"),
    ("15", "CROWDSTRIKE BUYS ZSCALER IN $44BN CYBER DEAL", "REUTERS"),
    ("16", "CATHERINE SPEAKS OF 'MORTALITY' IN NEW FILM CLIP", "BBC"),
    ("17", "KING CHARLES REACHES OUT TO MEGHAN MARKLE", "TOI"),
    ("18", "DUTCH ACTIVIST DIES BY EUTHANASIA AT 28", "TOI"),
    ("19", "PELICOT 'SHOCKED' AS NUDE IMAGES SELL A BOOK", "GUARDIAN"),
    ("20", "NETANYAHU WANTS TO HIT IRAN. DOES IT SERVE HIM?", "NYT"),
    ("21", "DRONE ATTACK HITS A COLOMBIAN CITY", "GUARDIAN"),
    ("22", "IRAN FLOGS SINGER WHO SANG WITHOUT HIJAB", "GUARDIAN"),
    ("23", "TRUMP IMPERSONATOR MOCKS HIM AT CANADA DINNER", "GUARDIAN"),
    ("24", "BRAZIL REAL SLIDES PAST 6.00 TO THE DOLLAR", "REUTERS"),
    ("25", "INDIA, CHINA HOLD MILITARY TALKS IN ARUNACHAL", "TOI"),
    ("26", "MODI OPENS AI CENTRE AT IIT PATNA", "TOI"),
    ("27", "4.0 QUAKE STRIKES PAKISTAN NEAR AFGHAN BORDER", "TOI"),
    ("28", "YUNUS: SOMEONE DIRECTING ATTACKS ON GRAMEEN BANK", "TOI"),
    ("29", "INDIA V NEW ZEALAND FIRST TEST ENDS IN A DRAW", "TOI"),
    ("30", "SOUTH AFRICA'S FIRST WOMAN DEPUTY PRESIDENT DIES", "NYT"),
    ("31", "ASIA RALLIES ON HUANG: KOSPI +6.3%, NIKKEI +3%", "REUTERS"),
    ("32", "TAIWAN CURBS SHORT-SELLING AFTER MARKET ROUT", "REUTERS"),
    ("33", "THAILAND TO BAN MINING CHEMICALS TO MYANMAR", "AFP"),
    ("34", "CYPRUS EXPELS TWO DIPLOMATS OVER SPYING", "AFP"),
    ("35", "KIM JONG UN RECEIVES ENVOYS' CREDENTIALS", "TOI"),
]


# ------------------------------------------------------------------ layout
def build_page():
    c = Canvas(W, H, PAPER)

    # ---- masthead
    text_center(c, W // 2, 8, "THE WORLD TODAY", 7, INK)
    c.hline(12, 60, W - 24, RED)
    draw_text(c, 12, 66, "TUESDAY, 24 NOVEMBER 2026", 2, INK)
    counts = "AMERICAS 7 - EUROPE 8 - ASIA 12 - MIDDLE EAST 4 - AFRICA 1 - OCEANIA 1 - GLOBAL 2"
    draw_text(c, W - 12 - text_w(counts, 1), 68, counts, 1, GREY)
    c.hline(12, 86, W - 24, INK)

    # ---- headline strip
    text_center(c, W // 2, 94, "HUANG IS BACK - NVIDIA +31% - KYIV BRACES", 3, RED)
    c.hline(12, 122, W - 24, RED)

    # ---- numbers strip: six boxes
    n_w, n_gap, n_y, n_h = 166, 4, 128, 46
    for i, (num, cap) in enumerate(NUMBERS):
        bx = 4 + i * (n_w + n_gap)
        c.frame(bx, n_y, n_w, n_h, INK, 2)
        text_center(c, bx + n_w // 2, n_y + 5, num, 3, NAVY)
        text_center(c, bx + n_w // 2, n_y + 31, cap, 1, INK)
    c.hline(12, 180, W - 24, INK)

    # ---- three lead stories
    lead_y, lead_h, lead_w, lead_gap = 186, 222, 328, 8
    for i, lead in enumerate(LEADS):
        px = 12 + i * (lead_w + lead_gap)
        py = lead_y
        c.frame(px, py, lead_w, lead_h, INK, 2)
        lead["scene"](c, px + 2, py + 2, lead_w - 4, 92)
        c.rect(px + 2, py + 94, lead_w - 4, 20, RED)
        draw_text(c, px + 10, py + 99, lead["tag"], 2, WHITE)
        draw_text(c, px + lead_w - 10 - text_w(lead["num"], 2), py + 99,
                  lead["num"], 2, WHITE)
        # headline: two lines, scale 2
        hl = wrap(lead["head"], lead_w - 16, 2)[:2]
        hy = py + 120
        for line in hl:
            draw_text(c, px + 8, hy, line, 2, INK)
            hy += 17
        # body: three lines, scale 2
        bl = wrap(lead["body"], lead_w - 16, 2)[:3]
        by = py + 156
        for line in bl:
            draw_text(c, px + 8, by, line, 2, INK)
            by += 17
        draw_text(c, px + 8, py + lead_h - 12, lead["src"], 1, GREY)

    # ---- ten picture panels, two rows of five
    pan_w, pan_gap, pan_h = 196, 5, 136
    for row in range(2):
        for col in range(5):
            p = PANELS[row * 5 + col]
            px = 12 + col * (pan_w + pan_gap)
            py = 414 + row * (pan_h + 6)
            c.frame(px, py, pan_w, pan_h, INK, 2)
            p["scene"](c, px + 2, py + 2, pan_w - 4, 64)
            c.rect(px + 2, py + 66, pan_w - 4, 16, NAVY)
            draw_text(c, px + 6, py + 70, p["tag"], 1, WHITE)
            right = p["num"] + " " + p["src"]
            draw_text(c, px + pan_w - 6 - text_w(right, 1), py + 70,
                      right, 1, (200, 210, 235))
            hl = wrap(p["head"], pan_w - 12, 2)[:3]
            hy = py + 84
            for line in hl:
                draw_text(c, px + 6, hy, line, 2, INK)
                hy += 15

    # ---- world map with numbered pins
    draw_text(c, 12, 700, "WHERE IT HAPPENED - 13 PLACES", 2, INK)
    draw_text(c, W - 12 - text_w("EACH NUMBER IS THAT STORY ON THIS PAGE", 1),
              702, "EACH NUMBER IS THAT STORY ON THIS PAGE", 1, GREY)
    c.frame(12, 720, W - 24, 112, INK, 2)
    draw_map(c, 14, 722, W - 28, 108)
    c.hline(12, 838, W - 24, INK)

    # ---- twenty-two more stories, two columns
    draw_text(c, 12, 844, "ALSO ON TUESDAY 24 NOVEMBER - 22 MORE STORIES", 2, INK)
    c.hline(12, 864, W - 24, INK)
    for col in range(2):
        cx = 12 + col * 506
        for r in range(11):
            num, head, src = MORE[col * 11 + r]
            ry = 872 + r * 10
            x = cx
            x = draw_text(c, x, ry, num, 1, RED)
            x = draw_text(c, x + 6, ry, head, 1, INK)
            draw_text(c, x + 6, ry, "(" + src + ")", 1, GREY)
    c.hline(12, 986, W - 24, INK)

    # ---- footer: date check + sources
    draw_para(c, 12, 992, W - 24,
              "DATE CHECK - LEFT OUT AS NOT 24 NOVEMBER NEWS: COP31 COLLAPSE "
              "ITSELF (SUNDAY 22 NOV); ALCARAZ ATP FINALS WIN (SUNDAY); "
              "NVIDIA -14% (FRIDAY 20 NOV).", 1, GREY)
    draw_text(c, 12, 1012,
              "SOURCES: AFP, REUTERS, AP, BBC, CNN, NYT, THE HINDU, TIMES OF "
              "INDIA, GUARDIAN, FORBES, CHESS.COM.", 1, GREY)
    return c


def out_path():
    d = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not d:
        d = "/output" if os.path.isdir("/output") else os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "entry.png")


def main():
    canvas = build_page()
    data = png_bytes(canvas)
    path = out_path()
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, sha256 %s)"
          % (path, len(data), hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
