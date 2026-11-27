# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Add an S-meter and a band-scope strip to the HA1G main screen.

usage: build_scope.py IN.bin OUT.bin [--step 6250] [--half 18] [--dwell-us 1500]
                      [--hop-ticks 1] [--pts-per-hop 1] [--redraw-ticks 5]
                      [--cal-db 0] [--floor -130] [--top -70] [--quiet-ticks 3]
                      [--watch-view 1] [--recentre-ticks 25]
                      [--cave cave.bin]
  IN must be HA1G_V1.01.14.002_MON_TAFR.bin (monitor + TA/FR fixes); both are kept.
  The add-on code (scope.c + glue.S, compiled for 0x73350) is appended after the
  image end; cave.bin is the compiled blob, its first 56 bytes are the settings.

Patch sites
  0x101e6  radio tick, odd ticks (polls run on even ticks): b.w tick_glue -> scope_tick()
  0x0ad52  RX setup bl bk_setfreq -> bl hf_hook (remembers the home frequency)
  0x0b3f8  same for the other RX retune path
  0x14aec  main-screen dialog callback pointer -> dlg_hook (creates the strip windows)
  0x38830  standby RX info card -> popup_hook (skipped while the strip is shown)
  0x38a3c  same for the 5 s card after RX ends
  version  Radio Information suffix gains 'P13' (V1.1.14.002QRP13)
