# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Verify the monitor fix by diffing and by CPU emulation of the RX status poll.
usage: verify_mon.py BASE.bin MON.bin
  BASE = the image build_mon.py was given (stock, CTCSS or SCR build)

Checks
  1. Only the hook site, the version string(s) and the appended cave differ.
  2. Emulates rx_status_poll (0xa966) with stubbed BK4819 register reads,
     on both images, with the stock level-0 thresholds of a UHF channel:
       - empty channel, monitor OFF : closed on both (normal squelch unchanged)
       - empty channel, monitor ON  : stock stays closed (the bug), fix opens
       - strong signal, monitor OFF : opens on both after the stock debounce
       - monitor ON then OFF, empty : fix closes again with normal squelch
"""
import sys,struct
from unicorn import *
from unicorn.arm_const import *
BASE=0x4000
base=open(sys.argv[1],'rb').read(); mod=open(sys.argv[2],'rb').read()

# ---- 1. diff ----
diff=[i for i in range(len(base)) if base[i]!=mod[i]]
runs=[]
for i in diff:
    if runs and i==runs[-1][1]+1: runs[-1][1]=i
    else: runs.append([i,i])
ok=True
print('--- 1. diff vs base ---')
for s,e in runs:
    a=s+BASE; txt=mod[s:e+1]
    if a==0xa98c and e-s<4: tag='hook 0xa98c'
    elif b'%03d' in mod[s-18:e+3]: tag='version string'
    elif a>=BASE+len(base)-248: tag='earlier mod cave: version string'
    else: tag='UNEXPECTED'; ok=False
    print(f'  {a:#x}..{e+BASE:#x} ({e-s+1} bytes) {tag}')
print('  appended:',len(mod)-len(base),'bytes @',hex(BASE+len(base)))

# ---- 2. emulation ----
RXDRV=0x1fff9260; RADIO=0x20020000; CFG=0x2000792a
def mkemu(img):
    mu=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
    mu.mem_map(0,0x80000); mu.mem_write(BASE,img)
    mu.mem_map(0x1fff0000,0x40000)
    return mu
def run_poll(mu,regs):
    def stub(uc,addr,size,ud):
        lr=uc.reg_read(UC_ARM_REG_LR)
        if addr==0x9716: uc.reg_write(UC_ARM_REG_R0,regs.get(uc.reg_read(UC_ARM_REG_R0),0))
        else: uc.reg_write(UC_ARM_REG_R0,0)
        uc.reg_write(UC_ARM_REG_PC,lr)
    hs=[mu.hook_add(UC_HOOK_CODE,stub,begin=a,end=a) for a in (0x9716,0x96bc,0x932c,0x151c6)]
    sp=0x2002f000
    outs=[0x2002e000,0x2002e004,0x2002e008]
    mu.mem_write(sp,struct.pack('<3I',*outs))
    for r,v in ((UC_ARM_REG_R0,RADIO),(UC_ARM_REG_R1,CFG),(UC_ARM_REG_R2,RADIO+0x1e),(UC_ARM_REG_R3,0x2002e00c),
                (UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,0x11111)):
        mu.reg_write(r,v)
    mu.emu_start(0xa966|1,0x11110,count=20000)
    for h in hs: mu.hook_del(h)
    return mu.reg_read(UC_ARM_REG_R0)&0xff
def setup(mu,monitor):
    mu.mem_write(RXDRV,bytes(0x40))
    mu.mem_write(RXDRV+4,bytes([0x38,0x14]))          # noise/glitch limits (UHF, 25k) from 0xacf8
    mu.mem_write(RXDRV+0x1c,struct.pack('<HH',68,70)) # level-0 open/close RSSI, table 0x6770c (UHF)
    mu.mem_write(RADIO,bytes(0x200))
    mu.mem_write(RADIO+8,bytes([2 if monitor else 0]))
    mu.mem_write(CFG,bytes(0x40))
def sq(mu): return mu.mem_read(RXDRV,1)[0]&1
EMPTY={0x67:60,0x65:80,0x63:40,0x0c:0}   # RSSI, noise, glitch, no IRQ
STRONG={0x67:200,0x65:5,0x63:2,0x0c:0}

print('--- 2. RX status poll emulation (UHF channel, squelch level 0 = monitor) ---')
res={}
for name,img in (('stock',base),('fixed',mod)):
    mu=mkemu(img)
    setup(mu,False); [run_poll(mu,EMPTY) for _ in range(8)]; a=sq(mu)
    setup(mu,True);  [run_poll(mu,EMPTY) for _ in range(8)]; b=sq(mu)
    setup(mu,False); [run_poll(mu,STRONG) for _ in range(8)]; c=sq(mu)
    setup(mu,True);  run_poll(mu,EMPTY); first=sq(mu)
    mu.mem_write(RADIO+8,b'\0'); [run_poll(mu,EMPTY) for _ in range(8)]; e=sq(mu)
    res[name]=(a,b,c,first,e)
    print(f'  {name:5}: empty/mon-off={a}  empty/mon-on={b}  strong/mon-off={c}  mon-on 1st poll={first}  then mon-off={e}')
s,f=res['stock'],res['fixed']
checks=[('normal squelch unchanged on empty channel', s[0]==f[0]==0),
        ('stock monitor fails on empty UHF channel (bug reproduced)', s[1]==0),
        ('fixed monitor opens on empty channel', f[1]==1),
        ('fixed monitor opens on the first poll', f[3]==1),
        ('normal signal still opens squelch', s[2]==f[2]==1),
        ('squelch closes again after monitor off', f[4]==0)]
for t,c in checks:
    ok&=c; print(f'  {"OK  " if c else "FAIL"} {t}')
print(); print('RESULT:','ALL CHECKS PASS' if ok else 'FAILURES PRESENT')
sys.exit(0 if ok else 1)
