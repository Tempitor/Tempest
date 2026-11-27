#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""3-VFO (Band C) test build.  usage: build_vfo3.py SCOPE.bin OUT.bin
SCOPE.bin = MON_TAFR + scope add-on built by tools/vfo3/scope (build_scope.py with the clang cave from
make_cave_clang.sh, whose scope.c gives the 3-VFO view a full S-meter at y69 and a labelled scope at y85).
1) Stock init sets radio+0x9c (VFO count) = 2 for every model; all 3-VFO code (Band C menu item,
   A/B/C cycle, 3-panel template 0x5a9a0, VFO-C record 2) is gated on +0x9c==3.
   0x35ace (HA1G init path): store 3. r8 (=2) untouched: it is reused at 0x35bae as EU region default.
2) Panel fill 0x19148 handles layout 1 and 2 only (cmp r5,#2; bne exit), so the 3-panel screen kept its
   template placeholder 'Text'. Hook it to a cave that fills panels 0..2 with the stock per-panel
   routines 0x1852c / 0x186d8 (both already fall through to their 3-panel ID tables for layout 3).
3) Refresh message 0x408 in the main dialog callback (0x1482e) also only passed layouts 1/2 on: let 3 through.
Version: V1.1.14.002D020 (revision REV below)."""
import sys, hashlib
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
src, out = sys.argv[1:3]
d = bytearray(open(src,'rb').read())
assert b'V%d.%d.%d.%03dQRP13\0' in d, 'expected a QRP13 scope build'
d += b'\0' * (-len(d) % 4)
B = 0x4000
ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
def asm(src, addr):
    return bytes(ks.asm(src, addr)[0])
def patch(addr, old, new):
    o = addr - B
    assert d[o:o+len(old)] == old, (hex(addr), d[o:o+len(old)].hex())
    assert len(old) == len(new)
    d[o:o+len(new)] = new
# 1) VFO count = 3 on the HA1G init path
patch(0x35ace, bytes.fromhex('84f89c80' '6770'), bytes.fromhex('0320' '84f89c00'))
# 2) layout-3 panel fill in a cave appended after the scope cave
CAVE = B + len(d)
assert CAVE % 4 == 0
cave = asm("""
    cmp r5, #2
    bne not2
    b.w 0x19200
not2:
    cmp r5, #3
    beq is3
    b.w 0x19176
is3:
    movs r4, #0
loop:
    str r4, [sp]
    mov r3, r4
    mov r2, r5
    mov r1, r7
    mov r0, r8
    bl 0x1852c
    str r4, [sp]
    mov r3, r4
    mov r2, r5
    mov r1, r7
    mov r0, r8
    bl 0x186d8
    adds r4, #1
    cmp r4, #3
    blo loop
    b.w 0x19176