"""
import sys,hashlib,struct,argparse,os,keystone
ap=argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--cave',default=os.path.join(os.path.dirname(os.path.abspath(__file__)),'scope_cave.bin'))
for n,dv in (('step',6250),('half',18),('dwell-us',2500),('hop-ticks',1),('pts-per-hop',3),
             ('redraw-ticks',5),('cal-db',0),('floor',-130),('top',-70),('quiet-ticks',3),('watch-view',1),('recentre-ticks',25),('dw-pts',3),('dw-quiet',1),('toggle-key',1),('scope-on',2),('even-hops',1),('meter-gap',2),('meter-every',2),('lock-margin',10)):
    ap.add_argument('--'+n,type=int,default=dv)
a=ap.parse_args()
MON_TAFR='09a75c39fc04dac7dcc8e8a96d72aa99bf0bce37f7b4d5378db30d3eaf242943'
BASE=0x4000; CAVE=0x73350
d=bytearray(open(a.src,'rb').read())
assert hashlib.sha256(d).hexdigest()==MON_TAFR,'input must be HA1G_V1.01.14.002_MON_TAFR.bin'
assert BASE+len(d)==CAVE
cave=bytearray(open(a.cave,'rb').read())
assert struct.unpack_from('<I',cave,0)[0]==0x31504353,'cave.bin settings header missing'
assert 1<=a.half<=24 and a.step>=1000 and a.half*a.step<=500000
assert 200<=a.dwell_us<=20000 and 1<=a.pts_per_hop<=8 and a.hop_ticks>=1 and a.redraw_ticks>=1
assert a.top>a.floor and 1<=a.dw_pts<=8 and 0<=a.toggle_key<=0x10 and a.scope_on in (0,1,2)
struct.pack_into('<IIIIIIIIiiiIIIIIIIIIIi',cave,0,0x31504353,1,a.step,a.half,a.dwell_us,a.hop_ticks,
                 a.pts_per_hop,a.redraw_ticks,a.cal_db,a.floor,a.top,a.quiet_ticks,a.watch_view,a.recentre_ticks,a.dw_pts,a.dw_quiet,a.toggle_key,a.scope_on,a.even_hops,a.meter_gap,a.meter_every,a.lock_margin)
# symbol addresses inside the cave (fixed by the link map, checked here)
SYM={k:int(v,16) for k,v in (l.split() for l in open(os.path.splitext(a.cave)[0]+'.sym'))}
assert SYM['CFG']==CAVE
ks=keystone.Ks(keystone.KS_ARCH_ARM,keystone.KS_MODE_THUMB)
def asm(s,addr): return bytes(ks.asm(s,addr)[0])
def put(addr,old,new):
    o=addr-BASE; assert d[o:o+len(old)]==bytes(old),(hex(addr),d[o:o+len(old)].hex())
    assert len(old)==len(new); d[o:o+len(new)]=new
put(0x101e6,bytes.fromhex('c00704d1'),asm(f'b.w #{SYM["tick_glue"]}',0x101e6))
put(0x0ad52,asm('bl #0x9fda',0xad52),asm(f'bl #{SYM["hf_hook"]}',0xad52))
put(0x0b3f8,asm('bl #0x9fda',0xb3f8),asm(f'bl #{SYM["hf_hook"]}',0xb3f8))
put(0x38830,asm('bl #0x2b670',0x38830),asm(f'bl #{SYM["popup_hook"]}',0x38830))
put(0x38a3c,asm('bl #0x2b670',0x38a3c),asm(f'bl #{SYM["popup_hook"]}',0x38a3c))
put(0x3b852,bytes.fromhex('7cb50646'),asm(f'b.w #{SYM["key_glue"]}',0x3b852))
put(0x0fdb8,bytes.fromhex('06462046'),asm(f'b.w #{SYM["mon_poll_glue"]}',0xfdb8))
put(0x1001e,bytes.fromhex('a8794007'),asm(f'b.w #{SYM["mon_dtmf_glue"]}',0x1001e))
put(0x0fc88,bytes.fromhex('3079b8b1'),asm(f'b.w #{SYM["mon_tone_glue"]}',0xfc88))
put(0x39aa8,asm('bl #0x2b670',0x39aa8),asm(f'bl #{SYM["popup_hook"]}',0x39aa8))   # stock TX card
# receiving panel green: re-apply after the stock panel fill / background repaint
put(0x14860,asm('bl #0x19148',0x14860),asm(f'bl #{SYM["fill_hook"]}',0x14860))
put(0x1930e,asm('bl #0x19148',0x1930e),asm(f'bl #{SYM["fill_hook"]}',0x1930e))
put(0x192fe,asm('bl #0x1925c',0x192fe),asm(f'bl #{SYM["bg_hook"]}',0x192fe))
# Radio Setting: 15th item "Band Scope", D020: 16th item "Theme" (item count 0xe -> 0x10)
put(0x15920,asm('ldr.w r8, [pc, #0x240]',0x15920),asm(f'b.w #{SYM["rs_fill_glue"]}',0x15920))
put(0x15944,asm('cmp r4, #0xe',0x15944),asm('cmp r4, #0x10',0x15944))
put(0x159ea,asm('add.w r8, r5, #0x44',0x159ea),asm(f'b.w #{SYM["rs_key_glue"]}',0x159ea))
put(0x159f8,asm('mov.w ip, #0xe',0x159f8),asm('mov.w ip, #0x10',0x159f8))
put(0x15a84,asm('cmp r7, #0xe',0x15a84),asm('cmp r7, #0x10',0x15a84))
put(0x15aa2,asm('cmp r7, #0xe',0x15aa2),asm('cmp r7, #0x10',0x15aa2))
# D020: themes - bitmap palette entries are recoloured too (GUI palette -> index loop at 0x45c3c);
# the colour-API pointer 0x1fffafdc is redirected at run time by th_install() (scope.c)
put(0x45c40,asm('bl #0x45718',0x45c40),asm(f'bl #{SYM["th_pal"]}',0x45c40))
# D003: side keys as PTT by VFO view (side-key translator) + which VFO each PTT keys (PTT handler)
# D006: the lock check result (cbz r0 at 0x36794) goes through lock_glue first, so a side key held as PTT
# is released even while the keypad is locked; lock_glue then continues in side_glue
put(0x36794,bytes.fromhex('c0b199f80100'),asm(f'b.w #{SYM["lock_glue"]}; nop',0x36794))
# D006: key dispatcher skips the translator in Key Lock Mode 2 and in Weather Alert: kd_glue still passes side-key PTT
put(0x368f6,bytes.fromhex('022808d0'),asm(f'b.w #{SYM["kd_glue"]}',0x368f6))
# D003: Radio Setting -> 5 Key Function: 4th item "Side Key PTT" (list fill, entry table, item count 3 -> 4)
put(0x1c518,asm('ldr.w r8, [pc, #0x23c]',0x1c518),asm(f'b.w #{SYM["kfm_fill_glue"]}',0x1c518))
put(0x1c53c,asm('cmp r4, #3',0x1c53c),asm('cmp r4, #4',0x1c53c))
put(0x1c5e0,asm('add.w r7, r4, #0x18',0x1c5e0),asm(f'b.w #{SYM["kfm_key_glue"]}',0x1c5e0))
put(0x1c5ee,asm('mov.w ip, #3',0x1c5ee),asm('mov.w ip, #4',0x1c5ee))
put(0x1c678,asm('cmp r7, #3',0x1c678),asm('cmp r7, #4',0x1c678))
put(0x1c696,asm('cmp r7, #3',0x1c696),asm('cmp r7, #4',0x1c696))
put(0x1c6c6,asm('cmp r1, #3',0x1c6c6),asm('cmp r1, #4',0x1c6c6))
put(0x1c6ce,asm('movs r1, #2',0x1c6ce),asm('movs r1, #3',0x1c6ce))
# D008: 3-VFO main screen is created through tpl3_create (32-px cards from a RAM copy while the scope is off)
put(0x1b572,asm('bl #0x40c70',0x1b572),asm(f'bl #{SYM["tpl3_create"]}',0x1b572))
# D011: same for the 2-VFO main screen (template 0x5a63c, n=31)
put(0x1b59e,asm('bl #0x40c70',0x1b59e),asm(f'bl #{SYM["tpl3_create"]}',0x1b59e))
put(0x383ce,bytes.fromhex('0d2d0fd0'),asm(f'b.w #{SYM["ptt_glue"]}',0x383ce))
# Key Function Select: Band Scope (function id 40) as row 12, Prog PTT row 13
put(0x1d31c,asm('ldr.w r8, [pc, #0x29c]',0x1d31c),asm(f'b.w #{SYM["kf_fill_glue"]}',0x1d31c))
put(0x1d3d0,bytes.fromhex('60780c21'),asm(f'b.w #{SYM["kf_open_glue"]}',0x1d3d0))
put(0x1d55c,bytes.fromhex('a0880d28'),asm(f'b.w #{SYM["kf_sel_glue"]}',0x1d55c))
# side/top key function -> key code: Band Scope toggles the scope
put(0x368c0,asm('bl #0x36670',0x368c0),asm(f'bl #{SYM["sk_map"]}',0x368c0))
put(0x14aec,struct.pack('<I',0x146e5),struct.pack('<I',SYM['dlg_hook']|1))
# D010: standby-screen keys go through wf_key (waterfall marker: Up/Down move it, Menu = Go)
put(0x14fe2,asm('bl #0x14bec',0x14fe2),asm(f'bl #{SYM["wf_key"]}',0x14fe2))
# watch view: re-lay out the stock two-VFO dialog template (0x5a63c, 28-byte GUI_WIDGET_CREATE_INFO
# entries: cb, name, id u16, x, y, w, h i16, flags u16, para, extra) so both VFO panels are 36 px tall
# (all their texts are vertically centred) with a 10-px gap for the meter between them.
# id: (old y, old h, new y, new h)
# vfo3: identical to the 3-VFO view -> D007: full meter y0, panels A y16..49 and B y50..84 (TPL2 y + 16), scope y85
# top rows (zone, channel, icons, power) 1 px below the panel top so they do not touch the bar above
# D002: name and CH/frequency/W rows 1 px lower so the zone/channel row no longer touches the name
# (freq row y24 h10 draws at the same pixel as y23 h12 would, but stays inside the 34-px panel A)
TPL2={0x85b:(0,47,0,34),  0x842:(0,16,1,10), 0x81e:(0,16,1,10), 0x83c:(2,10,1,10), 0x839:(2,10,1,10),
      0x815:(2,10,1,10),  0x818:(2,10,1,10), 0x81b:(3,10,1,10), 0x823:(14,20,9,18),
      0x822:(32,16,24,10),0x824:(32,16,24,10),0x80f:(35,10,24,10),0x83f:(35,10,24,10),
      0x85c:(47,47,34,35),0x843:(47,16,35,10),0x81f:(47,16,35,10),0x83d:(49,10,35,10),0x83a:(49,10,35,10),
      0x816:(49,10,35,10),0x819:(49,10,35,10),0x81c:(50,10,35,10),0x828:(61,18,43,18),
      0x827:(79,16,58,10),0x829:(79,16,58,10),0x810:(82,10,58,10),0x840:(82,10,58,10)}
if a.watch_view:
    o=0x5a63c-BASE; seen=set()
    while True:
        wid,x,y,w,h=struct.unpack_from('<HhhhH',d,o+8)
        if struct.unpack_from('<I',d,o)[0]>>20!=0 or not (0x800<=wid<0x900): break
        if wid in TPL2:
            oy,oh,ny,nh=TPL2[wid]; assert (y,h)==(oy,oh),(hex(wid),y,h)
            struct.pack_into('<h',d,o+12,ny+16); struct.pack_into('<h',d,o+16,nh); seen.add(wid)   # D007: +16, meter on top
        o+=28
        if wid==0x860: break
    assert seen==set(TPL2),sorted(hex(i) for i in set(TPL2)-seen)
n=0
for i in range(len(d)-20):
    if d[i:i+19]==b'V%d.%02d.%d.%03dQR\0':
        d[i:i+20]=b'V%d.%d.%d.%03dQRP13\0'; n+=1
assert n>=1,'version string not found'
d+=cave; d+=b'\0'*(-len(d)%4)
assert BASE+len(d)<=0x7C000,f'add-on ends at {BASE+len(d):#x}: D010 may pass 0x76000 only because the logo step (tools/vfo3/logo) owns 0x74000-0x7DFFF; keep room for the logo'
open(a.dst,'wb').write(d)
print(f'fmt_strings={n} cave={len(cave)} size={len(d)}')
print(hashlib.sha256(d).hexdigest())
