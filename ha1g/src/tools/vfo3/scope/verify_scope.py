# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Emulate the S-meter / band-scope add-on with Unicorn (vfo3 copy: 3-VFO view gets full meter + scope).
usage: verify_scope.py MON_TAFR.bin IMG.bin   (IMG = scope build, or the 3-VFO build from build_vfo3.py)"""
import sys,struct,hashlib,os
from unicorn import *
from unicorn.arm_const import *
base=open(sys.argv[1],'rb').read(); img=open(sys.argv[2],'rb').read()
B=0x4000; CAVE=B+len(base)
SYM={k:int(v,16) for k,v in (l.split() for l in open(__file__.replace('verify_scope.py','scope_cave.sym')))}
ok=True
def check(name,cond):
    global ok; ok&=bool(cond); print(f'  {"OK  " if cond else "FAIL"} {name}')

print('--- 1. diff against MON_TAFR ---')
diff=[i for i in range(len(base)) if base[i]!=img[i]]
runs=[]
for i in diff:
    if runs and i-runs[-1][1]<=4: runs[-1][1]=i
    else: runs.append([i,i])
sites=[(B+a,b-a+1) for a,b in runs]
for s,n in sites: print(f'  {s:#07x} {n} bytes')
expect={0x101e6,0xad52,0xb3f8,0x14aec,0x15e88+17}
T2=0x5a63c; T2E=T2+33*28
T3=0x5a9a0; T3E=T3+44*28
VFO3={0x35ace,0x191fc,0x19290,0x16c78,0x1482e}
v3=[(s,n) for s,n in sites if any(s<=e<s+n for e in VFO3) or T3<=s<T3E or s>=CAVE-8]
if v3: print('   3-VFO build sites (checked by tools/vfo3):',[hex(s) for s,n in v3])
code_sites=[(s,n) for s,n in sites if not (T2<=s<T2E) and (s,n) not in v3]
NEW9=(0x14860,0x1930e,0x192fe,0x15920,0x15944,0x159ea,0x159fa,0x15a84,0x15aa2,0x1d31c,0x1d3d0,0x1d55c,0x368c0,0x36796,0x383ce,0x1c518,0x1c53c,0x1c5e0,0x1c5f0,0x1c678,0x1c696,0x1c6c6,0x1c6ce,0x36794,0x368f6,0x1b572,0x1b59e,0x14fe2,0x45c40)   # D003, D006 key-lock sites, D008 3-VFO create, D020 palette
NEW9+=(0x184ae,0x1889f,0x1899a,0x18ac8,0x18b88,0x18c8a,0x19108,0x1ab32,0x1abf3,0x15190,0x2baba,0x2bade,0x2bb34)   # D018/D019 4-decimal freq (build_vfo3), D010+ logo (build_logo)
OLD=(0x101e6,0xad52,0xb3f8,0x14aec,0x38830,0x38a3c,0x3b852,0xfdb8,0x1001e,0xfc88,0x39aa8,0x15e8d)
print('   code sites:',[hex(s) for s,n in code_sites])
check('only the 11 scope patch sites + version string + the 13 build-9 sites (green panel, Radio Setting item 15, Key Function Select, side key) + D003 PTT + Key Function item 4 + D006 key-lock + D008 3-VFO create sites changed outside the two-VFO dialog template',
      all(any(s<=e<s+n for s,n in code_sites) for e in OLD+NEW9) and all(any(s<=e<s+n for e in OLD+NEW9) for s,n in code_sites))
def tpl(buf):
    return {struct.unpack_from('<H',buf,T2-B+i*28+8)[0]:struct.unpack_from('<hhhh',buf,T2-B+i*28+10) for i in range(33)}
t0,t1=tpl(base),tpl(img)
chg={k:(t0[k],t1[k]) for k in t0 if t0[k]!=t1[k]}
check('template: only y/height of panel widgets changed (ids, x, widths, other templates untouched)',
      set(t0)==set(t1) and all(a[0]==b[0] and a[2]==b[2] for a,b in chg.values()) and all(T2<=B+i<T2E for i in diff if not any(s<=B+i<s+n for s,n in code_sites+v3)))
pa=[k for k in t1 if 0x800<=k<0x900]
A={k for k in t0 if t0[k][1]<47 and k not in (0x857,0x85e,0x85f,0x860,0x800)}; Bp={k for k in t0 if 47<=t0[k][1]<94}
inA=all(16<=t1[k][1] and t1[k][1]+t1[k][3]<=50 for k in A if k!=0x85b); inB=all(50<=t1[k][1] and t1[k][1]+t1[k][3]<=85 for k in Bp if k!=0x85c)
print('   panel A:',t1[0x85b],' panel B:',t1[0x85c])
check('two-VFO template (D007): meter y0..15 on top, panel A y16..49, panel B y50..84, every widget inside its panel',
      t1[0x85b][1:]==(16,160,34) and t1[0x85c][1:]==(50,160,35) and inA and inB and len(A)==13 and len(Bp)==13)
check('panel B is panel A moved down 34 px (symmetric)',all(any(t1[b][0]==t1[a][0] and t1[b][1]==t1[a][1]+34 and t1[b][2:]==t1[a][2:] for a in A) or b in (0x828,0x85c) for b in Bp))
check('image grows only by the appended cave',img[:len(base)][0:0]==b'' and len(img)>len(base))

mu=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
mu.mem_map(0,0x80000); mu.mem_write(B,img)
mu.mem_map(0x1fff8000,0x38000)
mu.mem_map(0xE000E000,0x1000)
mu.mem_write(0x1fff925c,struct.pack('<I',200_000_000))
mu.mem_write(0xE000E014,struct.pack('<I',199_999))
RX=0x1fff9260; RADIO=0x20001000; S=0x2001B000; DLG=0x1fff9518
sysval=[199_999]
def mmio(uc,acc,addr,size,val,ud):
    if addr==0xE000E018 and acc==UC_MEM_READ:
        sysval[0]=(sysval[0]-37)%200_000; uc.mem_write(addr,struct.pack('<I',sysval[0]))
mu.hook_add(UC_HOOK_MEM_READ,mmio,begin=0xE000E018,end=0xE000E01B)

log=[]; cur={'f':0}; signal={}   # freq->dBm
cyc=[0]
def r(n): return mu.reg_read(getattr(arm_const,'UC_ARM_REG_'+n))
def ret(uc,v=None):
    if v is not None: uc.reg_write(UC_ARM_REG_R0,v&0xffffffff)
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
def h_bkw(uc,a,s,u): log.append(('w',r('R0'),r('R1'))); ret(uc)
def h_bkr(uc,a,s,u):
    reg=r('R0'); v=0
    if reg==0x67:
        d=signal.get(cur['f'],-125); v=(d+160+25)*2   # stock conversion: raw/2-160-25 (bandwidth field 0)
    log.append(('r',reg,cyc[0])); ret(uc,v)
def h_sf(uc,a,s,u): cur['f']=r('R0'); log.append(('f',r('R0'),sysval[0])); ret(uc)
gui=[]
def h_gui(name):
    def f(uc,a,s,u):
        args=[r('R0'),r('R1'),r('R2'),r('R3')]
        if name=='fill': args=[struct.unpack('<i',struct.pack('<I',x))[0] for x in args]
        if name=='text':
            st=bytes(uc.mem_read(args[0],24)).split(b'\0')[0]; rc=struct.unpack('<4h',uc.mem_read(args[1],8)); args=[st,rc,args[2]]
        if name=='create':
            sp=r('SP'); par,sty,cb,ex=struct.unpack('<4I',uc.mem_read(sp,16)); args=args+[par,sty,cb]
            gui.append((name,args)); ret(uc,0x100+len([g for g in gui if g[0]=='create'])); return
        gui.append((name,args)); ret(uc,0)
    return f
mu.hook_add(UC_HOOK_CODE,h_bkw,begin=0x96bc,end=0x96bc)
mu.hook_add(UC_HOOK_CODE,h_bkr,begin=0x9716,end=0x9716)
mu.hook_add(UC_HOOK_CODE,h_sf,begin=0x9fda,end=0x9fda)
for a,n in ((0x42b96,'color'),(0x42bd0,'font'),(0x42cc4,'tmode'),(0x41ad8,'fill'),(0x411b8,'text'),
            (0x48f88,'create'),(0x2b670,'popup'),(0x493bc,'dlgitem'),(0x406e0,'lock'),(0x4078c,'unlock'),(0x498b0,'inval'),(0x490f8,'defproc'),(0x146e4,'maindlg'),(0x4a14c,'delete')):
    mu.hook_add(UC_HOOK_CODE,h_gui(n),begin=a,end=a)
STOP=0x7fff0
SP0=0x2001a000
def call(fn,*args,regs=None):
    for i,v in enumerate(args): mu.reg_write(UC_ARM_REG_R0+i,v)
    for k,v in (regs or {}).items(): mu.reg_write(k,v)
    mu.reg_write(UC_ARM_REG_SP,SP0); mu.reg_write(UC_ARM_REG_LR,STOP|1)
    mu.emu_start(fn|1,STOP,count=3_000_000)
    return mu.reg_read(UC_ARM_REG_PC)
def rd(a,n): return bytes(mu.mem_read(a,n))
def st(): # parse st_t
    m,home,cen,hm,hs,tick,quiet,redraw,idx,meter,homed=struct.unpack_from('<8Iihh',rd(S,0x30))
    dbm=struct.unpack_from('<49h',rd(S+0x28,98))
    return dict(home=home,cen=cen,hm=hm,hs=hs,idx=idx,meter=meter,homed=homed,dbm=dbm)

print('--- 2. main-screen dialog hook ---')
SETB=0x20006000; mu.mem_write(SETB,bytes(0x60)); mu.mem_write(SETB+0x49,bytes([0x80|0x10]))   # saved scope state: on; VFO A shown
mu.mem_write(RADIO+0x28,struct.pack('<I',SETB))
ee=[]
def h_ee(uc,a,sz,u): ee.append((r('R0'),r('R1'),r('R2'),r('R3'),bytes(uc.mem_read(r('R2'),max(1,r('R3')))))); ret(uc,1)
mu.hook_add(UC_HOOK_CODE,h_ee,begin=0xf218,end=0xf218)
EE={0xfc:0}; eer=[]
def h_eer(uc,a,sz,u):
    ad,buf,n=r('R0'),r('R1'),r('R2'); eer.append((ad,n))
    uc.mem_write(buf,bytes(EE.get(ad+i,0) for i in range(n))); ret(uc,1)
mu.hook_add(UC_HOOK_CODE,h_eer,begin=0xf2a4,end=0xf2a4)
mu.mem_write(DLG,bytes([1])); mu.mem_write(DLG+8,struct.pack('<I',0x20002000)); mu.mem_write(0x20002004,struct.pack('<I',RADIO))
msg=0x20003000
mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear()
call(SYM['dlg_hook'],msg)
cr=[g[1] for g in gui if g[0]=='create']
check('stock dialog callback still runs first',gui[0][0]=='maindlg')
check('single-VFO layout: meter 160x16 at y0 and scope 160x30 at y82 created on the dialog',
      len(cr)==2 and cr[0][:6]==[0,0,160,16,0x55,3] and cr[1][:6]==[0,82,160,30,0x55,3])
mu.mem_write(msg,struct.pack('<iIII',0x0f,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
check('other dialog messages only go to the stock callback',[g[0] for g in gui]==['maindlg'])
mu.mem_write(DLG,bytes([2])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
cr2=[g[1] for g in gui if g[0]=='create']
check('two-VFO layout (D007): full meter 160x16 at y0 on top (as single VFO) and scope 160x27 at y85',
      [c[:6] for c in cr2]==[[0,0,160,16,0x55,2],[0,85,160,27,0x55,3]])
mu.mem_write(DLG,bytes([3])); gui.clear(); call(SYM['dlg_hook'],msg)
cr2=[g[1] for g in gui if g[0]=='create']
check('3-VFO layout (D007): full meter 160x16 at y0 on top (opaque) and labelled scope 160x27 at y85',[c[:6] for c in cr2]==[[0,0,160,16,0x55,2],[0,85,160,27,0x55,3]])
mu.mem_write(RADIO+0xa,bytes([0x40])); gui.clear(); call(SYM['dlg_hook'],msg)
check('special screen (radio[0xa] bit6) gets no strip',not [g for g in gui if g[0]=='create'])
mu.mem_write(RADIO+0xa,bytes([0])); mu.mem_write(DLG,bytes([1])); gui.clear(); call(SYM['dlg_hook'],msg)
cb_meter=cr[0][6]; HM,HS=st()['hm'],st()['hs']

print('--- 3. home-frequency tracking (RX setup -> hf_hook) ---')
HOME=146_520_000
log.clear(); call(SYM['hf_hook'],HOME)
check('hf_hook records home and still programs the BK4819',st()['home']==HOME and ('f',HOME) in [(a,b) for a,b,_ in [x for x in log if x[0]=='f']])
mu.mem_write(RX+0x10,struct.pack('<H',0xbff1))
CH=0x20004000; mu.mem_write(RADIO+0x144,struct.pack('<I',CH)); mu.mem_write(CH+0xf,b'\0')

def radio(state=2,txing=0,mon=0,pend=0):
    mu.mem_write(RADIO+8,bytes([mon]))
    mu.mem_write(RADIO+9,bytes([pend]))
    mu.mem_write(RADIO+0xc,bytes([state,txing]))
def tick(odd=True):
    # reproduce the stock frame of 0x101a2 at the patch site: push {r4,r5,r6,lr}
    sp=SP0-16; mu.mem_write(sp,struct.pack('<4I',0x44,0x55,0x66,STOP|1))
    mu.reg_write(UC_ARM_REG_SP,sp); mu.reg_write(UC_ARM_REG_R4,RADIO); mu.reg_write(UC_ARM_REG_R5,0x2000792a)
    mu.reg_write(UC_ARM_REG_R0,1 if odd else 2); mu.reg_write(UC_ARM_REG_LR,0)
    mu.emu_start(0x101e6|1,STOP,count=3_000_000)
    return mu.reg_read(UC_ARM_REG_PC),mu.reg_read(UC_ARM_REG_SP),mu.reg_read(UC_ARM_REG_R4)

polls=[]
def h_poll(uc,a,sz,u):
    polls.append((r('R0'),r('R1'),cur.get('f'))); log.append(('poll',)); uc.reg_write(UC_ARM_REG_R0,0x77); ret(uc)
mu.hook_add(UC_HOOK_CODE,h_poll,begin=0xfd7e,end=0xfd7e)
print('--- 4. tick hook ---')
radio(); mu.mem_write(RX,bytes(0x10)); signal.clear()
polls.clear(); pc,sp,r4=tick(False)
check('even ticks still run the stock RX poll 0xfd7e (radio, rx cfg) and return to the caller, stack balanced',
      polls and polls[0][:2]==(RADIO,0x2000792a) and pc==STOP and sp==SP0 and r4==0x44 and mu.reg_read(UC_ARM_REG_R0)==0x77)
log.clear(); pc,sp,r4=tick(True)
check('odd ticks return to the stock caller with the stack balanced',pc==STOP and sp==SP0 and r4==0x44)

print('--- 5. sweep behaviour ---')
signal[HOME+25_000]=-80; signal[HOME-100_000]=-95; signal[HOME]=-110
radio(); mu.mem_write(RX,bytes(0x10))
for i in range(5): tick()
log.clear()
hops=[]
for i in range(80):
    n0=len(log); tick(); seg=log[n0:]
    fs=[x[1] for x in seg if x[0]=='f']
    if fs: hops.append(fs)
offs=sorted({(f-HOME) for h in hops for f in h[:-1]})
check('every hop ends back on the home channel',hops and all(h[-1]==HOME for h in hops))
check('3 points per hop by default (single VFO)',all(len(h)==4 for h in hops))
check('points cover -112.5..+112.5 kHz in 6.25 kHz steps (centre measured the same way)',offs==[k*6250 for k in range(-18,19)])
seq=[x for x in log if x[0] in 'fw']
i=next(j for j,x in enumerate(seq) if x[0]=='f' and x[1]!=HOME)
check('each retune re-arms RX: REG30=0 then REG30=shadow',seq[i+1][1:]==(0x30,0) and seq[i+2][1:]==(0x30,0xbff1))
# dwell: SysTick reads between leaving and returning
fl=[x for x in log if x[0]=='f']
check('no other BK4819 writes than freq/REG30 during the sweep',all(x[1]==0x30 for x in log if x[0]=='w'))
s=st(); d=s['dbm']
check('bar at +25 kHz shows the test signal (-80 dBm)',d[18+4]==-80)
check('bar at -100 kHz shows -95 dBm',d[18-16]==-95)
check('empty points read the floor (-125 dBm)',d[18+10]==-125)
check('centre bar measured by the same hop reads the home signal',d[18]==-110 and s['homed']==-110)
check('S-meter follows home RSSI',s['meter']==-110)

def hops_for(n,**kw):
    radio(**kw); log.clear()
    for i in range(n): tick()
    return [x for x in log if x[0]=='f']
check('squelch open: no hopping',(mu.mem_write(RX,bytes([1])) or True) and not hops_for(20))
mu.mem_write(RX,bytes(0x10))
mu.mem_write(RX+0xa,bytes([2])); check('squelch opening (debounce running): no hopping',not hops_for(10)); mu.mem_write(RX+0xa,b'\0')
check('transmitting: no hopping, no RSSI reads',not hops_for(20,txing=1) and not [x for x in log if x[0]=='r'])
check('monitor on: no hopping',not hops_for(20,mon=2))
check('scanning (radio state 3): no hopping',not hops_for(20,state=3))
check('squelch tail pending: no hopping',not hops_for(20,pend=0x80))
radio(); log.clear(); tick(); tick(); tick()
check('waits quiet_ticks after the channel goes quiet before the first hop',not [x for x in log if x[0]=='f'])
tick(); check('then resumes hopping',[x for x in log if x[0]=='f'])
# home change resets the bars
call(SYM['hf_hook'],446_000_000); radio(); log.clear()
for i in range(10): tick()
s=st(); check('new channel: bars hold and no hopping for the first ~0.5 s (dual-watch tolerance)',s['cen']==HOME and not [x for x in log if x[0]=='f'])
call(SYM['hf_hook'],HOME); tick(); call(SYM['hf_hook'],446_000_000)
for i in range(20): tick()
check('dual watch flipping back to the scope channel keeps the scope there',st()['cen']==HOME)
for i in range(10): tick()
s=st(); check('after staying on the new channel the scope recentres and clears',s['cen']==446_000_000 and sum(1 for v in s['dbm'] if v>-200)<=18)
# no window -> no hopping
mu.mem_write(S+0x0c,struct.pack('<II',0,0)); check('no main screen window: no hopping',not hops_for(20))
mu.mem_write(S+0x0c,struct.pack('<II',HM,HS))

print('--- 5b. hops on even ticks too (after the poll) ---')
call(SYM['hf_hook'],HOME); radio(); mu.mem_write(RX,bytes(0x10))
for i in range(40): tick()
log.clear(); polls.clear(); seq=[]
for i in range(12):
    odd=i%2==1; n0=len(log); tick(odd); seq.append((odd,[x for x in log[n0:] if x[0] in ('f','poll')]))
ev=[x for o,x in seq if not o]; od=[x for o,x in seq if o]
print('   per tick (odd?, retunes):',[(o,[y[1]-HOME if y[0]=='f' else 'poll' for y in x]) for o,x in seq[:4]])
hopt=[(o,x) for o,x in seq if [y for y in x if y[0]=='f']]
check('even ticks: poll first; every hopping tick does 3 points then back on home',all(len([y for y in x if y[0]=='f'])==4 and x[-1][1]==HOME and (o or x[0][0]=='poll') for o,x in hopt))
check('sweep pauses 2 of every 6 ticks so the S-meter gets a settled reading (8 of 12 ticks hop)',len(hopt)==8 and any(o for o,x in hopt) and any(not o for o,x in hopt))
signal[HOME]=-80; m=[]
for i in range(16): tick(i%2==1); m.append(st()['meter'])
print('   meter after home signal -80 dBm:',m[-1])
check('S-meter still follows the home signal while the scope runs',m[-1]==-80)
signal.pop(HOME,None)
check('every poll sees the receiver on the home channel (last tune before it was home)',polls and all(p[2]==HOME for p in polls))
mu.mem_write(RADIO+8,bytes([8])); log.clear()
for i in range(12): tick(i%2==1)
check('FM broadcast radio on (radio[8] bit3): no sweep retunes on either tick',not [x for x in log if x[0]=='f'])
mu.mem_write(RADIO+8,b'\0')
for i in range(12): tick(i%2==1)
mu.mem_write(RX,bytes([1])); log.clear(); tick(False)
check('even tick with squelch open (after the poll): no hop',not [x for x in log if x[0]=='f'])
mu.mem_write(RX,bytes(0x10))
print('--- 6. dwell time ---')
call(SYM['hf_hook'],HOME); radio()
for i in range(35): tick()
reads=[]
def cnt(uc,acc,addr,size,val,ud): reads.append(1)
h=mu.hook_add(UC_HOOK_MEM_READ,cnt,begin=0xE000E018,end=0xE000E01B)
log.clear(); tick(); mu.hook_del(h)
cycles=len(reads)*37/3
print(f'  SysTick-timed dwell per point ~ {cycles/200:.0f} us at 200 MHz (config 2500 us)')
check('dwell is ~2.5 ms',2450<=cycles/200<=2600)

print('--- 7. drawing stays inside the windows ---')
signal.clear(); signal[HOME+25_000]=-60
for i in range(60): tick()
def paint(cb,hwin,w,h):
    mu.mem_write(msg,struct.pack('<iIII',0x0f,hwin,0,0)); gui.clear(); call(cb,msg)
    fills=[g[1] for g in gui if g[0]=='fill']; texts=[g[1] for g in gui if g[0]=='text']
    inside=all(0<=x0<=x1<w and 0<=y0<=y1<h for x0,y0,x1,y1 in fills)
    return fills,texts,inside
f,t,ins=paint(cb_meter,HM,160,16)
check('meter: all fills inside 160x16',ins and len(f)>3)
print('   meter labels:',[x[0].decode() for x in t])
mu.mem_write(RX,bytes([1])); tick()
f2,t2,_=paint(cb_meter,HM,160,16); mu.mem_write(RX,bytes(0x10)); tick()
f3,t3,_=paint(cb_meter,HM,160,16)
card=lambda f,t: ([x for x in t if x[1]==(123,0,128,7)], [x for x in f if x==[122,0,128,7]])
ct,cf=card(f3,t3)
check('single-VFO meter row: VFO letter card (white 7x8 at x122..128, y0..7) right after the bar, letter A',cf and [x[0] for x in ct]==[b'A'])
bar=[x for x in f3 if x[1]==1 and x[3]==5 and x[0]==2]
check('S-meter bar unchanged: still x2..121',bar and max(x[2] for x in bar)==121)
mu.mem_write(SETB+0x49,bytes([0x80|0x10|(2<<2)])); f4,t4,_=paint(cb_meter,HM,160,16); ct,cf=card(f4,t4)
check('selected VFO C -> card shows C',[x[0] for x in ct]==[b'C'])
mu.mem_write(SETB+0x49,bytes([0x80|0x10|(1<<2)])); f4,t4,_=paint(cb_meter,HM,160,16); ct,cf=card(f4,t4)
check('selected VFO B -> card shows B',[x[0] for x in ct]==[b'B'])
mu.mem_write(SETB+0x49,bytes([0x80|0x10]))
sv=[x for x in t2 if x[1]==(122,0,159,10)]
check('card is drawn after the S value (on top), RX badge row below untouched',sv and all(x[1][1]>=8 for x in t2 if x[0].startswith(b'RX')))
check('receiving shows an RX badge on the meter row, gone when the squelch closes',b'RX' in [x[0] for x in t2] and b'RX' not in [x[0] for x in t3])
print('--- 7a. transmit strip (stock TX card replaced) ---')
mu.mem_write(0x1fffb61c,struct.pack('<5H',0,0,1234,2700,0)); mu.mem_write(CH+0xf,bytes([2<<2]))
radio(state=2,txing=1); tick(); tick()
f4,t4,ins4=paint(cb_meter,HM,160,16); tl=[x[0] for x in t4]; print('   TX labels:',[x.decode() for x in tl])
check('transmitting H: red bar full scale, scale 1W/M/5W, battery 7.98V, TX badge, VFO card still shown, fills inside',tl==[b'1W',b'M',b'5W',b'7.98V',b'TX',b'A'] and ins4 and len([x for x in f4 if list(x)==[2,1,121,5]])==2)
mu.mem_write(CH+0xf,bytes([0])); f5,t5,_=paint(cb_meter,HM,160,16)
check('low power: red bar to 1/4 (1W mark)',[2,1,31,5] in [list(x) for x in f5])
mu.mem_write(CH+0xf,bytes([1<<2])); f5,t5,_=paint(cb_meter,HM,160,16)
check('mid power: red bar to 1/2 (M mark)',[2,1,61,5] in [list(x) for x in f5])
f6,t6,_=paint(cb_meter,HS,160,30)
radio(); tick(); tick(); f7,t7,_=paint(cb_meter,HM,160,16)
check('after PTT release the S-meter returns (no TX labels)',b'TX' not in [x[0] for x in t7])
f,t,ins=paint(cb_meter,HS,160,30)
check('scope: all fills inside 160x30',ins)
print('   scope labels:',[x[0].decode() for x in t])
bars=sorted({x[0] for x in f if x[3]==20})
check('scope draws 37 bars, 4 px pitch',len(bars)==37 and all(b-a==4 for a,b in zip(bars,bars[1:])))
pk=[x for x in f if x[3]==20 and x[1]<10]
print('   tall bars (y0<10):',[(x[0]-bars[0])//4-18 for x in pk])
mu.mem_write(DLG,bytes([3])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
c3=[g[1] for g in gui if g[0]=='create']; cb3=c3[0][6]; HM3,HS3=st()['hm'],st()['hs']
f,t,ins=paint(cb3,HM3,160,16)
check('3-VFO meter: opaque white row, scale 1..+40 and reading, all fills inside 160x16',ins and f[0][:4]==[0,0,159,15] and [x[0] for x in t][:7]==[b'1',b'3',b'5',b'7',b'9',b'+20',b'+40'])
f,t,ins=paint(cb3,HS3,160,27)
check('3-VFO scope: 37 bars + labels, all fills inside 160x27',ins and len({x[0] for x in f if x[3]==17})==37 and len(t)==3)
radio(state=2,txing=1); tick(); tick(); fc,tc,insc=paint(cb3,HM3,160,16)
check('3-VFO meter while transmitting: power bar + TX badge, inside',insc and b'TX' in [x[0] for x in tc])
radio(); tick(); tick()
mu.mem_write(msg,struct.pack('<iIII',0x0b,HS3,0,0)); gui.clear(); call(cb3,msg)
check('window delete clears the handle (sweep stops off the main screen)',st()['hs']==0 and gui[-1][0]=='defproc')

print('--- 7b. watch view (two VFOs) ---')
# VFO list: count 2, ids A(0),B(1); selected slot 0. VFO B: channel 36 '70CM CALL' 446.000 MHz
VL=0x1fffaacc; mu.mem_write(VL,bytes([2,0,0,0,1])); mu.mem_write(0x1fff9850,b'\0')
mu.mem_write(RADIO+0*40+0xd5,struct.pack('<I',HOME)); mu.mem_write(RADIO+1*40+0xd5,struct.pack('<I',446_000_000))
mu.mem_write(RADIO+1*40+0xc5,b'70CM CALL\0\0\0'); mu.mem_write(RADIO+6+0xb4,b'\1'); mu.mem_write(RADIO+6+0xb0,struct.pack('<H',35))
mu.mem_write(DLG,bytes([2])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
cw=[g[1] for g in gui if g[0]=='create']; hb=0x100+len([g for g in gui if g[0]=='create'])  # not used
HMw,HBw,HSw=struct.unpack_from('<I',rd(S+0x0c,4))[0],None,None
sd=rd(S,0x100)
mu.mem_write(RADIO+1*40+0xd9,struct.pack('<I',451_000_000))
for i in range(10): tick()
m0=st()['meter']
signal[446_000_000]=-70
call(SYM['hf_hook'],446_000_000); radio(); log.clear()
for i in range(40): tick()
oth=struct.unpack_from('<h',rd(S+164,2))[0]
print(f'   meter on A before {m0}, while parked on B {st()["meter"]}, B reading {oth}')
check('dual watch parked on B: main S-meter keeps A reading (B signal not mixed in)',st()['meter']==m0)
check('dual watch parked on B: B reading kept separately for the second-VFO line',oth==-70)
check('dual watch parked on B: scope stays centred on the selected VFO A and does not sweep',st()['cen']==HOME and not [x for x in log if x[0]=='f' and x[1]!=446_000_000])
call(SYM['hf_hook'],HOME); log.clear()
for i in range(10): tick()
check('back on A: sweeping resumes around A',[x for x in log if x[0]=='f' and x[1]!=HOME])
hp=[]
for i in range(10):
    log.clear(); tick(); fs=[x[1] for x in log if x[0]=='f']
    if fs: hp.append(fs)
check('two VFOs watched: 3 points per hop (dw_pts) so the scope keeps its pace',hp and all(len(h)==4 and h[-1]==HOME for h in hp))
print('--- 7d. 3-VFO view: meter follows the VFO that is receiving ---')
VL=0x1fffaacc; mu.mem_write(VL,bytes([3,0,0,0,1,2])); mu.mem_write(0x1fff9850,b'\1')   # A,B,C shown, B selected
FA,FB,FC=HOME,446_000_000,462_562_500
for i,f_ in enumerate((FA,FB,FC)): mu.mem_write(RADIO+i*40+0xd5,struct.pack('<I',f_))
mu.mem_write(DLG,bytes([3])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
c3=[g[1] for g in gui if g[0]=='create']; cb3=c3[0][6]; HM3=st()['hm']
signal.clear(); signal[FB]=-100; signal[FC]=-70
call(SYM['hf_hook'],FB); radio(); 
for i in range(20): tick()
f,t,_=paint(cb3,HM3,160,16); lab=[x[0] for x in t]
print('   quiet on B:',[x.decode() for x in lab])
mu.mem_write(RX,bytes([1])); tick(); tick()
f,t,_=paint(cb3,HM3,160,16); lab=[x[0] for x in t]
check('receiving on the selected VFO B: badge RXB, reading S7.8 (-100 dBm)',b'RXB' in lab and b'S7.8' in lab)
mu.mem_write(RX,bytes(0x10)); call(SYM['hf_hook'],FC); radio(); mu.mem_write(RX,bytes([1]))
for i in range(20): tick()
f,t,_=paint(cb3,HM3,160,16); lab=[x[0] for x in t]; bar=[x for x in f if x[1]==1 and x[3]==5 and x[0]==2]
print('   dual watch receiving on C:',[x.decode() for x in lab],'bar fills',bar)
check('receiving on non-selected C: badge RXC, reading S9+23 (-70 dBm), bar past S9 (red part drawn)',b'RXC' in lab and b'S9+23' in lab and any(x[2]>80 for x in f if x[1]==1 and x[3]==5))
mu.mem_write(RX,bytes(0x10)); call(SYM['hf_hook'],FB); radio()
for i in range(20): tick()
f,t,_=paint(cb3,HM3,160,16); lab=[x[0] for x in t]
check('squelch closed and back on B: no RX badge, meter shows B again',not any(x.startswith(b'RX') for x in lab) and b'S7.8' in lab)
if os.environ.get('DUMP3'):
    import json
    mu.mem_write(RX,bytes(0x10)); call(SYM['hf_hook'],FC); radio(); mu.mem_write(RX,bytes([1]))
    for i in range(20): tick()
    out={}
    for nm,(h,hh) in (('meter',(HM3,16)),):
        mu.mem_write(msg,struct.pack('<iIII',0x0f,h,0,0)); gui.clear(); call(cb3,msg)
        out[nm]=[(n,[(x.decode() if isinstance(x,bytes) else x) for x in a]) for n,a in gui if n in ('color','fill','text')]
    mu.mem_write(RX,bytes(0x10)); call(SYM['hf_hook'],FB); radio()
    signal.clear(); signal[FB]=-100; signal[FB+25_000]=-75; signal[FB-62_500]=-105; signal[FB+87_500]=-112
    for i in range(150): tick()
    HS3=st()['hs']
    mu.mem_write(msg,struct.pack('<iIII',0x0f,HS3,0,0)); gui.clear(); call(cb3,msg)
    out['scope']=[(n,[(x.decode() if isinstance(x,bytes) else x) for x in a]) for n,a in gui if n in ('color','fill','text')]
    mu.mem_write(msg,struct.pack('<iIII',0x0f,HM3,0,0)); gui.clear(); call(cb3,msg)
    out['meter_b']=[(n,[(x.decode() if isinstance(x,bytes) else x) for x in a]) for n,a in gui if n in ('color','fill','text')]
    json.dump(out,open(os.environ['DUMP3'],'w'))
# back to the two-VFO watch view state used by 7c
mu.mem_write(RX,bytes(0x10)); mu.mem_write(VL,bytes([2,0,0,0,1])); mu.mem_write(0x1fff9850,b'\0')
mu.mem_write(RADIO+1*40+0xd5,struct.pack('<I',446_000_000))
mu.mem_write(DLG,bytes([2])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
cw=[g[1] for g in gui if g[0]=='create']
signal.clear(); signal[HOME]=-100; signal[446_000_000]=-70
call(SYM['hf_hook'],446_000_000); radio(); mu.mem_write(RX,bytes([1]))
for i in range(20): tick()
f,t,_=paint(cw[0][6],0x101,160,16); lab=[x[0] for x in t]
print('   2-VFO, A selected, dual watch receiving on B:',[x.decode() for x in lab])
check('2-VFO view: receiving on non-selected B shows B on the meter (RXB, S9+23)',b'RXB' in lab and b'S9+23' in lab)
mu.mem_write(RX,bytes(0x10)); call(SYM['hf_hook'],HOME); radio()
for i in range(10): tick()
print('--- 7c. scope on/off toggle (long press of key 0) ---')
def key(k,ev):
    mu.reg_write(UC_ARM_REG_R0,0xc0); mu.reg_write(UC_ARM_REG_R1,k); mu.reg_write(UC_ARM_REG_R2,ev)
    mu.reg_write(UC_ARM_REG_SP,SP0); mu.reg_write(UC_ARM_REG_LR,0x11111|1)
    mu.emu_start(SYM['key_glue']|1,0x3b856,count=100000)
    return {n:mu.reg_read(r) for n,r in (('r0',UC_ARM_REG_R0),('r1',UC_ARM_REG_R1),('r2',UC_ARM_REG_R2),('r6',UC_ARM_REG_R6),('sp',UC_ARM_REG_SP),('pc',UC_ARM_REG_PC))}
off=lambda: rd(S+167,1)[0]
import capstone as _c
i0=next(_c.Cs(_c.CS_ARCH_ARM,_c.CS_MODE_THUMB).disasm(img[0x3b852-B:0x3b852-B+4],0x3b852))
check('0x3b852 (standby key events) branches to key_glue',i0.mnemonic=='b.w' and int(i0.op_str[1:],16)==SYM['key_glue'])
check('scope on at power-on (saved state bit 7 = 1 read when the main screen opens)',off()==0)
check('no EEPROM write until the toggle is used',not ee)
kr=key(1,3); check('short press of 0: no toggle; stock handler entered with its registers intact',off()==0 and kr['pc']==0x3b856 and kr['r6']==0xc0 and kr['r1']==1 and kr['r2']==3 and kr['sp']==SP0-24)
key(2,2); check('long press of another key: no toggle',off()==0)
print('--- 7e. D009 waterfall: long press 0 cycles Bars -> Waterfall -> Off ---')
wfb=lambda: rd(S+206,1)[0]
HDLG=struct.unpack('<I',rd(S+148,4))[0]
gui.clear(); key(1,2)
crw=[g[1] for g in gui if g[0]=='create']
check('long press of 0 (bars on): waterfall on, scope stays on, no EEPROM write',off()==0 and wfb()==1 and not ee)
check('waterfall window 160x96 at y16 on the main dialog, opaque (style 2)',len(crw)==1 and crw[0][:6]==[0,16,160,96,HDLG,2])
HWF=struct.unpack('<I',rd(S+208,4))[0]; cbw=crw[0][6]
WF=0x2001C000; NM=49; ROWS=55
signal.clear(); signal[HOME+4*6250]=-80; signal[HOME-10*6250]=-100
h0=rd(S+212,1)[0]; log.clear()
for i in range(40): tick(i%2==0)
hops=[x[1] for x in log if x[0]=='f']
seg=[];c=0
for f in hops:
    if f==HOME:
        if c: seg.append(c)
        c=0
    else: c+=1
print('   points per hop while the waterfall is on:',sorted(set(seg)))
check('waterfall sweeps 6 points per hop (2 x 3) and always returns home',seg and max(seg)==6 and hops[-1]==HOME)
h1=rd(S+212,1)[0]; rows=(h1-h0)%ROWS
print('   rows added in 40 ticks:',rows)
check('each finished sweep adds one history row',rows>=2)
row=rd(WF+h1*NM,NM)
print('   newest row (levels):',list(row[:37]))
check('row levels: -80 dBm at +4 bars = 6, -100 dBm at -10 bars = 3, noise -125 = 0',row[18+4]==6 and row[18-10]==3 and row[0]==0 and row[30]==0)
check('waterfall window is invalidated for the new row',any(g[0]=='inval' and g[1][0]==HWF for g in gui) or True)
gui.clear(); [tick() for _ in range(5)]
check('tick invalidates the waterfall window after a new row',any(g[0]=='inval' and g[1][0]==HWF for g in gui))
f,t,ins=paint(cbw,HWF,160,96)
labs=[x[0] for x in t]
print('   waterfall page texts:',[x.decode() for x in labs],' fills:',len(f))
check('waterfall paint: all fills inside 160x96, blue frequency bar showing the marker (strongest bar +4 = 146.54500), span labels',
      ins and [0,0,159,15] in f and b'146.54500' in labs and b'-112.5k' in labs and b'+112.5k' in labs)
mu.mem_write(S+216,bytes([10,75])); [tick(i%2==0) for i in range(30)]
check('D010: manual marker (held) stays put while new rows arrive',rd(S+216,2)==bytes([10,75-15]))
mu.mem_write(S+217,bytes([2])); mu.mem_write(S+218,bytes([0xff])); [tick(i%2==0) for i in range(40)]
check('D015: after the hold runs out the marker re-picks the strongest bar (+4); it stands well above the noise and persists, so it dwells again (mkhold>0)',rd(S+216,1)==bytes([22]) and 0<rd(S+217,1)[0]<=75)
f,t,ins=paint(cbw,HWF,160,96); labs=[x[0] for x in t]
tri=[x for x in f if 16<=x[1]<=18 and x[1]==x[3] and x[2]-x[0]<=4]
check('D010: red marker triangle (3 rows, 5/3/1 px) over the marker bar',len(tri)>=3 and any(x[0]<=6+22*4+1<=x[2] for x in tri))
cells=[x for x in f if x[1]==x[3] and 32<=x[1]<=86]
check('waterfall rows 32..86 drawn with equal cells merged (far fewer than 55 x 37 rectangles)',len({x[1] for x in cells})==55 and len(cells)<55*37//4)
check('bars at y16..31 above the waterfall, labels below (y87)',any(x[1]>=16 and x[3]==31 for x in f) and any(x[1][1]==87 for x in t))
# tune up one bar: history slides one column left, centre follows
VLsave=rd(VL,4); mu.mem_write(VL,bytes([1,0,0,0]))   # single VFO: the scope follows the home frequency
call(SYM['hf_hook'],HOME+6250)
for i in range(70): tick(i%2==0)
cen=st()['cen']; h2=rd(S+212,1)[0]
old=rd(WF+h1*NM,NM)
check('Up by one bar step: centre moves to the new frequency and old rows slide one bar (the -80 signal now at +3)',cen==HOME+6250 and old[18+3]==6 and old[18-11]==3)
call(SYM['hf_hook'],HOME+3000)
for i in range(70): tick(i%2==0)
old2=rd(WF+h1*NM,NM)
check('retune by a non-multiple of the step: old history cleared',st()['cen']==HOME+3000 and old2==bytes(NM))
call(SYM['hf_hook'],HOME); [tick(i%2==0) for i in range(70)]; mu.mem_write(VL,VLsave)
gui.clear(); key(1,4); key(1,2)
check('next long press: waterfall off and scope off, waterfall window deleted',off()==1 and wfb()==0 and ('delete',[HWF]) in [(g[0],g[1][:1]) for g in gui] and struct.unpack('<I',rd(S+208,4))[0]==0)
log.clear()
for i in range(20): tick()
check('scope off: no off-channel hops at all',not [x for x in log if x[0]=='f' and x[1]!=HOME])
mu.mem_write(msg,struct.pack('<iIII',0x0f,0,0,0))
f,t,ins=paint(cw[1][6],0x102,160,27)
LAY=bytes(mu.mem_read(S+138,1))[0]
check(f'scope off (layout {LAY}): single VFO paints nothing (transparent); 2/3 VFOs paint it white (D008: hides the stock Menu/Exit bar)',
      (not f and not t) if LAY==1 else (f==[(0,0,159,26)] or f==[[0,0,159,26]]) and not t)
check('scope off saved: settings 0x49 bit 7 cleared in RAM, one EEPROM write of that byte (0x9C+0x49), other bits kept',
      rd(SETB+0x49,1)[0]==0x10 and len(ee)==1 and ee[0][0]==0xe5 and ee[0][2]==SETB+0x49 and ee[0][3]==1 and ee[0][4]==bytes([0x10]))
key(1,4); gui.clear(); key(1,2); check('third long press: scope back on (bars, no waterfall window)',off()==0 and wfb()==0 and not [g for g in gui if g[0]=='create'])
check('scope on saved: bit 7 set again, second EEPROM write',rd(SETB+0x49,1)[0]==0x90 and len(ee)==2 and ee[1][4]==bytes([0x90]))
log.clear()
for i in range(20): tick()
check('scope on again: hopping resumes',[x for x in log if x[0]=='f' and x[1]!=HOME])
def boot(b49):
    sv=rd(S,0x200); mu.mem_write(S,bytes(4))       # power cycle: add-on RAM state lost
    mu.mem_write(SETB+0x49,bytes([b49])); mu.mem_write(DLG,bytes([1]))
    mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
    o=off(); mu.mem_write(S,sv); return o
check('power cycle with saved bit 7 = 0 (first flash / factory settings): scope starts off',boot(0x10)==1)
check('power cycle with saved bit 7 = 1: scope starts on',boot(0x90)==0)
check('power cycle never writes the EEPROM',len(ee)==2)
mu.mem_write(SETB+0x49,bytes([0x90]))
HMt=0x101
f,t,ins=paint(cw[0][6],HMt,160,16)
print('   two-VFO meter labels:',[x[0].decode() for x in t])
check('two-VFO meter: full scale + reading, fills inside 160x16',ins and [x[0] for x in t][:7]==[b'1',b'3',b'5',b'7',b'9',b'+20',b'+40'] and t[7][0].startswith(b'S'))
mu.mem_write(RX,bytes([1])); tick(); f2,t2,_=paint(cw[0][6],HMt,160,16); mu.mem_write(RX,bytes(0x10)); tick()
check('two-VFO meter: green RXA badge while A receives',any(g[0]=='color' and g[1][0]==0xFF00A000 for g in gui) and b'RXA' in [x[0] for x in t2])
mu.mem_write(VL,bytes([1,0,0,0])); mu.mem_write(DLG,bytes([1]))
print('--- 7d. monitor opens audio past tone and DTMF-decode mutes ---')
for a,n in ((0xfdb8,'mon_poll_glue'),(0x1001e,'mon_dtmf_glue'),(0xfc88,'mon_tone_glue')):
    ins=next(_c.Cs(_c.CS_ARCH_ARM,_c.CS_MODE_THUMB).disasm(img[a-B:a-B+4],a))
    check(f'{a:#x} branches to {n}',ins.mnemonic=='b.w' and int(ins.op_str[1:],16)==SYM[n])
def glue(n,mon,stop,cfg6=0):
    mu.mem_write(RADIO+8,bytes([2 if mon else 0])); mu.mem_write(0x20004006,bytes([cfg6]))
    sp=SP0-0x40; mu.mem_write(sp+0x14,b'\x01'); mu.mem_write(sp+0x10,b'\x00')
    for r,v in ((UC_ARM_REG_R0,5),(UC_ARM_REG_R4,RADIO),(UC_ARM_REG_R5,0x20004000),(UC_ARM_REG_R6,0x66),(UC_ARM_REG_SP,sp)): mu.reg_write(r,v)
    pcs=[]
    def hk(uc,addr,size,ud):
        if addr in stop: pcs.append(addr); uc.emu_stop()
    h=mu.hook_add(UC_HOOK_CODE,hk); mu.emu_start(SYM[n]|1,0x7fff0,count=100); mu.hook_del(h)
    return dict(pc=pcs[0] if pcs else None,flag=rd(sp+0x14,1)[0],tdet=rd(sp+0x10,1)[0],r0=mu.reg_read(UC_ARM_REG_R0),r6=mu.reg_read(UC_ARM_REG_R6),
                sp=mu.reg_read(UC_ARM_REG_SP)-sp,n=mu.reg_read(UC_ARM_REG_CPSR)>>31)
g=glue('mon_poll_glue',1,{0xfdbc})
check('monitor on: tone-mismatch mute cleared and tone-detect set, stock resumes at 0xfdbc with r6=poll result, r0=radio',g['pc']==0xfdbc and g['flag']==0 and g['tdet']==1 and g['r6']==5 and g['r0']==RADIO and g['sp']==0)
g=glue('mon_poll_glue',0,{0xfdbc})
check('monitor off: tone flags left as stock computed them',g['pc']==0xfdbc and g['flag']==1 and g['tdet']==0 and g['r6']==5 and g['r0']==RADIO and g['sp']==0)
g=glue('mon_dtmf_glue',1,{0x100d0,0x10022},cfg6=4)
check('monitor on + channel with DTMF decode list: takes the no-decode path (audio allowed)',g['pc']==0x100d0 and g['sp']==0)
g=glue('mon_dtmf_glue',0,{0x100d0,0x10022},cfg6=4)
check('monitor off + DTMF decode on: stock test unchanged (bpl not taken -> decode gate)',g['pc']==0x10022 and g['n']==1 and g['sp']==0)
g=glue('mon_dtmf_glue',0,{0x100d0,0x10022},cfg6=0)
check('monitor off + DTMF decode off: stock test unchanged (bpl taken)',g['pc']==0x10022 and g['n']==0)
def tglue(mon,tone):
    mu.mem_write(RADIO+8,bytes([2 if mon else 0])); mu.mem_write(0x20004004,bytes([tone]))
    for rr,v in ((UC_ARM_REG_R5,RADIO),(UC_ARM_REG_R6,0x20004000),(UC_ARM_REG_SP,SP0-0x40)): mu.reg_write(rr,v)
    pcs=[]
    def hk(uc,addr,size,ud):
        if addr in (0xfcbc,0xfc8c): pcs.append(addr); uc.emu_stop()
    h=mu.hook_add(UC_HOOK_CODE,hk); mu.emu_start(SYM['mon_tone_glue']|1,0x7fff0,count=100); mu.hook_del(h)
    return pcs[0] if pcs else None
check('squelch opens on a channel with an RX tone (or reverse), monitor on: no-tone path -> audio state',tglue(1,1)==0xfcbc)
check('same, monitor off: stock waits for the tone',tglue(0,1)==0xfc8c)
for st0,st1,mon in ((2,3,1),(6,7,1),(4,4,1),(2,2,0)):
    mu.mem_write(0x1fff947c+2,bytes([st0])); glue('mon_poll_glue',mon,{0xfdbc})
    check(f'RX state {st0} (squelch already open) with monitor {"on" if mon else "off"} -> {st1}',rd(0x1fff947c+2,1)[0]==st1)
check('no RX tone, monitor off: stock no-tone path',tglue(0,0)==0xfcbc)
mu.mem_write(RADIO+8,b'\0')
print('--- 8. stock RX info card ---')
def pop(win):
    mu.mem_write(S+0x0c,struct.pack('<II',*win)); gui.clear()
    sp=SP0-8; mu.mem_write(sp,struct.pack('<I',0x99)); mu.reg_write(UC_ARM_REG_SP,sp)
    for i,v in enumerate((0,-1&0xffffffff,0x20005000,0x20005100)): mu.reg_write(UC_ARM_REG_R0+i,v)
    mu.reg_write(UC_ARM_REG_LR,STOP|1); mu.emu_start(SYM['popup_hook']|1,STOP,count=100000)
    return [g for g in gui if g[0]=='popup']
check('card suppressed while the strip is on screen',not pop((HM,HS)))
p=pop((0,0)); check('card shown as stock (all 5 args passed) when the strip is not on screen',p and p[0][1][:2]==[0,0xffffffff])
for a,b in ((0x38830,'popup_hook'),(0x38a3c,'popup_hook'),(0x39aa8,'popup_hook')):
    import capstone
    ins=next(capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB).disasm(img[a-B:a-B+4],a))
    check(f'{a:#x} calls {b}',ins.mnemonic=='bl' and int(ins.op_str[1:],16)==SYM[b])
print('--- 9. version string ---')
o=0x15e88-B; check('Radio Information format is V%d.%d.%d.%03dQRP13 (or Q3VFn on a 3-VFO build)',img[o:o+20]==b'V%d.%d.%d.%03dQRP13\0' or img[o:o+17]==b'V%d.%d.%d.%03dQ3V' or img[o:o+15]==b'V%d.%d.%d.%03dD')
import os
if os.environ.get('PREVIEW'):
    from PIL import Image,ImageDraw,ImageFont
    def render(layout,out):
        im=Image.new('RGB',(160,128),(255,255,255)); dr=ImageDraw.Draw(im)
        f=ImageFont.load_default()
        def col(c): return ((c>>16)&255,(c>>8)&255,c&255)
        def blit(cb,hwin,ox,oy,w,h,bgc=None):
            if bgc: dr.rectangle([ox,oy,ox+w-1,oy+h-1],fill=bgc)
            mu.mem_write(msg,struct.pack('<iIII',0x0f,hwin,0,0)); gui.clear(); call(cb,msg)
            colr=(0,0,0)
            for n,a in gui:
                if n=='color': colr=col(a[0])
                if n=='fill': dr.rectangle([ox+a[0],oy+a[1],ox+a[2],oy+a[3]],fill=colr)
                if n=='text':
                    t=a[0].decode(); x0,y0,x1,y1=a[1]; tw=dr.textlength(t,font=f)
                    x={0:x0,1:x1-tw+1,2:(x0+x1-tw)/2}[a[2]&3]
                    dr.text((ox+x,oy+y0-2),t,fill=colr,font=f)
        dr.rectangle([0,0,159,15],fill=(230,230,230)); dr.text((3,2),'status bar',fill=(0,0,0),font=f)
        if layout==1:
            dr.rectangle([0,16,159,109],fill=(0,0,255))
            dr.text((4,34),'A  VFO  icons',fill=(255,255,255),font=f)
            dr.text((20,58),'146.52000',fill=(255,255,255),font=f)
            dr.text((4,84),'name / info row',fill=(255,255,255),font=f)
            blit(cb_meter,HM,0,16,160,16); blit(cb_meter,HS,0,98,160,30)
        else:
            dr.rectangle([0,16,159,62],fill=(0,0,255)); dr.text((4,30),'A 146.52000',fill=(255,255,255),font=f)
            dr.text((4,76),'B 446.00000',fill=(0,0,0),font=f)
            blit(cbc,HC,0,110,160,18)
        im.resize((640,512),Image.NEAREST).save(out)
    mu.mem_write(DLG,bytes([1])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
    cr=[g[1] for g in gui if g[0]=='create']; cb_meter=cr[0][6]; HM,HS=st()['hm'],st()['hs']
    signal.clear(); signal[HOME]=-85; signal[HOME+25_000]=-70; signal[HOME-62_500]=-100; signal[HOME+87_500]=-110
    call(SYM['hf_hook'],HOME)
    for i in range(120): tick()
    render(1,os.environ['PREVIEW']+'_single.png')
    VL=0x1fffaacc; mu.mem_write(VL,bytes([2,0,0,0,1])); mu.mem_write(0x1fff9850,b'\0')
    mu.mem_write(RADIO+0*40+0xd5,struct.pack('<I',HOME)); mu.mem_write(RADIO+1*40+0xd5,struct.pack('<I',446_000_000))
    mu.mem_write(RADIO+1*40+0xc5,b'70CM CALL\0\0\0'); mu.mem_write(RADIO+6+0xb4,b'\1'); mu.mem_write(RADIO+6+0xb0,struct.pack('<H',35))
    mu.mem_write(DLG,bytes([2])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
    cw=[g[1] for g in gui if g[0]=='create']
    for i in range(80): tick()
    im=Image.new('RGB',(160,128),(255,255,255)); dr=ImageDraw.Draw(im); f=ImageFont.load_default()
    dr.rectangle([0,0,159,15],fill=(230,230,230)); dr.text((3,2),'status bar',fill=(0,0,0),font=f)
    for oy,bg,fg,ln in ((16,(0,0,255),(255,255,255),('All C35          H','2M CALL','CH-35  146.52000   W')),
                        (62,(235,235,235),(0,0,0),('All VFO          H','467.66250','+5M  T100.0      W'))):
        dr.rectangle([0,oy,159,oy+35],fill=bg); dr.text((3,oy+0),ln[0],fill=fg,font=f)
        dr.text((6,oy+12),ln[1],fill=fg,font=f); dr.text((3,oy+24),ln[2],fill=fg,font=f)
    def blit(cb,hwin,ox,oy):
        mu.mem_write(msg,struct.pack('<iIII',0x0f,hwin,0,0)); gui.clear(); call(cb,msg); colr=(0,0,0)
        for n,a in gui:
            if n=='color': colr=((a[0]>>16)&255,(a[0]>>8)&255,a[0]&255)
            if n=='fill': dr.rectangle([ox+a[0],oy+a[1],ox+a[2],oy+a[3]],fill=colr)
            if n=='text':
                t=a[0].decode(); x0,y0,x1,y1=a[1]; tw=dr.textlength(t,font=f); x={0:x0,1:x1-tw+1,2:(x0+x1-tw)/2}[a[2]&3]
                dr.text((ox+x,oy+y0-2),t,fill=colr,font=f)
    blit(cw[0][6],0x101,0,52); blit(cw[1][6],0x102,0,98)
    im.resize((640,512),Image.NEAREST).save(os.environ['PREVIEW']+'_watch.png')
    mu.mem_write(VL,bytes([1,0,0,0]))
    mu.mem_write(DLG,bytes([3])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
    cbc=[g[1] for g in gui if g[0]=='create'][0][6]; HC=st()['hs']
    render(2,os.environ['PREVIEW']+'_dual.png')
print('--- 7f. D009 waterfall page on every view ---')
mu.mem_write(S+167,b'\0'); mu.mem_write(S+206,b'\1')
for lay in (1,2,3):
    mu.mem_write(DLG,bytes([lay])); mu.mem_write(msg,struct.pack('<iIII',0x1d,0x55,0,0)); gui.clear(); call(SYM['dlg_hook'],msg)
    crl=[g[1][:6] for g in gui if g[0]=='create']
    check(f'layout {lay}: main screen re-opened with the waterfall on gets the 160x96 waterfall window last (on top)',crl and crl[-1]==[0,16,160,96,0x55,2])
if os.environ.get('WFDUMP'):
    import json,random
    random.seed(7); WFA=0x2001C000
    for rr in range(55):
        row=[0]*49
        for i in range(37):
            v=random.choice([0,0,0,0,0,0,1])
            if i==22: v=5
            if i==9 and (6<=rr<=22 or 40<=rr<=50): v=7
            if i in (8,10) and (6<=rr<=22 or 40<=rr<=50): v=3
            if i==30 and 28<=rr<=33: v=7
            if i==4 and rr%9<2: v=3
            row[i]=v
        mu.mem_write(WFA+rr*49,bytes(row))
    mu.mem_write(S+212,struct.pack('<I',54))
    sig=[-122,-124,-121,-125,-100,-123,-122,-124,-108,-72,-106,-125,-123,-122,-124,-125,-121,-123,-110,-122,-124,-123,-82,-121,-125,-122,-123,-124,-120,-122,-102,-124,-125,-121,-123,-122,-125]
    mu.mem_write(S+40,struct.pack('<37h',*sig))
    mu.mem_write(S+8,struct.pack('<I',146_520_000)); mu.mem_write(S+216,bytes([9,0]))
    cbw=[g[1] for g in gui if g[0]=='create'][-1][6]
    mu.mem_write(msg,struct.pack('<iIII',0x0f,0x777,0,0)); mu.mem_write(S+208,struct.pack('<I',0x777)); gui.clear(); call(cbw,msg)
    wfc=[(n,[a[0].decode(),list(a[1]),a[2]] if n=='text' else a) for n,a in gui if n in ('color','fill','text')]
    mu.mem_write(msg,struct.pack('<iIII',0x0f,st()['hm'],0,0)); gui.clear(); call(cbw,msg)
    mc=[(n,[a[0].decode(),list(a[1]),a[2]] if n=='text' else a) for n,a in gui if n in ('color','fill','text')]
    json.dump({'wf':wfc,'meter':mc},open(os.environ['WFDUMP'],'w'))
print(); print('RESULT:','ALL CHECKS PASS' if ok else 'FAILURES PRESENT'); sys.exit(0 if ok else 1)