""", CAVE)
d += cave
patch(0x191fc, bytes.fromhex('022dbad1'), asm('b.w %#x' % CAVE, 0x191fc))
# 2b) panel background colours 0x1925c: panel C is only recoloured when arg5 (actually the selected
#     VFO id, 0..2) == 3, so it kept the template's blue. Test the real layout MAINDLG[0]==3 instead.
CAVE2 = B + len(d)
assert CAVE2 % 4 == 0
cave2 = asm('''
    ldr r1, =0x1fff9518
    ldrb r1, [r1]
    cmp r1, #3
    beq c3
    b.w 0x192c6
c3:
    b.w 0x19294
''', CAVE2)
d += cave2 + b'\0' * (-len(cave2) % 4)
patch(0x19290, bytes.fromhex('032d18d1'), asm('b.w %#x' % CAVE2, 0x19290))
# 2c) 3-panel template 0x5a9a0 (28-byte entries: cb,name,id,x,y,w,h). Compact: 23-px panels (y0/23/46,
#     ending at 69 where the add-on's S-meter starts); CH label hidden (the channel number is on the top row);
#     top row y0 h10; name (2,7,90,16) 2 px below the top row; frequency (94,12,54,10) and W on the name row.
import struct
FAM = [  # ids for panels A,B,C -> new (x,y,w,h) relative to the panel top (None = keep x/w)
    ((0x85b,0x85c,0x85d), (0,0,160,23)),
    ((0x842,0x843,0x844), (None,1,None,10)),   # zone (1 px below the panel top)
    ((0x81e,0x81f,0x820), (None,1,None,10)),   # channel number
    ((0x83c,0x83d,0x83e), (None,1,None,10)), ((0x839,0x83a,0x83b), (None,1,None,10)),
    ((0x815,0x816,0x817), (None,1,None,10)), ((0x818,0x819,0x81a), (None,1,None,10)),   # status icons
    ((0x81b,0x81c,0x81d), (148,1,10,10)),      # power L/M/H
    ((0x80f,0x810,0x811), (148,12,10,10)),     # bandwidth W/N
    ((0x83f,0x840,0x841), (128,12,16,10)),
    ((0x822,0x827,0x82a), (160,0,1,1)),        # CH-n label: hidden off screen (D008: size 0 meant 'size of parent' in emWin, so CH-49 showed under card C)
    ((0x823,0x828,0x82b), (2,7,90,16)),        # name (16 px font)
    ((0x824,0x829,0x82c), (94,12,54,10)),      # frequency (8 px font)
]
ent = {}
for k in range(44):
    a = 0x5a9a0 + 28*k
    wid, x, y, w, h = struct.unpack_from('<Hhhhh', d, a + 8 - B)
    ent.setdefault(wid, a)
done = 0
for ids, (nx, ny, nw, nh) in FAM:
    for p, wid in enumerate(ids):
        a = ent[wid]; old = bytes(d[a+8-B:a+18-B])
        _, x, y, w, h = struct.unpack('<Hhhhh', old)
        new = struct.pack('<Hhhhh', wid, x if nx is None else nx, 16 + 23*p + ny, w if nw is None else nw, nh)   # D007: +16, meter on top
        patch(a+8, old, new); done += 1
assert done == 39
# 2d) '#' display cycle 0x16c28: with 3 VFOs, two shown -> first press swaps the partner VFO (state byte
#     [r5+3]), only the second press shows all three. Make it single -> dual -> triple -> single.
patch(0x16c78, bytes.fromhex('e87888b1'), asm('nop; nop', 0x16c78))
# 3) 0x408 refresh: (cmp r2,#1; beq; cmp r2,#2; bne exit) -> (subs r0,r2,#1; cmp r0,#2; bhi exit; nop)
patch(0x1482e, bytes.fromhex('012a01d0022af9d1'), asm('subs r0, r2, #1; cmp r0, #2; bhi 0x1482a; nop', 0x1482e))
# D018/D019: frequency display 4 decimal places instead of 5.  The panel code has SEVEN
# copies of the formatter that builds "%03d.%05d" from (MHz, remainder/10), remainder = freq -
# MHz*1e6 (sub-MHz Hz), one per layout/mode.  Six share the format string at 0x18898, one uses
# 0x1abec.  To drop the 10 Hz digit every copy's divisor must go /10 -> /100 and its format string
# -> "%04d".  D018 only did one divisor (0x1899a) + the 0x18898 string, so the other five copies
# printed a 5-digit value with %04d = still 5 places on most screens.  D019 patches all seven divisors.
for a in (0x184ae, 0x1899a, 0x18ac8, 0x18b88, 0x18c8a):
    patch(a, bytes.fromhex('0a20'), bytes.fromhex('6420'))     # movs r0,#0xa -> #0x64  (/10 -> /100)
patch(0x19108, bytes.fromhex('0a21'), bytes.fromhex('6421'))   # movs r1,#0xa -> #0x64
patch(0x1889f, b'5', b'4')                                     # 0x18898 "%03d.%05d" -> "%03d.%04d" (shared by six)
patch(0x1ab32, bytes.fromhex('0a21'), bytes.fromhex('6421'))   # movs r1,#0xa -> #0x64 (0x1abec formatter)
patch(0x1abf3, b'5', b'4')                                     # 0x1abec "%03d.%05d" -> "%03d.%04d"
# version suffix QRP13 -> revision scheme Dnnn (D001 = 2026-11-24 baseline, was Q3V12)
REV = 'D022'
i = d.find(b'V%d.%d.%d.%03dQRP13\0'); assert i > 0 and len(REV) <= 5
d[i:i+20] = (b'V%d.%d.%d.%03d' + REV.encode()).ljust(20, b'\0')
END = B + len(d)
assert END <= 0x7C000, f'image ends at {END:#x}: D010+ must be finished by tools/vfo3/logo/build_logo.py (owns 0x74000-0x7DFFF, blocks CPS picture writes)'
open(out,'wb').write(d)
# check the cave decodes to the intended branch targets
import capstone
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
tg = [i.op_str for i in md.disasm(bytes(cave), CAVE) if i.mnemonic.startswith('b')]
assert tg == ['#%#x'%(CAVE+8), '#0x19200', '#%#x'%(CAVE+0x10), '#0x19176', '#0x1852c', '#0x186d8', '#%#x'%(CAVE+0x12), '#0x19176'], tg
tg = [i.mnemonic+' '+i.op_str for i in md.disasm(bytes(cave2), CAVE2)]
assert tg[3:6] == ['beq #%#x'%(CAVE2+0xc), 'b.w #0x192c6', 'b.w #0x19294'] and 'ldr r1' in tg[0], tg
lit = int(tg[0].split('#')[1].rstrip(']'),16); la = ((CAVE2+4)&~3)+lit
assert d[la-B:la-B+4] == (0x1fff9518).to_bytes(4,'little'), hex(la)
print(out, hex(len(d)), hashlib.sha256(d).hexdigest())
