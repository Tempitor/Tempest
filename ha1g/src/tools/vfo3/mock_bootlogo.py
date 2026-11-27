# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Tempest boot-logo mockups (design only, no firmware code).
Every option is drawn ONLY from primitives cheap to do in firmware: row gradients, filled rects,
lines, filled polygons, circles/arcs, a per-pixel polar formula, and the radio's own stock fonts
(font.py/mock.py).  The big TEMPEST wordmark is a 5-glyph rectangle font (T E M P S) -> ~90 bytes.
All colours are quantised to RGB565 like the LCD.   usage: mock_bootlogo.py outdir"""
import sys, math, os
from PIL import Image, ImageDraw
from mock import text
from font import width
F8, F10, F16, F20 = 0x68918, 0x6a570, 0x6ba98, 0x6dab0
VER = 'V1.01.14.002 D022'

BLACK = (0, 0, 0); NAVY = (0, 12, 48); DEEP = (4, 24, 96); ROYAL = (36, 72, 220)
TEAL = (0, 184, 168); AQUA = (96, 240, 220); WHITE = (255, 255, 255); GREY = (120, 140, 160)

def q565(c): return (c[0] & 0xF8, c[1] & 0xFC, c[2] & 0xF8)
def mix(a, b, k): return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))

def vgrad(dr, y0, y1, c0, c1, x0=0, x1=159):
    for y in range(y0, y1 + 1):
        dr.line((x0, y, x1, y), fill=mix(c0, c1, (y - y0) / max(1, y1 - y0)))

# ---- block wordmark: 5 unique glyphs as rects (x0,y0,x1,y1) in a 16x22 cell, stroke 4 ----------
G = {'T': [(0, 0, 15, 3), (6, 0, 9, 21)],
     'E': [(0, 0, 3, 21), (0, 0, 15, 3), (0, 9, 12, 12), (0, 18, 15, 21)],
     'M': [(0, 0, 3, 21), (12, 0, 15, 21), (0, 0, 15, 3), (6, 0, 9, 13)],
     'P': [(0, 0, 3, 21), (0, 0, 15, 3), (12, 0, 15, 12), (0, 9, 15, 12)],
     'S': [(0, 0, 15, 3), (0, 0, 3, 12), (0, 9, 15, 12), (12, 9, 15, 21), (0, 18, 15, 21)]}
def word(im, x, y, s, col, sc=1.0, gap=4, slant=0, col2=None, shadow=None):
    """slant = px shift per 4 rows (italic); col2 = colour of bottom half (two-tone)."""
    dr = ImageDraw.Draw(im)
    for layer in ([(shadow, 2)] if shadow else []) + [(col, 0)]:
        c, off = layer; cx = x
        for ch in s:
            for (a, b, e, f) in G[ch]:
                for yy in range(int(b * sc), int((f + 1) * sc)):
                    sh = int(slant * (int(22 * sc) - yy) / 4)
                    cc = c if (col2 is None or c is shadow or yy < 11 * sc) else col2
                    dr.line((cx + int(a * sc) + sh + off, y + yy + off, cx + int((e + 1) * sc) - 1 + sh + off, y + yy + off), fill=cc)
            cx += int(16 * sc) + gap
    return cx - gap - x
def word_w(s, sc=1.0, gap=4): return len(s) * int(16 * sc) + (len(s) - 1) * gap

def ctext(im, f, y, s, col, cx=80): text(im, f, cx - width(f, s) // 2, y, s, col)

# ---------------------------------------------------------------------------------------------
def opt_a():   # STORM EYE: procedural hurricane spiral, black bg
    im = Image.new('RGB', (160, 128), BLACK); px = im.load()
    cx, cy, R = 80, 40, 37
    for y in range(128):
        for x in range(160):
            dx, dy = x - cx, (y - cy) * 1.0; r = math.hypot(dx, dy)
            if r > R or r < 4: continue
            th = math.atan2(dy, dx)
            v = math.sin(3 * th + 2.6 * math.log(r))            # 3 log-spiral arms
            if v > 0.25:
                k = r / R; px[x, y] = mix(AQUA, ROYAL, k) if v > 0.7 else mix(TEAL, DEEP, k)
    dr = ImageDraw.Draw(im); dr.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=WHITE)
    w = word_w('TEMPEST', 0.82, 3); word(im, 80 - w // 2, 82, 'TEMPEST', WHITE, 0.82, 3)
    ctext(im, F8, 105, 'F I R M W A R E', TEAL); ctext(im, F8, 120, VER, GREY)
    return im

def opt_b():   # BOLT: navy->black gradient, teal lightning polygon through the wordmark
    im = Image.new('RGB', (160, 128)); dr = ImageDraw.Draw(im)
    vgrad(dr, 0, 127, DEEP, BLACK)
    bolt = [(96, 4), (70, 50), (84, 50), (62, 96), (102, 40), (86, 40), (108, 4)]
    dr.polygon([(x + 2, y + 2) for x, y in bolt], fill=NAVY); dr.polygon(bolt, fill=TEAL)
    dr.line((96, 4, 70, 50), fill=AQUA); dr.line((84, 50, 62, 96), fill=AQUA)
    w = word_w('TEMPEST', 0.9, 3); word(im, 80 - w // 2, 60, 'TEMPEST', WHITE, 0.9, 3, shadow=BLACK)
    dr.rectangle((20, 86, 139, 86), fill=ROYAL)
    ctext(im, F10, 92, 'FIRMWARE', AQUA); ctext(im, F8, 118, VER, GREY)
    return im

def opt_c():   # SIGNAL: antenna mast with radiating teal arcs, wordmark under, royal band
    im = Image.new('RGB', (160, 128), BLACK); dr = ImageDraw.Draw(im)
    ax, ay = 80, 36
    for i, rr in enumerate((9, 15, 21, 27, 33)):
        c = mix(AQUA, DEEP, i / 4)
        for t in (0, 1):
            dr.arc((ax - rr - t, ay - rr - t, ax + rr + t, ay + rr + t), 200, 340, fill=c)
    dr.polygon([(80, 36), (73, 71), (87, 71)], outline=ROYAL); dr.line((80, 36, 80, 71), fill=ROYAL)
    dr.line((77, 54, 83, 54), fill=ROYAL); dr.ellipse((77, 33, 83, 39), fill=AQUA)
    vgrad(dr, 72, 101, DEEP, NAVY)
    w = word_w('TEMPEST', 0.86, 3); word(im, 80 - w // 2, 77, 'TEMPEST', WHITE, 0.86, 3)
    ctext(im, F10, 104, 'FIRMWARE', TEAL); ctext(im, F8, 119, VER, GREY)
    return im

def opt_d():   # WIND: minimal italic wordmark, two-tone, royal/teal speed lines
    im = Image.new('RGB', (160, 128), BLACK); dr = ImageDraw.Draw(im)
    for y, x0, x1, c in ((30, 8, 70, DEEP), (36, 30, 150, ROYAL), (42, 60, 152, DEEP),
                         (86, 6, 100, DEEP), (92, 20, 130, TEAL), (98, 70, 150, DEEP)):
        dr.rectangle((x0, y, x1, y + 1), fill=c)
    w = word_w('TEMPEST', 0.95, 2) + 5; word(im, 80 - w // 2 - 2, 52, 'TEMPEST', WHITE, 0.95, 2, slant=1, col2=AQUA)
    text(im, F10, 112, 104, 'FW', TEAL); dr.rectangle((108, 103, 130, 115), outline=TEAL)
    text(im, F8, 6, 118, 'D009', GREY)
    return im

def opt_e():   # SPECTRUM: waveform + band-scope bars ties to the radio's scope, black bg
    im = Image.new('RGB', (160, 128), BLACK); dr = ImageDraw.Draw(im)
    vgrad(dr, 0, 63, BLACK, NAVY)
    hs = [3, 4, 3, 5, 4, 6, 5, 8, 7, 11, 14, 20, 28, 36, 42, 36, 28, 20, 14, 11, 7, 8, 5, 6, 4, 5, 3, 4, 3]
    n = len(hs); bw = 5; x0 = 80 - (n * bw) // 2
    for i, h in enumerate(hs):
        top = 60 - h; mid = i == n // 2
        for y in range(top, 61):
            dr.line((x0 + i * bw, y, x0 + i * bw + bw - 2, y), fill=(AQUA if mid else mix(TEAL, ROYAL, (y - top) / max(1, 60 - top) * 0.2 + abs(i - n // 2) / n * 1.6 if True else 0)))
    pts = [(x, 66 + int(5 * math.sin(x / 7.0) * math.exp(-((x - 80) / 50.0) ** 2))) for x in range(8, 152)]
    dr.line(pts, fill=ROYAL)
    w = word_w('TEMPEST', 0.86, 3); word(im, 80 - w // 2, 78, 'TEMPEST', WHITE, 0.86, 3)
    ctext(im, F8, 102, 'FIRMWARE', TEAL); ctext(im, F8, 118, VER, GREY)
    return im

def opt_f():   # BADGE: royal-blue shield/diamond with teal T, wordmark right; compact
    im = Image.new('RGB', (160, 128), BLACK); dr = ImageDraw.Draw(im)
    vgrad(dr, 0, 127, BLACK, NAVY)
    cx, cy = 80, 42
    dia = [(cx, cy - 30), (cx + 30, cy), (cx, cy + 30), (cx - 30, cy)]
    dr.polygon(dia, fill=DEEP); dr.line(dia + [dia[0]], fill=ROYAL, width=1)
    inner = [(cx, cy - 25), (cx + 25, cy), (cx, cy + 25), (cx - 25, cy)]; dr.line(inner + [inner[0]], fill=TEAL)
    word(im, cx - 13, cy - 13, 'T', AQUA, 1.6, 0)
    w = word_w('TEMPEST', 0.82, 3); word(im, 80 - w // 2, 82, 'TEMPEST', WHITE, 0.82, 3)
    ctext(im, F8, 104, 'F I R M W A R E', TEAL); ctext(im, F8, 118, VER, GREY)
    return im

OPTS = [('A', 'Storm eye', opt_a, 'procedural 3-arm spiral (per-pixel polar formula)'),
        ('B', 'Lightning bolt', opt_b, 'gradient + 7-point polygon'),
        ('C', 'Signal mast', opt_c, 'arcs + small mast polygon + band gradient'),
        ('D', 'Wind / minimal', opt_d, 'italic two-tone wordmark + 6 speed lines'),
        ('E', 'Spectrum', opt_e, 'scope bars + damped sine line'),
        ('F', 'Diamond badge', opt_f, 'diamond polygons + large T glyph')]

if __name__ == '__main__':
    out = sys.argv[1]; S = 2; cols = 3
    sheet = Image.new('RGB', (cols * (160 * S + 24) + 24, 2 * (128 * S + 44) + 20), (40, 40, 40)); sd = ImageDraw.Draw(sheet)
    for k, (tag, name, fn, _) in enumerate(OPTS):
        im = fn(); im = Image.eval(im, lambda v: v)  # copy
        im = im.point(lambda v: v)  # keep
        px = im.load()
        for y in range(128):
            for x in range(160): px[x, y] = q565(px[x, y])
        base = os.path.join(out, f'tempest_logo_{tag}')
        im.save(base + '_1x.png'); im.resize((320, 256), Image.NEAREST).save(base + '_2x.png')
        im.resize((640, 512), Image.NEAREST).save(base + '_4x.png')
        X = 24 + (k % cols) * (160 * S + 24); Y = 36 + (k // cols) * (128 * S + 44)
        sheet.paste(im.resize((160 * S, 128 * S), Image.NEAREST), (X, Y))
        sd.text((X, Y - 18), f'{tag}  {name}', fill=(255, 255, 255))
    sheet.save(os.path.join(out, 'tempest_logo_options.png')); print('ok')
