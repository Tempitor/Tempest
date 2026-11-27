#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Check a logo build: patch sites, CPS picture-upload block, and an emulated render of logo_draw
(Unicorn, stock GUI calls hooked) compared pixel by pixel with the mockup (mock_bootlogo_e.e_final).
usage: verify_logo.py BASE.bin LOGO.bin [render.png]"""
import sys, os, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from unicorn import *
from unicorn.arm_const import *
import capstone
from PIL import Image, ImageDraw
base = open(sys.argv[1], 'rb').read(); img = open(sys.argv[2], 'rb').read()
B = 0x4000; ok = True
def check(n, c):
    global ok; ok &= bool(c); print(f'  {"OK  " if c else "FAIL"} {n}')
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
def ins(a): return next(md.disasm(img[a-B:a-B+4], a))
ORG = B + len(base) + (-len(base) % 4)
print('--- 1. patch sites ---')
diff = [B + i for i in range(len(base)) if base[i] != img[i]]
sites = sorted({a & ~1 for a in diff})
check('only 0x15190 (boot paint), 0x2baba, 0x2bade, 0x2bb34 changed in the base image',
      all(any(s <= a < s + 4 for s in (0x15190, 0x2baba, 0x2bade, 0x2bb34)) for a in diff))
i = ins(0x15190); check(f'boot paint calls logo_draw at {ORG:#x} ({i.mnemonic} {i.op_str})', i.mnemonic == 'bl' and int(i.op_str[1:], 16) == ORG)
check('picture erase 0x2bade and erase+write 0x2bb34 return at once', img[0x2bade-B:0x2bade-B+2] == b'\x70\x47' and img[0x2bb34-B:0x2bb34-B+2] == b'\x70\x47')
check('picture packet write 0x2baba returns 1 without writing', img[0x2baba-B:0x2baba-B+4] == bytes.fromhex('01207047'))
END = B + len(img); check(f'image ends {END:#x} <= 0x7E000', END <= 0x7E000)
v = img.find(b'V%d.%d.%d.%03d'); check('version string ' + img[v:v+18].split(b'\0')[0].decode(), v > 0)

print('--- 2. emulated logo_draw ---')
mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB); mu.mem_map(0, 0x80000); mu.mem_write(B, img); mu.mem_map(0x1fff8000, 0x38000)
calls = []; pc_ok = [True]
def r(n): return mu.reg_read(getattr(arm_const, 'UC_ARM_REG_' + n))
def hook(name, rv=0):
    def f(uc, a, s, u):
        calls.append((name, [r('R0'), r('R1'), r('R2'), r('R3')])); uc.reg_write(UC_ARM_REG_R0, rv)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    return f
for a, n, rv in ((0x42b96, 'color', 0), (0x42bd0, 'font', 0x1234), (0x42cc4, 'tmode', 1), (0x41ad8, 'fill', 0),
                 (0x410a8, 'text', 0), (0xf18c, 'flush', 0)):
    mu.hook_add(UC_HOOK_CODE, hook(n, rv), begin=a, end=a)
def anyc(uc, a, s, u):
    if not (ORG <= a < END or a in (0x42b96, 0x42bd0, 0x42cc4, 0x41ad8, 0x410a8, 0xf18c, 0x7fff0)): pc_ok[0] = False; print('  stray pc', hex(a))
mu.hook_add(UC_HOOK_CODE, anyc)
wr = []
mu.hook_add(UC_HOOK_MEM_WRITE, lambda uc, acc, a, sz, v, u: wr.append(a) if not (0x2001a000 - 0x400 <= a < 0x2001a000) else None)
mu.reg_write(UC_ARM_REG_SP, 0x2001a000); mu.reg_write(UC_ARM_REG_LR, 0x7fff1)
mu.emu_start(ORG | 1, 0x7fff0, count=2_000_000)
check('returns, only calls the stock GUI/flush functions', mu.reg_read(UC_ARM_REG_PC) == 0x7fff0 and pc_ok[0])
check('no RAM written outside its own stack', not wr)
names = [c[0] for c in calls]
check('ends: font 8 px, text mode 2, grey text centred at (80,118), modes restored, flush',
      names[-7:] == ['font', 'tmode', 'color', 'text', 'tmode', 'font', 'flush'] and calls[-7][1][0] == 0x68918 and calls[-6][1][0] == 2
      and calls[-4][1][1:3] == [80, 118] and calls[-3][1][0] == 1 and calls[-2][1][0] == 0x1234)
txt = bytes(mu.mem_read(calls[-4][1][0], 32)).split(b'\0')[0].decode(); print('   text:', txt)
nf = names.count('fill'); print(f'   {nf} FillRect calls')
im = Image.new('RGB', (160, 128), (255, 0, 255)); dr = ImageDraw.Draw(im); col = (0, 0, 0)
from mock import text
from font import width
def s16(x): return struct.unpack('<i', struct.pack('<I', x))[0]
for n, a in calls:
    if n == 'color': col = ((a[0] >> 16) & 255, (a[0] >> 8) & 255, a[0] & 255); assert a[0] >> 24 == 0xff
    elif n == 'fill': dr.rectangle(tuple(map(s16, a)), fill=col)
    elif n == 'text': text(im, 0x68918, 80 - width(0x68918, txt) // 2, 118, txt, col)
from mock_bootlogo_e import e_final
from mock_bootlogo import q565
ref = e_final()
q = lambda m: [q565(p) for p in m.getdata()]
a, b = q(im), q(ref)
bad = [k for k in range(len(a)) if a[k] != b[k]]
check(f'emulated render == mockup at RGB565 ({len(bad)} pixels differ)', not bad)
for k in bad[:10]: print('   ', (k % 160, k // 160), a[k], b[k])
if len(sys.argv) > 3:
    S = 4; out = Image.new('RGB', (160 * S * 2 + 60, 128 * S + 50), (40, 40, 40)); od = ImageDraw.Draw(out)
    out.paste(im.resize((160 * S, 128 * S), Image.NEAREST), (20, 40)); out.paste(ref.resize((160 * S, 128 * S), Image.NEAREST), (160 * S + 40, 40))
    od.text((20, 14), 'emulated firmware (logo_draw)', fill=(255, 255, 255)); od.text((160 * S + 40, 14), 'approved mockup', fill=(255, 255, 255))
    out.save(sys.argv[3])
print('ALL OK' if ok else 'FAILURES'); sys.exit(0 if ok else 1)
