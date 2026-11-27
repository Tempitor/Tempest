# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Add the "monitor works on every channel" fix to an HA1G V1.01.14.002 image.

usage: build_mon.py IN.bin OUT.bin
  IN may be the stock image or one of the earlier mod builds in this folder
  (CTCSS or SCR); the fix is stacked on top and the earlier mod is kept.

Root cause (stock firmware)
---------------------------
Both monitor key functions ("Monitor" = hold, "MonitorSw" = toggle; key-function
table in RAM at 0x1fff9860, handlers 0x19702 / 0x19730 -> 0x1a4cc / 0x1a4fc)
set monitor flag bit 1 of radio[8] and then re-program the RX path with
squelch LEVEL 0 and tone squelch off (0x1a400, and the RX re-setup at 0x10ab0).
They never actually force the squelch open.

Squelch level 0 on this radio is not "open": the software squelch at 0x9cae
still needs RSSI > a per-band threshold (default level-0 table at 0x6770c:
open 68 on >=400 MHz, 42 below; factory calibration in EEPROM overrides it per
sub-band) AND noise indicator < 0x38/0x3e AND glitch count < 0x11/0x14
(set per band and bandwidth in 0xacf8). On an empty channel the noise
indicator is high, so whether "monitor" opens depends on the channel's band,
bandwidth and that band's calibration. Hence: monitor works on some channels
only.

Fix
---
One hook in the RX status poll (0xa966) right after the TX check: when the
monitor flag (radio[8] bit 1) is set, the squelch state is forced open and
the threshold checks are skipped. Everything else (tone/CTCSS/DCS handling,
interrupt processing, audio routing) runs exactly as stock. When the monitor
flag is clear the stock code path is taken unchanged, so normal squelch and
the configured squelch levels behave exactly as before.

  0x0a98c  ldrb.w r0,[fp]  ->  b.w mon_hook        (4 bytes)
  cave     mon_hook (appended after the image end, 4-byte aligned)
  version  Radio Information suffix gains 'Q' (V1.01.14.002Q / ...CQ / ...MQ,SQ)
"""
import sys,hashlib,keystone

KNOWN={
 '267bee83b844d99f76a008ab2698a822c78fd8fecc27ab6cd79e4f869e8f2d77':'stock',
 '191a4c40dc10980b3b4686a4cb34c1e74ff91c032f2c654389677d240a0e2acc':'ctcss',
 '775aa384331babf7c973c9bf1af350b42deab9c458a9af10a99a775b401bba4a':'scr',
}
BASE=0x4000
src,dst=sys.argv[1],sys.argv[2]
d=bytearray(open(src,'rb').read())
kind=KNOWN.get(hashlib.sha256(d).hexdigest())
assert kind,'input is not stock V1.01.14.002 or a known mod build from this folder'
assert len(d)%4==0

ks=keystone.Ks(keystone.KS_ARCH_ARM,keystone.KS_MODE_THUMB)
def asm(s,addr):
    b,_=ks.asm(s,addr); return bytes(b)
def put(addr,old,new):
    o=addr-BASE
    assert d[o:o+len(old)]==bytes(old),(hex(addr),d[o:o+len(old)].hex())
    assert len(old)==len(new)
    d[o:o+len(new)]=new

SITE=0xa98c          # in rx_status_poll(radio=r4, fp=sb=&rxdrv 0x1fff9260, r8=0)
RESUME=0xa990        # stock: lsls r0,r0,#31 ; beq ...
JOIN=0xa9ea          # stock: common tail after the squelch decision
CAVE=BASE+len(d)

cave_src=f"""
mon_hook:
  ldrb r0, [r4, #8]
  lsls r0, r0, #30
  bpl mon_norm
  ldrb.w r0, [fp]
  orr r0, r0, #1
  strb.w r0, [fp]
  movs r0, #0
  strb.w r0, [fp, #0xa]
  ldrb r0, [r4, #9]
  bic r0, r0, #0x80
  strb r0, [r4, #9]
  b.w #{JOIN}
mon_norm:
  ldrb.w r0, [fp]
  b.w #{RESUME}
"""
cave=asm(cave_src,CAVE)
cave+=b'\0'*(-len(cave)%4)

put(SITE,bytes.fromhex('9bf80000'),asm(f'b.w #{CAVE}',SITE))

# version marker: for two-letter suffixes drop the redundant %02d on the minor field
# (14 prints the same either way) so every string still fits its 20-byte slot.
n=0
for old,new in [
    (b'V%2d.%02d.%02d.%03d\0',  b'V%d.%02d.%02d.%03dQ\0'), # stock
    (b'V%d.%02d.%02d.%03dC\0',  b'V%d.%02d.%d.%03dCQ\0'),  # ctcss
    (b'V%d.%02d.%02d.%03dM\0',  b'V%d.%02d.%d.%03dMQ\0'),  # scr, flag off (2 copies)
    (b'V%d.%02d.%02d.%03dS\0',  b'V%d.%02d.%d.%03dSQ\0'),  # scr, flag on
]:
    new=new.ljust(20,b'\0')
    assert len(old)==len(new)==20
    i=d.find(old)
    while i>=0:
        d[i:i+20]=new; n+=1; i=d.find(old,i+20)
assert n>=1,'version format string not found'

d+=cave
open(dst,'wb').write(d)
print(f'base={kind} cave@{CAVE:#x} len={len(cave)} fmt_strings={n} size={len(d)}')
print(hashlib.sha256(d).hexdigest())
