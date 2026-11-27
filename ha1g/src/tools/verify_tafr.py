# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Verify the TA/FR display fix by diffing and by CPU emulation.
usage: verify_tafr.py BASE.bin TAFR.bin
  BASE = the image build_tafr.py was given

Checks
  1. Only the three display sites, version string(s) and the appended caves differ.
  2. Radio side (identical on both images): emulates the RX frequency setup
     (0x10618) and the TX frequency/tone setup (0x10776) for a repeater
     channel with TA off / TA / FR, to show what each label really does.
  3. Display side: emulates the standby frequency (frequency mode, 0x18846),
     name-mode frequency (0x187d2) and the tone-type indicator (0x18dce),
     for RX and TX, on both images, and checks the fixed image shows the
     frequency/tone the radio actually uses.
"""
import sys,struct
from unicorn import *
from unicorn.arm_const import *
BASE=0x4000
base=open(sys.argv[1],'rb').read(); mod=open(sys.argv[2],'rb').read()
SITES={0x1884a:2,0x187da:4,0x18dd8:4}

print('--- 1. diff vs base ---')
diff=[i for i in range(len(base)) if base[i]!=mod[i]]
runs=[]
for i in diff:
    if runs and i==runs[-1][1]+1: runs[-1][1]=i
    else: runs.append([i,i])
ok=True
for s,e in runs:
    a=s+BASE
    if any(x<=a and e+BASE<x+n for x,n in SITES.items()): tag='display patch'
    elif b'%03d' in mod[max(0,s-18):e+3]: tag='version string'
    else: tag='UNEXPECTED'; ok=False
    print(f'  {a:#x}..{e+BASE:#x} ({e-s+1} bytes) {tag}')
print('  appended:',len(mod)-len(base),'bytes @',hex(BASE+len(base)))

RX,TX=0x44012500,0x44512500          # 440.125 / 445.125 (any distinct values)
RXT,TXT=0x4211,0x8222                # tone fields (type<<14 | code)
FLAGS={'none':0x00,'TA':0x10,'FR':0x08}

def rec(flag):
    r=bytearray(0x25)
    r[0x10:0x14]=struct.pack('<I',RX); r[0x14:0x18]=struct.pack('<I',TX)
    r[0x18]=RXT>>8; r[0x19]=RXT&0xff; r[0x1b]=TXT>>8; r[0x1c]=TXT&0xff
    r[0x1e]=flag
    return bytes(r)

def emu(img):
    mu=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
    mu.mem_map(0,0x80000); mu.mem_write(BASE,img)
    mu.mem_map(0x20000000,0x40000)
    return mu
def regs(mu,**kw):
    for k,v in kw.items(): mu.reg_write(getattr(arm_const,'UC_ARM_REG_'+k.upper()),v)
import unicorn.arm_const as arm_const
REC=0x20001000; OUT=0x20002000; RAD=0x20003000; DISP=0x20010000; SP=0x2003f000

def rf(img,flag):
    mu=emu(img); mu.mem_write(REC,rec(flag))
    regs(mu,r0=REC,r6=OUT,r7=OUT+0x100,r4=RAD,sp=SP)
    mu.emu_start(0x10618|1,0x1064a,count=200)
    rxf=struct.unpack('<I',mu.mem_read(OUT+0x14,4))[0]
    mu.mem_write(RAD+0x144,struct.pack('<I',REC))
    mu.mem_write(RAD+0x28,struct.pack('<I',RAD+0x400))
    regs(mu,r4=RAD,r6=OUT,r7=OUT+0x100,sp=SP)
    mu.emu_start(0x10776|1,0x10844,count=200)
    txf=struct.unpack('<I',mu.mem_read(OUT+0x14,4))[0]
    txt=(mu.reg_read(UC_ARM_REG_R8)<<14)|mu.reg_read(UC_ARM_REG_FP)
    return rxf,txf,txt

def disp(img,flag,tx):
    """returns (freq shown in frequency mode, freq shown in name mode, tone shown)"""
    mu=emu(img)
    slot=DISP+0xc0                      # display entry 0 (sl=0): 5-byte header + record
    mu.mem_write(slot+5,rec(flag)); mu.mem_write(slot+4,bytes([1 if tx else 0]))
    # frequency mode standby (stock clears the TX flag on this path)
    regs(mu,r5=DISP,r8=DISP,sl=0,sp=SP)
    mu.emu_start(0x18846|1,0x1892e,count=200); fmode=mu.reg_read(UC_ARM_REG_R7)
    # name mode
    mu.mem_write(slot+4,bytes([1 if tx else 0]))
    regs(mu,r8=DISP,sl=0,sp=SP)
    mu.emu_start(0x187d2|1,0x187f4,count=200); nmode=mu.reg_read(UC_ARM_REG_R5)
    # tone-type indicator: which field the code went on to show
    regs(mu,r5=DISP,sp=SP)
    ends={0x18e02:'TX tone',0x18de4:'TX tone',0x18e6a:'RX tone'}
    hit=[]
    def h(uc,addr,size,ud):
        if addr in ends: hit.append(ends[addr]); uc.emu_stop()
    hh=mu.hook_add(UC_HOOK_CODE,h)
    mu.emu_start(0x18dce|1,0x7fffe,count=200); mu.hook_del(hh)
    return fmode,nmode,hit[0] if hit else '?'

name=lambda f:{RX:'output (RX field)',TX:'input (TX field)'}.get(f,hex(f))
tname=lambda t:{RXT:'RX tone',TXT:'TX tone'}.get(t,hex(t))

print('\n--- 2. radio side (stock code, unchanged) ---')
for k,f in FLAGS.items():
    r=rf(base,f); m=rf(mod,f); assert r==m
    print(f'  {k:4}: receives on {name(r[0]):18}  transmits on {name(r[1]):18} with {tname(r[2])}')
    if k=='TA': assert r[0]==RX and r[1]==RX
    if k=='FR': assert r[0]==TX and r[1]==RX

print('\n--- 3. display ---')
for k,f in FLAGS.items():
    rxf,txf,txt=rf(base,f)
    for tx in (0,1):
        b=disp(base,f,tx); m=disp(mod,f,tx)
        want_f=txf if tx else rxf
        want_t=tname(txt) if tx else ('TX tone' if f==0x08 else 'RX tone')
        print(f'  {k:4} {"TX" if tx else "RX"}: stock shows freqmode={name(b[0]):18} namemode={name(b[1]):18} {b[2]}')
        print(f'  {"":4} {"":2}  fixed shows freqmode={name(m[0]):18} namemode={name(m[1]):18} {m[2]}')
        if not tx: ok&=(m[0]==want_f)
        ok&=(m[1]==want_f) and (m[2]==want_t)
        if f==0: ok&=(b==m)       # no TA/FR: identical to stock
print('\nRESULT:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
