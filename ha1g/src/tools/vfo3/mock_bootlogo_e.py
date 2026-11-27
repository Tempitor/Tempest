# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Tempest boot logo, option E (Spectrum) iterations. Design only, no firmware code.
E0 = original, E1 reflection, E2 peak caps + bars behind wordmark, E3 bars + waterfall strip, E4 scope frame.
usage: mock_bootlogo_e.py outdir"""
import sys, os, math, random
from PIL import Image, ImageDraw
from mock_bootlogo import (opt_e, word, word_w, ctext, vgrad, mix, q565, F8, F10, VER,
                           BLACK, NAVY, DEEP, ROYAL, TEAL, AQUA, WHITE, GREY)

HS = [3, 4, 3, 5, 4, 6, 5, 8, 7, 11, 14, 20, 28, 36, 42, 36, 28, 20, 14, 11, 7, 8, 5, 6, 4, 5, 3, 4, 3]

def bars(dr, base, hs=HS, bw=5, scale=1.0, mirror=0, cap=False, dim=1.0):
    n = len(hs); x0 = 80 - (n * bw) // 2; c = n // 2
    for i, h0 in enumerate(hs):
        h = int(h0 * scale); top = base - h; xa, xb = x0 + i * bw, x0 + i * bw + bw - 2
        for y in range(top, base + 1):
            k = (base - y) / max(1, h)                           # 0 bottom .. 1 top
            col = mix(ROYAL, AQUA if i == c else TEAL, k)
            dr.line((xa, y, xb, y), fill=mix(BLACK, col, dim))
        if cap: dr.line((xa, top - 3, xb, top - 3), fill=WHITE if i == c else AQUA)
        for j in range(1, mirror + 1):                            # reflection: every other row, fading
            if j % 2 or j > h * 0.6: continue
            dr.line((xa, base + j, xb, base + j), fill=mix(BLACK, mix(ROYAL, TEAL, 0.4) if i != c else AQUA, 0.75 * (1 - j / (mirror + 1))))

def e1():   # reflection on a "water line"
    im = Image.new('RGB', (160, 128), BLACK); dr = ImageDraw.Draw(im)
    vgrad(dr, 0, 50, BLACK, NAVY)
    bars(dr, 50, mirror=18); dr.line((8, 51, 151, 51), fill=ROYAL)
    w = word_w('TEMPEST', 0.86, 3); word(im, 80 - w // 2, 76, 'TEMPEST', WHITE, 0.86, 3)
    ctext(im, F8, 100, 'FIRMWARE', TEAL); ctext(im, F8, 118, VER, GREY)
    return im

def e2():   # tall dim bars behind the wordmark, peak-hold caps
    im = Image.new('RGB', (160, 128), BLACK); dr = ImageDraw.Draw(im)
    hs = [6, 8, 7, 10, 9, 12, 11, 15, 14, 20, 26, 34, 46, 60, 70, 60, 46, 34, 26, 20, 14, 15, 11, 12, 9, 10, 7, 8, 6]
    bars(dr, 92, hs, cap=True, dim=0.75)
    wx = 80 - word_w('TEMPEST', 0.86, 3) // 2
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (1, -1), (-1, 1)):
        word(im, wx + ox, 70 + oy, 'TEMPEST', BLACK, 0.86, 3)
    word(im, wx, 70, 'TEMPEST', WHITE, 0.86, 3)
    dr.line((8, 93, 151, 93), fill=ROYAL)
    ctext(im, F8, 100, 'FIRMWARE', TEAL); ctext(im, F8, 118, VER, GREY)
    return im

def e3():   # bars + small waterfall strip (ties to the waterfall feature)
    im = Image.new('RGB', (160, 128), BLACK); dr = ImageDraw.Draw(im)
    bars(dr, 40, scale=0.8)
    n = len(HS); x0 = 80 - (n * 5) // 2; random.seed(4)
    stops = [(0, BLACK), (0.35, DEEP), (0.65, ROYAL), (0.85, TEAL), (1.0, AQUA)]
    def pal(v):
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if v <= b: return mix(ca, cb, (v - a) / (b - a))
        return AQUA
    for r in range(22):
        for i, h in enumerate(HS):
            v = min(1, h / 26 * (0.75 + 0.25 * random.random()) + (0.25 if i == n // 2 and r % 7 < 4 else 0))
            dr.line((x0 + i * 5, 43 + r, x0 + i * 5 + 4, 43 + r), fill=pal(v * (1 - r / 60)))
    word(im, 80 - word_w('TEMPEST', 0.86, 3) // 2, 74, 'TEMPEST', WHITE, 0.86, 3)
    ctext(im, F8, 98, 'FIRMWARE', TEAL); ctext(im, F8, 118, VER, GREY)
    return im

def e4():   # scope frame: bezel, tick marks, centre marker, like the radio's Band Scope
    im = Image.new('RGB', (160, 128), BLACK); dr = ImageDraw.Draw(im)
    dr.rectangle((4, 4, 155, 60), outline=ROYAL); vgrad(dr, 5, 59, BLACK, NAVY, 5, 154)
    for x in range(10, 152, 12): dr.line((x, 56, x, 59), fill=DEEP)
    for y in range(14, 56, 10):
        for x in range(8, 152, 4): dr.point((x, y), fill=DEEP)
    bars(dr, 55, scale=0.95)
    dr.polygon([(77, 5), (83, 5), (80, 9)], fill=WHITE)
    word(im, 80 - word_w('TEMPEST', 0.86, 3) // 2, 70, 'TEMPEST', WHITE, 0.86, 3)
    ctext(im, F8, 94, 'FIRMWARE', TEAL)
    dr.line((30, 106, 129, 106), fill=DEEP); ctext(im, F8, 112, VER, GREY)
    return im

OPTS = [('E0', 'Original', opt_e), ('E1', 'Reflection', e1), ('E2', 'Bars behind name + peak caps', e2),
        ('E3', 'Bars + waterfall strip', e3), ('E4', 'Scope frame', e4)]

if __name__ == '__main__':
    out = sys.argv[1]; S = 2; cols = 3
    sheet = Image.new('RGB', (cols * (160 * S + 24) + 24, 2 * (128 * S + 44) + 20), (40, 40, 40)); sd = ImageDraw.Draw(sheet)
    for k, (tag, name, fn) in enumerate(OPTS):
        im = fn(); px = im.load()
        for y in range(128):
            for x in range(160): px[x, y] = q565(px[x, y])
        base = os.path.join(out, f'tempest_logo_{tag}')
        im.save(base + '_1x.png'); im.resize((320, 256), Image.NEAREST).save(base + '_2x.png')
        im.resize((640, 512), Image.NEAREST).save(base + '_4x.png')
        X = 24 + (k % cols) * (160 * S + 24); Y = 36 + (k // cols) * (128 * S + 44)
        sheet.paste(im.resize((160 * S, 128 * S), Image.NEAREST), (X, Y)); sd.text((X, Y - 18), f'{tag}  {name}', fill=(255, 255, 255))
    sheet.save(os.path.join(out, 'tempest_logo_E_iterations.png')); print('ok')

def e_final():   # E0 without FIRMWARE (2026-11-25)
    im = opt_e(); dr = ImageDraw.Draw(im)
    dr.rectangle((0, 100, 159, 111), fill=BLACK)   # FIRMWARE line removed
    return im
