/* SPDX-License-Identifier: GPL-3.0-or-later
   Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root. */
/* HA1G S-meter + band scope add-on (V1.01.14.002 MON_TAFR base).
 * Runs inside the stock Mmi task: the radio tick, the key handling (PTT) and
 * the emWin drawing all happen there, so nothing here races the stock code. */
typedef unsigned int u32; typedef int s32; typedef unsigned short u16;
typedef short s16; typedef unsigned char u8; typedef signed char s8;

/* ---------------- tunables (patched by build script, see CFG at cave start) --- */
typedef struct {
  u32 magic;          /* 'SCP1' */
  u32 enable;         /* 0 = add-on completely off (stock behaviour) */
  u32 step_hz;        /* scope step, default 6250 */
  u32 half_points;    /* bars each side of centre, default 18 -> 37 bars, +-112.5 kHz */
  u32 dwell_us;       /* settle time on each off-channel point before reading RSSI */
  u32 hop_ticks;      /* hop out every N radio ticks (1 tick ~ 20 ms) */
  u32 pts_per_hop;    /* off-channel points measured per hop */
  u32 redraw_ticks;   /* repaint every N radio ticks */
  s32 rssi_cal_db;    /* added to dBm = raw/2-160 */
  s32 floor_dbm;      /* scope bar zero */
  s32 top_dbm;        /* scope bar full */
  u32 quiet_ticks;    /* ticks to wait after squelch closes / retune before sweeping */
  u32 watch_view;     /* dual display (2 VFOs): show it as single view + one-line second VFO */
  u32 recentre_ticks; /* home must stay on a new frequency this long before the scope moves (dual watch) */
  u32 dw_pts;         /* points per hop while two VFOs are watched (receiver is only home half the time) */
  u32 dw_quiet;       /* quiet ticks needed after dual watch lands back on the selected VFO */
  u32 toggle_key;     /* internal key code whose long press turns the scope on/off (0 = no toggle) */
  u32 scope_on;       /* scope at power-on: 0 off, 1 on, 2 = last state, kept in settings byte 0x49 bit 7 (EEPROM 0xE5) */
  u32 even_hops;      /* also hop on even ticks, right after the stock RX poll */
  u32 meter_gap;      /* S-meter only reads after this many radio ticks with no hop (receiver settled) */
  u32 meter_every;    /* pause the sweep when this many odd ticks pass without a settled reading */
  s32 lock_margin;    /* D015: auto marker dwells 5 s on a peak standing at least this many dB above the sweep's average (a real signal, not a spike) */
} cfg_t;
extern const cfg_t CFG;

/* ---------------- stock firmware entry points ------------------------------ */
#define FN(a,t) ((t)((a)|1))
#define bk_write   FN(0x96bc,void(*)(u32,u32))
#define bk_read    FN(0x9716,u32(*)(u32))
#define bk_setfreq FN(0x9fda,void(*)(u32))
#define GUI_SetColor     FN(0x42b96,u32(*)(u32))
#define GUI_SetFont      FN(0x42bd0,const void*(*)(const void*))
#define GUI_SetTextMode  FN(0x42cc4,int(*)(int))
#define GUI_FillRect     FN(0x41ad8,void(*)(int,int,int,int))
#define GUI_DispStrRect  FN(0x411b8,void(*)(const char*,const void*,int,int))
#define WM_CreateChild   FN(0x48f88,u32(*)(int,int,int,int,u32,u32,void*,int))
#define WM_Invalidate    FN(0x498b0,void(*)(u32))
#define WM_DefaultProc   FN(0x490f8,void(*)(void*))
#define RxPopup          FN(0x2b670,void(*)(u32,u32,u32,u32,u32))
#define DLG_MainCb       FN(0x146e4,void(*)(void*))
#define WM_GetDlgItem    FN(0x493bc,u32(*)(u32,int))
#define ALLOC_LockH      FN(0x406e0,u8*(*)(u32))
#define ALLOC_UnlockH    FN(0x4078c,void(*)(u8**))
#define FONT8   ((const void*)0x68918)

#define RXDRV   ((volatile u8*)0x1fff9260)   /* [0]b0 squelch open, [0xa] debounce, [0x10] REG30 shadow */
#define MAINDLG ((volatile u8*)0x1fff9518)   /* [0] layout 1/2/3, [8] -> ctx (+4 -> radio) */
#define SYSCLK  (*(volatile u32*)0x1fff925c)
#define SYST_LOAD (*(volatile u32*)0xE000E014)
#define SYST_VAL  (*(volatile u32*)0xE000E018)

#define NMAX 49
typedef struct {
  u32 magic;
  u32 home;            /* last RX frequency set by stock code (Hz) */
  u32 scope_center;    /* frequency the bars belong to */
  u32 hw_meter, hw_scope;
  u32 tick, quiet, redraw;
  s32 idx;             /* next off-channel point, -half..+half */
  s16 meter_dbm;       /* smoothed home dBm (or -200 = no reading/TX) */
  s16 home_dbm;
  s16 dbm[NMAX];
  u8 layout, dirty, intx, txon;     /* txon: transmitting (TX strip shown) */
  u32 away;
  u32 hdlg;
  s32 corr;
  u8 rx, rxshown, pad2, pad3;
  u32 hw_bline;
  s16 other_dbm;       /* dual watch: last reading while parked on the non-selected VFO */
  u8 settle, scope_off; /* ticks to skip after a stock freq change; scope hidden + sweep stopped */
  u8 nohop, mdue;      /* ticks since the last hop; odd ticks since the last settled meter reading */
  s16 meter_t, other_t, last_raw; /* same readings in 0.1 dB (raw RSSI is 0.5 dB) for the S5.3-style label */
  u8 persist_ok, span, span_ok, rxslot; /* saved on/off read; span code (EEPROM 0xFC); panel painted green (0xff none) */
  u8 pg_val, pg_changed, pad7, pad8;   /* Radio Setting -> 15 Band Scope page */
  u32 pg_parent, pg_hwin, pg_ctx;
  /* D003: side-key PTT by VFO view + red TX panel */
  u8 pg_which, ptt_on, ptt_key, ptt_vfo;  /* page shown (0 Band Scope, 1 Side Key PTT); feature on; side keys held as PTT (bit0 SK1, bit1 SK2); VFO */
  u8 ptt_mine, txvfo, txset, hlcol;       /* next 0xd press is ours; VFO that transmits (valid if txset); panel colour 1 green 2 red */
  u8 txidle, rebuild, wf, wfnew;      /* D008: rebuild = re-create the 3-VFO screen on the next tick; D009: waterfall shown, new row to draw */
  u32 hw_wf; u32 wfhead;              /* D009: waterfall window, newest history row */
  u8 mk, mkhold, mklast, theme;       /* D010: marker bar; odd ticks holding a position (0=follows strongest). D015: mklast = strong peak seen last sweep (0xff none). D020: theme 0 Stock 1 Dark 2 Tactical */
  u32 pg_ov;                          /* D012: Band Scope / Side Key PTT list overlay window (repainted on selection change) */
} st_t;
#define S ((st_t*)0x2001B000)
#define SMAGIC 0x53430016u   /* D005: changed per build so a flash without a power cycle starts clean */

static void st_init(void){
  if (S->magic == SMAGIC) return;
  u8 *p=(u8*)S; for (u32 i=0;i<sizeof(st_t);i++) p[i]=0;
  for (int i=0;i<NMAX;i++) S->dbm[i]=-200;
  S->meter_dbm=-200; S->home_dbm=-200; S->other_dbm=-200; S->meter_t=-2000; S->other_t=-2000; S->scope_off=(CFG.scope_on!=1); S->rxslot=0xff; S->mklast=0xff; S->magic=SMAGIC;
}

static void th_install(void);   /* D020, below */

static void delay_us(u32 us){
  u32 clk=SYSCLK/1000000u; if (clk<8||clk>400) clk=200;
  u32 load=(SYST_LOAD&0xffffff)+1, need=us*clk, acc=0, prev=SYST_VAL;
  if (load<2){ for (volatile u32 i=0;i<us*40;i++); return; }
  u32 guard=0;
  while (acc<need && ++guard<2000000u){
    u32 cur=SYST_VAL;
    acc += (prev>=cur)? prev-cur : prev+load-cur;
    prev=cur;
  }
}

/* same conversion as the stock firmware's RSSI read-out (0x2b292):
   raw/2 - 160, minus 25 dB (19 dB when the channel's bandwidth field is 3) */
static s32 rssi_dbm(void){
  s32 raw=bk_read(0x67)&0x1ff; S->last_raw=(s16)raw;
  return raw/2-160+S->corr+CFG.rssi_cal_db;
}
static s32 last_tdb(void){ return S->last_raw*5-1600+(S->corr+CFG.rssi_cal_db)*10; }  /* last reading, 0.1 dB */
static s16 smooth_t(s16 m,s32 t,int reset){ return (s16)((reset || m<=-2000 || t>m)? t : (m*3+t)/4); }

#define VFOLIST ((volatile u8*)0x1fffaacc)    /* [0] count, [3..] VFO ids in panel order */
#define SELSLOT (*(volatile u8*)0x1fff9850)   /* highlighted panel slot */
static u8 *radio_ptr(void){
  u32 ctx=*(volatile u32*)(MAINDLG+8); return ctx? *(u8**)(ctx+4) : 0;
}
static u32 rd32(const u8*p){ return p[0]|(p[1]<<8)|(p[2]<<16)|((u32)p[3]<<24); }

/* scope on/off kept across power-off in bit 7 of global settings byte 0x49 (unused by stock and CHIRP:
   'rev_4'; every stock writer of 0x49 masks only bits 0-6).  Settings RAM copy = radio[0x28], loaded
   from EEPROM 0x9C (0x60 bytes) at boot; the stock page writer 0xf218(addr,_,buf,len) stores it back. */
#define EE_WRITE FN(0xf218,u32(*)(u32,u32,const u8*,u32))
#define SET_SCOPE 0x49
static u8 *settings_ptr(void){ u8 *r=radio_ptr(); return r? *(u8**)(r+0x28) : 0; }
/* scope span: 37 bars at 5 / 6.25 / 10 / 12.5 / 25 kHz.  Span code in EEPROM byte 0xFC (bits 0-2), just
   after the 0x60-byte settings block 0x9C..0xFB: no stock code reads or writes it (only the factory-reset
   copy of 100 bytes from 0xCCF4 covers it).  Code 0 (blank EEPROM / any other value) = 6.25 kHz. */
#define EE_READ FN(0xf2a4,u32(*)(u32,u8*,u32))
#define EE_SPAN 0xfc
static const u16 SPAN_STEP[5]={6250,5000,10000,12500,25000};
static u32 step_hz(void){ return S->span<5? SPAN_STEP[S->span] : CFG.step_hz; }
static void span_load(void){
  if (S->span_ok) return;
  if (!settings_ptr()) return;                 /* boot not finished */
  u8 b=0; EE_READ(EE_SPAN,&b,1);
  S->ptt_on = ((b>>3)&3)==1;                   /* D003: bits 3-4 = 01 -> side-key PTT on (blank 0xFF / 0x00 = off) */
  S->theme = (u8)((b>>5)&3); if (S->theme>2) S->theme=0;   /* D020: bits 5-6 = theme (blank 0xFF -> 3 -> Stock) */
  b&=7; S->span = b<5? b : 0; S->span_ok=1;
}
static void scope_reset(void){ S->quiet=0; S->scope_center=0; for (int i=0;i<NMAX;i++) S->dbm[i]=-200; }
static void scope_load(void){
  span_load();
  if (S->persist_ok || CFG.scope_on!=2) return;
  u8 *st=settings_ptr(); if (!st) return;
  S->scope_off = !(st[SET_SCOPE]&0x80); S->persist_ok=1;
}
static void scope_save(void){
  if (CFG.scope_on!=2) return;
  u8 *st=settings_ptr(); if (!st) return;
  u8 v = S->scope_off? (st[SET_SCOPE]&0x7f) : (st[SET_SCOPE]|0x80);
  if (v==st[SET_SCOPE]) return;
  st[SET_SCOPE]=v; EE_WRITE(0x9c+SET_SCOPE,1,st+SET_SCOPE,1);
}

/* stock RX setup calls this instead of bk_setfreq: remember the home channel */
void hf_hook(u32 hz){
  st_init();
  if (S->home!=hz){ S->home=hz; S->quiet=0; S->settle=2; }
  bk_setfreq(hz);
}

static void retune(u32 hz){
  bk_setfreq(hz);
  bk_write(0x30,0);
  bk_write(0x30,*(volatile u16*)(RXDRV+0x10));
}

static int npts(void){ u32 h=CFG.half_points; if (h>(NMAX-1)/2) h=(NMAX-1)/2; if(h<1)h=1; return (int)h; }

/* D009 waterfall: history of quantised sweeps (level 0..7 per bar), ring of WF_ROWS rows of NMAX bytes in
   free RAM above the D008 template (0x2001C000..0x2001CA87) */
#define WF_ROWS 55
#define WF ((u8*)0x2001C000)
__attribute__((minsize,noinline)) static void wf_push(void){
  if (!S->wf) return;
  if (++S->wfhead>=WF_ROWS) S->wfhead=0;
  u8 *row=WF+S->wfhead*NMAX;
  int n=2*npts()+1, b=n/2; s32 sum=0; int cnt=0;
  for (int i=0;i<n;i++){ s32 d=S->dbm[i]; if (d>S->dbm[b]) b=i; if (d>-190){ sum+=d; cnt++; } }
  /* D022: colour relative to this sweep's average (the same reference as the marker lock): level 1 from
     4 dB above it, one level per 3 dB, 7 from 22 dB up (a 12 dB signal = cyan, a locked 15 dB peak = level 4).  Was absolute (-116 dBm and up), so a weak but
     audible signal that locked the marker could still be drawn as background. */
  s32 av = cnt? sum/cnt : -200;
  for (int i=0;i<NMAX;i++){ s32 d=S->dbm[i]-av; s32 q= (i>=n || d<4)? 0 : (d-1)/3; row[i]=(u8)(q>7?7:q); }
  S->wfnew=1;
  if (!S->mkhold){
    S->mk=(u8)b;   /* D010: marker on the strongest bar */
    /* D015: lock only on a peak that stands lock_margin dB above the sweep's average (a real signal, not a
       momentary spike or the noise floor) AND that was already the standout on the previous sweep, so a
       one-sweep spike cannot grab the 5 s dwell. */
    int strong = cnt && (S->dbm[b]-(s16)(sum/cnt) >= (s16)CFG.lock_margin);
    if (strong && S->mklast!=0xff && (int)S->mklast>=b-1 && (int)S->mklast<=b+1) S->mkhold=75;
    S->mklast = strong? (u8)b : 0xff;
  }
}
/* scope moves to a new centre: bars restart; the waterfall history slides sideways by whole bars (tuning
   by the bar step keeps what was seen), anything else clears it */
__attribute__((minsize)) static void recentre(u32 f){
  s32 st=(s32)step_hz(), df=(s32)(f-S->scope_center), k=99;
  if (S->scope_center && df%st==0) k=df/st;
  S->scope_center=f; S->idx=-npts(); S->away=0;
  for (int i=0;i<NMAX;i++) S->dbm[i]=-200;
  for (int r=0;r<WF_ROWS;r++){ u8 *row=WF+r*NMAX;
    if (k>=0){ for (int i=0;i<NMAX;i++) row[i]= i+k<NMAX? row[i+k] : 0; }
    else for (int i=NMAX-1;i>=0;i--) row[i]= i+k>=0? row[i+k] : 0;
  }
  S->wfnew=1;
}

/* one hop: measure n points of the sweep, then straight back to the home channel */
static void hop_maybe(int busy, u32 want){
  int oncentre = S->home && S->home==S->scope_center;
  u32 qt = want? CFG.dw_quiet : CFG.quiet_ticks;
  if (S->scope_off || busy || !oncentre || S->quiet<=qt) return;
  if (CFG.meter_every && S->mdue>=CFG.meter_every) return;   /* let the meter take a settled reading first */
  S->nohop=0;
  int h=npts();
  if (S->idx<-h || S->idx>h) S->idx=-h;
  u32 n=want? CFG.dw_pts : CFG.pts_per_hop; if (S->wf) n*=2; if(n<1)n=1; if(n>8)n=8;   /* D009: waterfall sweeps twice as fast */
  for (u32 k=0;k<n;k++){
    u32 f=S->home+(u32)(S->idx*(s32)step_hz());
    retune(f);              /* centre point too, so all bars are measured the same way */
    delay_us(CFG.dwell_us);
    S->dbm[h+S->idx]=(s16)rssi_dbm();
    if (++S->idx>h){ S->idx=-h; wf_push(); }   /* D009: a finished sweep is one waterfall row */
  }
  retune(S->home);           /* straight back to the home channel */
}

static u32 want_freq(void){
  u32 want=0;
  if (VFOLIST[0]>=2){ u8 *rp=radio_ptr(); u8 sl=SELSLOT; if (rp && sl<VFOLIST[0]) want=rd32(rp+(VFOLIST[3+sl]&3)*40+0xd5); }
  return want;
}

/* called on even ticks right after the stock RX poll (0xfd7e) has run, so the squelch state is
   fresh; the next poll is two ticks away and the odd-tick hop still leaves a full tick on the
   home channel before it.  No meter/quiet bookkeeping here: that stays on the odd tick. */
void scope_tick_even(u8 *r){
  st_init();
  if (S->nohop<255) S->nohop++;
  if (!CFG.enable || !CFG.even_hops) return;
  if (!(S->hw_scope || S->hw_meter)) return;
  int tx = (r[0xd]==1);
  int busy = tx || r[0xc]!=2 || (RXDRV[0]&1) || RXDRV[0xa] || (r[8]&2) || (r[8]&8) || (r[9]&0x80);
  if (busy){ S->quiet=0; return; }
  u32 want=want_freq();
  if (want && S->scope_center!=want) return;     /* odd tick recentres first */
  hop_maybe(0,want);
}

static void rx_panels(int force);
static void main_rebuild(void);
/* called from the radio tick (odd ticks, polls run on even ones); r = radio struct */
void scope_tick(u8 *r){
  st_init(); th_install();
  if (!CFG.enable) return;
  S->tick++;
  if (S->nohop<255) S->nohop++;
  int tx = (r[0xd]==1);
  { u8 *ch=*(u8**)(r+0x144); S->corr = !ch ? -7 : ((ch[0xf]&3)==3 ? -19 : -25); }
  { u8 rx = !tx && (RXDRV[0]&1); if (rx!=S->rx){ S->rx=rx; S->dirty=1; S->tick=0; } }
  if (S->rebuild){ S->rebuild=0; main_rebuild(); }
  if (S->mkhold && !--S->mkhold) S->wfnew=1;   /* D010: manual marker released after ~5 s */
  int haswin = S->hw_scope || S->hw_meter;
  if (!haswin) { S->quiet=0; return; }

  /* with two VFOs watched, the scope always belongs to the selected VFO */
  u32 want=want_freq();
  /* the meter belongs to the selected VFO only: dual watch alternates the
     receiver between VFOs, so readings taken while parked on the other one
     go to other_dbm (shown on the second-VFO line), and the first ticks after
     any stock frequency change are skipped while the AGC settles */
  if ((u8)tx!=S->txon){ S->txon=(u8)tx; S->dirty=1; S->tick=0; if (!tx) S->txset=0; }
  if (tx) S->txidle=0;
  else if (S->txset && ++S->txidle>30) S->txset=0;   /* PTT pressed but TX never started (~1 s) */
  rx_panels(0);                       /* green panel follows the VFO that receives */
  if (tx){ S->meter_dbm=-200; S->meter_t=-2000; S->home_dbm=-200; S->quiet=0; S->intx=1; S->dirty=1; }
  else if (S->settle){ S->settle--; }
  else if (S->nohop<=CFG.meter_gap){ if (S->mdue<255) S->mdue++; }  /* receiver still settling after a hop */
  else {
    S->mdue=0;
    s32 d=rssi_dbm();
    if (!want || S->home==want){
      S->home_dbm=(s16)d;
      S->meter_t=smooth_t(S->meter_t,last_tdb(),S->intx || S->meter_dbm<=-200);
      if (S->intx || S->meter_dbm<=-200 || d>S->meter_dbm) S->meter_dbm=(s16)d;
      else S->meter_dbm=(s16)((S->meter_dbm*3+d)/4);   /* fast attack, slow decay */
      S->intx=0;
    } else {
      S->other_t=smooth_t(S->other_t,last_tdb(),S->other_dbm<=-200);
      if (S->other_dbm<=-200 || d>S->other_dbm) S->other_dbm=(s16)d;
      else S->other_dbm=(s16)((S->other_dbm*3+d)/4);
    }
    S->dirty=1;
  }

  int busy = tx || r[0xc]!=2 || (RXDRV[0]&1) || RXDRV[0xa] || (r[8]&2) || (r[8]&8) || (r[9]&0x80);
  if (busy) S->quiet=0; else if (S->quiet<255) S->quiet++;

  if (want && S->scope_center!=want) recentre(want);
  if (!want && S->home && S->scope_center!=S->home){
    if (!S->scope_center || ++S->away>CFG.recentre_ticks) recentre(S->home);
  } else S->away=0;
  u32 ht=CFG.hop_ticks?CFG.hop_ticks:1;
  if ((S->tick%ht)==0) hop_maybe(busy,want);

  u32 rt=CFG.redraw_ticks?CFG.redraw_ticks:1;
  if ((S->tick%rt)==0 && S->dirty){
    S->dirty=0;
    if (S->hw_meter) WM_Invalidate(S->hw_meter);
    if (S->hw_scope && S->hw_scope!=S->hw_meter) WM_Invalidate(S->hw_scope);
  }
  if ((S->tick%rt)==0 && S->wfnew && S->hw_wf){ S->wfnew=0; WM_Invalidate(S->hw_wf); }   /* D009: new row / new centre */
}


/* ---------------- D020: themes (Radio Setting -> 16 Theme: Stock / Dark / Tactical) -----------------
   Every emWin colour goes through LCD_SetColor (0x46074) / LCD_SetBkColor (0x46004), which call through
   the colour-API pointer at RAM 0x1fffafdc (stock -> flash table 0x6f394: SetColor 0x54ff9, SetBkColor
   0x54f41, SetDrawMode 0x55019).  th_install() points it at TH_API, whose two wrappers recolour each
   colour for the theme before calling the stock functions, so stock menus, the top bar and our own
   screens all follow the theme with no per-screen patches.  Bitmap palettes (icons) go through th_pal
   (0x45c40).  Rules: neutral colours are inverted between the theme's text and background colours
   (white background -> dark, black text -> light; foreground white stays light, it is text on a
   coloured bar); coloured ones are sorted into blue / cyan / green / red / yellow and replaced by the
   theme's dark (background) or medium (foreground) shade of that class.  Output carries a signature in
   bits the RGB565 panel drops (R&7=5, G&3=2, B&7=6), so a colour read back and set again (GUI_GetColor)
   is not mapped twice.  Our code tags colours in the alpha byte: 0xFE = use the background rule even
   via SetColor (fills of backgrounds), 0xFD = final colour, do not touch (waterfall palettes). */
typedef struct { u8 bg[3], fg[3], hi[3]; u8 cb[5][3], cf[5][3]; } theme_t;
static const theme_t THEMES[2]={
  { {14,16,20},{215,220,228},{235,240,250},                                   /* Dark */
    {{28,48,92},{30,36,48},{0,84,36},{118,0,0},{100,90,0}},
    {{100,140,225},{0,130,170},{0,150,55},{200,40,40},{190,170,0}} },
  { {22,20,14},{196,186,146},{222,214,176},                                   /* Tactical */
    {{58,68,36},{48,42,28},{34,78,26},{110,34,18},{110,96,30}},
    {{150,138,82},{190,150,40},{84,130,40},{170,60,30},{200,170,60}} },
};
#define TH_SIG 0x050206u
#define TH_SIGM 0x070307u
static u32 th_rgb(const u8 *c,u32 k){ return 0xFF000000u|((c[0]*k/255)<<16)|((c[1]*k/255)<<8)|(c[2]*k/255); }
static u32 th_lerp(const u8 *a,const u8 *b,u32 t){   /* a..b, t 0..255 */
  u32 r=0xFF000000u; for (int i=0;i<3;i++) r|=((a[i]*(255-t)+b[i]*t)/255)<<(16-8*i); return r; }
__attribute__((noinline)) u32 th_map(u32 c,int bgp){
  u32 a=c>>24; c|=0xFF000000u;
  if (a==0xFD) return c;
  if (a==0xFE) bgp=1;
  if (S->magic!=SMAGIC || !S->theme || S->theme>2) return c;
  if ((c&TH_SIGM)==TH_SIG) return c;            /* already ours */
  const theme_t *t=&THEMES[S->theme-1];
  u32 r=(c>>16)&255, g=(c>>8)&255, b=c&255, mx=r>g?r:g, mn=r<g?r:g, o;
  if (b>mx) mx=b; if (b<mn) mn=b;
  if (mx-mn<40 || (mx-mn)*3<mx){                /* neutral: white <-> background, black <-> text */
    u32 L=(r*77+g*150+b*29)>>8;
    o = (!bgp && L>=245)? th_rgb(t->hi,255) : th_lerp(t->fg,t->bg,L);
  } else {
    int k;
    if (b==mx) k = g*8>b*5? 1 : 0;              /* cyan / blue */
    else if (g==mx) k = r*8>g*5? 4 : 2;         /* yellow / green */
    else k = g*8>r*5? 4 : 3;                    /* yellow / red */
    o = th_rgb(bgp? t->cb[k] : t->cf[k], (mx+255)/2);
  }
  return (o&~TH_SIGM)|TH_SIG;
}
#define TH_SETCOLOR FN(0x54ff8,void(*)(u32))
#define TH_SETBK    FN(0x54f40,void(*)(u32))
#define TH_C2I      FN(0x45718,u32(*)(u32))
void th_setcolor(u32 c){ TH_SETCOLOR(th_map(c,0)); }
void th_setbk(u32 c){ TH_SETBK(th_map(c,1)); }
u32 th_pal(u32 c){ return TH_C2I(th_map(c,0)); }       /* 0x45c40: bitmap palette entry -> index */
const u32 TH_API[3]={(u32)th_setcolor, (u32)th_setbk, 0x55019};
#define TH_PTR (*(volatile u32*)0x1fffafdc)
static void th_install(void){ if (TH_PTR!=(u32)TH_API) TH_PTR=(u32)TH_API; }
/* tags for our own drawing (only when a theme is on, so Stock draws exactly as before) */
static u32 TBG(u32 c){ return S->theme? (c&0xFFFFFFu)|0xFE000000u : c; }   /* background rule */
static u32 TRAW(u32 c){ return S->theme? (c&0xFFFFFFu)|0xFD000000u : c; }  /* final colour */

/* ---------------- drawing --------------------------------------------------- */
#define C_BG    0xFFFFFFFFu
#define C_FG    0xFF000000u
#define C_GRID  0xFFB0B0B0u
#define C_SM    0xFF00A000u
#define C_SOVER 0xFFE00000u
#define C_BAR   0xFF1E3C8Cu
#define C_CBAR  0xFF00B2EDu
#define C_EMPTY 0xFFE8E8E8u
#define C_RX    0xFF00A000u

typedef struct { s16 x0,y0,x1,y1; } rect_t;
static void fill(u32 c,int x0,int y0,int x1,int y1){ if(x1<x0||y1<y0)return; GUI_SetColor(c); GUI_FillRect(x0,y0,x1,y1); }
static void text(const char*s,int x0,int y0,int x1,int y1,int al){ rect_t r={x0,y0,x1,y1}; GUI_DispStrRect(s,&r,al,0); }
static char *utoa_(u32 v,char*p){ char t[12];int n=0; do{t[n++]='0'+v%10;v/=10;}while(v); while(n)*p++=t[--n]; *p=0; return p; }

static int dbm_x(s32 d,int w){ /* S-meter: S1(-141) .. S9+40(-53) */
  s32 v=d+141; if(v<0)v=0; if(v>88)v=88; return (int)(v*w/88);
}
/* label from 0.1-dB value: below S9 one decimal (S5.3, 1 S-unit = 6 dB), from S9 up whole dB (S9+12) */
static void sname_t(s32 t,char*o){
  if (t<=-1990){ o[0]='-';o[1]='-';o[2]=0;return; }
  o[0]='S';
  if (t<-930){ s32 v=t+1470; if(v<0)v=0; v/=6; if(v>89)v=89; o[1]='0'+v/10; o[2]='.'; o[3]='0'+v%10; o[4]=0; }
  else { o[1]='9'; s32 over=(t+930)/10; if(over<1){o[2]=0;return;} o[2]='+'; utoa_((u32)over,o+3); }
}

static u32 panel_bg(void){
  u32 c=C_BG;
  if (S->layout>=2) return C_BG;     /* watch view / 3-VFO: meter has its own white row */
  if (S->hdlg){ u32 h=WM_GetDlgItem(S->hdlg,0x85b);
    if (h){ u8 *p=ALLOC_LockH(h); if (p){ c=*(u32*)(p+0x38); ALLOC_UnlockH(&p);} } }
  return c|0xFF000000u;
}
static u32 th_mix(u32 bg,u32 fg);
static u32 lum(u32 c){ return ((c>>16)&255)*3+((c>>8)&255)*6+(c&255); }   /* 0..2550 */
static u32 mix(u32 a,u32 b){ /* 3/4 a + 1/4 b */
  u32 r=0xFF000000u; for (int s=0;s<24;s+=8){ u32 x=((a>>s)&255)*3+((b>>s)&255); r|=((x/4)&255)<<s; } return r; }
/* D020: empty meter bar = mix of the themed background and text colours */
static u32 th_mix(u32 bg,u32 fg){ return S->theme? TRAW(mix(th_map(bg,1),th_map(fg,0))) : mix(bg,fg); }

/* ---- transmit strip: replaces the meter while PTT is held (no SWR hardware on this radio) ----
   power level from the channel record (byte 0x0f bits 3-2: 0 L, 1 M, 2 H), battery voltage from the
   stock battery ADC result buffer (ch3, V = raw*3.288/4096*302/82, same as the stock battery task),
   and the raw 12-bit value of ADC ch2, which the stock firmware samples but never uses (test). */
#define ADCBUF ((volatile u16*)0x1fffb61c)       /* [2] ch2 (unused), [3] ch3 battery, [4] ch4 detect */
static u32 tx_pw(void){ u8 *r=radio_ptr(); u8 *ch=r? *(u8**)(r+0x144):0; return ch? (ch[0xf]>>2)&3 : 3; }
/* TX power bar: L ~1 W at 1/4, M (wattage not measured on the HA1G) at 1/2, H 5 W full scale */
static int tx_x(u32 pw,int bw){ return pw==0? bw/4 : pw==1? bw/2 : bw; }
static const char *tx_name(u32 pw){ return pw==0?"1W": pw==1?"M": pw==2?"5W":"?"; }
static void batt_text(char *p){ u32 mv=(u32)ADCBUF[3]*2956u/1000u; p=utoa_(mv/1000,p); *p++='.';
  *p++=(char)('0'+(mv/100)%10); *p++=(char)('0'+(mv/10)%10); *p++='V'; *p=0; }

/* letter of the VFO whose RX frequency is the receiver's current (home) frequency, 0 if none */
static char home_letter(void){
  u8 *rp=radio_ptr(); if (!rp || !S->home) return 0;
  u8 n=VFOLIST[0]; if (n>3) n=3;
  for (u8 i=0;i<n;i++){ u32 id=VFOLIST[3+i]&3; if (rd32(rp+id*40+0xd5)==S->home) return (char)('A'+id); }
  return 0;
}

/* selected VFO's letter, drawn right after the S-meter bar (bar ends x121, widest S value
   "S9+40" is right-aligned so it starts ~x130; scale labels/RX badge are below y8).
   D016: shown in 2/3-VFO too (empty space there) using dark text on the white top strip;
   single-VFO keeps the panel-coloured letter on a white card. */
static void vfo_card(u32 bg){
  u8 *st=settings_ptr(); if (!st) return;
  char b[2]; b[0]='A'+((st[0x49]>>2)&3); b[1]=0;
  if (b[0]>'C') return;
  fill(S->layout>=2? TBG(0xFFFFFFFFu) : 0xFFFFFFFFu,122,0,128,7);   /* D020: card = strip background in 2/3-VFO */
  GUI_SetFont(FONT8); GUI_SetTextMode(2);
  GUI_SetColor(S->layout>=2 ? C_FG : TBG(bg));
  text(b,123,0,128,7,2);
}

__attribute__((minsize)) static void draw_meter(int w){
  int bw = w-40;               /* bar width */
  int bx = 2, by0 = 1, by1 = 5;   /* bar y1-5, ticks y6, scale numbers y8-15 (1 px gap) */
  s32 d=S->meter_dbm, mt=S->meter_t;
  char vl=0;
  if (S->layout>=2 && S->rx){        /* 2/3 VFOs: while receiving, show the VFO that receives */
    vl=home_letter(); u32 want=want_freq();
    if (want && S->home!=want){ d=S->other_dbm; mt=S->other_t; }
  }
  int x = d<=-199?0:dbm_x(d,bw);
  int x9 = dbm_x(-93,bw);
  u32 bg = panel_bg();
  u32 fg = lum(bg)<1100 ? 0xFFFFFFFFu : C_FG;
  if (S->txon){                      /* transmit: same bar, solid red to the power level */
    u32 pw=tx_pw(); int x=tx_x(pw,bw);
    if (S->layout>=2) fill(TBG(C_BG),0,0,w-1,15);
    fill(th_mix(bg,fg),bx,by0,bx+bw-1,by1);
    fill(C_SOVER,bx,by0,bx+x-1,by1);
    int t1=bx+bw/4, t2=bx+bw/2, t3=bx+bw-1;
    fill(fg,t1,by1+1,t1,by1+1); fill(fg,t2,by1+1,t2,by1+1); fill(fg,t3,by1+1,t3,by1+1);
    GUI_SetFont(FONT8); GUI_SetTextMode(2); GUI_SetColor(fg);
    text("1W",t1-10,8,t1+10,15,2); text("M",t2-6,8,t2+6,15,2); text("5W",t3-20,8,t3+1,15,1);
    char b[10]; batt_text(b); text(b,w-38,0,w-1,10,1);
    fill(C_SOVER,w-24,8,w-2,15); GUI_SetColor(0xFFFFFFFFu); text("TX",w-24,8,w-2,15,2);
    vfo_card(bg);
    return;
  }
  if (S->layout>=2) fill(TBG(C_BG),0,0,w-1,15);
  fill(th_mix(bg,fg),bx,by0,bx+bw-1,by1);
  if (x>0){
    fill(C_SM,bx,by0,bx+(x<x9?x:x9)-1,by1);
    if (x>x9) fill(C_SOVER,bx+x9,by0,bx+x-1,by1);
  }
  {
    static const s8 tk[]={1,3,5,7,9};
    GUI_SetFont(FONT8); GUI_SetTextMode(2);
    char b[8];
    for (int i=0;i<5;i++){ int tx=bx+dbm_x(-141+(tk[i]-1)*6,bw); fill(fg,tx,by1+1,tx,by1+1);
      b[0]='0'+tk[i]; b[1]=0; GUI_SetColor(fg); text(b,tx-4,8,tx+4,15,2); }
    int t20=bx+dbm_x(-73,bw), t40=bx+dbm_x(-53,bw)-1;
    fill(fg,t20,by1+1,t20,by1+1); fill(fg,t40,by1+1,t40,by1+1);
    GUI_SetColor(fg); text("+20",t20-11,8,t20+11,15,2); text("+40",t40-22,8,t40+1,15,1);
    sname_t(d<=-199?-2000:mt,b); GUI_SetColor(fg); text(b,w-38,0,w-1,10,1);
    if (S->rx){ fill(C_RX,w-24,8,w-2,15); GUI_SetColor(0xFFFFFFFFu);
      b[0]='R'; b[1]='X'; b[2]=vl; b[3]=0; text(b,w-24,8,w-2,15,2); }
    vfo_card(bg);
  }
}

/* bars from row y0 to y1, labels on row ly..ly+8 (D009: also used at the top of the waterfall) */
#define w 160
__attribute__((minsize)) static void draw_scope(int y0,int y1,int ly){
  int h=npts(), n=2*h+1;
  int bw = w/n; if (bw<2) bw=2;
  int tot=bw*n, x0=(w-tot)/2;
  int H=y1-y0+1, hgt=ly+9;
  fill(TBG(C_BG),0,y0,w-1,ly+8);
  s32 fl=CFG.floor_dbm, tp=CFG.top_dbm; if (tp<=fl) tp=fl+1;
  for (int i=0;i<n;i++){
    s32 d=S->dbm[i];
    int bh = d<=-199 ? 0 : (int)((d-fl)*H/(tp-fl));
    if (d>-199 && bh<1) bh=1;
    if (bh>H) bh=H;
    int bx=x0+i*bw, bx1=bx+bw-2; if (bw<3) bx1=bx;
    fill(C_EMPTY,bx,y0,bx1,y1-bh);
    if (bh) fill(i==h?C_CBAR:C_BAR,bx,y1-bh+1,bx1,y1);
  }
  {
    char b[16],*p; u32 sp=(u32)h*step_hz()/100;  /* in 0.1 kHz */
    GUI_SetFont(FONT8); GUI_SetTextMode(2); GUI_SetColor(C_FG);
    b[0]='-'; p=utoa_(sp/10,b+1); if (sp%10){*p++='.';*p++='0'+sp%10;} *p++='k'; *p=0;
    text(b,0,hgt-9,50,hgt-1,0); b[0]='+'; text(b,w-51,hgt-9,w-1,hgt-1,1);
    u32 f=S->scope_center;
    if (f){ p=utoa_(f/1000000,b); *p++='.'; u32 k=(f/1000)%1000; *p++='0'+k/100; *p++='0'+(k/10)%10; *p++='0'+k%10; *p=0;
      text(b,40,hgt-9,w-41,hgt-1,2); }
  }
}
#undef w

/* D009 waterfall page over the panels (dialog y16..111): frequency bar, live bars, 55 history rows
   (newest on top), span labels.  Equal neighbouring cells are drawn as one rectangle. */
static const u32 WF_PAL[3][8]={{0xFF000028u,0xFF001E8Cu,0xFF005ADCu,0xFF00BEE6u,0xFF78E678u,0xFFFAE600u,0xFFFF8C00u,0xFFFF1E00u},
  {0xFF000000u,0xFF000E3Cu,0xFF00286Eu,0xFF005F78u,0xFF37783Cu,0xFF8C7D00u,0xFF965000u,0xFF961400u},   /* D020 Dark */
  {0xFF080804u,0xFF1C220Eu,0xFF2E4616u,0xFF506E1Eu,0xFF829628u,0xFFBEAA32u,0xFFDC9628u,0xFFEBD78Cu}};  /* D020 Tactical: olive to amber */
__attribute__((minsize)) static void draw_wf(void){
  char b[12],*p; int h=npts(), n=2*h+1, bw=160/n, x0=(160-bw*n)/2;
  if (S->mk>=n) S->mk=(u8)h;
  u32 f=S->scope_center? S->scope_center+(u32)(((s32)S->mk-h)*(s32)step_hz()) : 0;   /* D010: marker frequency */
  fill(TBG(0xFF0000FFu),0,0,159,15);      /* stock selected-panel blue (D020: themed as a background) */
  if (f){ p=utoa_(f/1000000,b); *p++='.'; u32 k=f%1000000/10; for (u32 i=10000;i;i/=10) *p++=(char)('0'+k/i%10); *p=0;
    GUI_SetFont((const void*)0x6b010); GUI_SetTextMode(2); GUI_SetColor(0xFFFFFFFFu); text(b,0,0,159,15,2); }
  draw_scope(16,31,87);
  for (int t=0;t<3;t++){ int mx=x0+S->mk*bw+1; fill(0xFFE00000u,mx-2+t,16+t,mx+2-t,16+t); }   /* D010: red marker triangle */
  fill(TBG(C_BG),0,32,x0-1,86); fill(TBG(C_BG),x0+bw*n,32,159,86);
  for (int r=0;r<WF_ROWS;r++){
    const u8 *row=WF+((S->wfhead+WF_ROWS-r)%WF_ROWS)*NMAX;
    for (int i=0,j;i<n;i=j){ for (j=i+1;j<n && row[j]==row[i];j++);
      fill(TRAW(WF_PAL[S->theme<3? S->theme : 0][row[i]&7]),x0+i*bw,32+r,x0+j*bw-1,32+r); }
  }
}

typedef struct { s32 MsgId; u32 hWin; u32 hSrc; void *p; } wmmsg_t;

__attribute__((minsize)) static void cb_win(wmmsg_t *m){
  if (m->MsgId==0x0f){            /* WM_PAINT */
    if (m->hWin==S->hw_meter) draw_meter(160);
    if (m->hWin==S->hw_wf) draw_wf();
    if (m->hWin==S->hw_scope){
      if (!S->scope_off){ int hg=S->layout>=2?27:30; draw_scope(0,hg-10,hg-9); }
      else if (S->layout>=2) fill(TBG(C_BG),0,0,159,26);   /* D008: hide the stock Menu/Exit bar under it */
    }
    return;
  }
  if (m->MsgId==0x0b){            /* WM_DELETE */
    if (m->hWin==S->hw_meter){ S->hw_meter=0; S->hdlg=0; }
    if (m->hWin==S->hw_scope) S->hw_scope=0;
    if (m->hWin==S->hw_wf) S->hw_wf=0;
  }
  WM_DefaultProc(m);
}

static void wf_show(void);
/* replaces the main-screen dialog callback pointer */
void dlg_hook(wmmsg_t *m){
  DLG_MainCb(m);
  if (m->MsgId!=0x1d || !CFG.enable) return;     /* WM_INIT_DIALOG */
  st_init(); scope_load(); th_install();
  u8 lay=MAINDLG[0];
  u32 ctx=*(volatile u32*)(MAINDLG+8);
  if (ctx){ u8 *radio=*(u8**)(ctx+4); if (radio && (radio[0xa]&0x40)) return; }
  S->layout=lay; S->hw_meter=0; S->hw_scope=0; S->hw_wf=0; S->hdlg=m->hWin; S->rxslot=0xff;
  if (lay==1){
    S->hw_meter=WM_CreateChild(0,0,160,16,m->hWin,3,(void*)cb_win,0);  /* SHOW|HASTRANS */
    S->hw_scope=WM_CreateChild(0,82,160,30,m->hWin,3,(void*)cb_win,0);
  } else if (lay==3 || (lay==2 && CFG.watch_view)){
    /* 2- and 3-VFO views: full meter on top (y0, same place as the single-VFO screen), panels re-laid out
       to y16..84 (2 VFOs: build_scope.py, 34/35 px; 3 VFOs: build_vfo3.py, 23 px each), labelled scope y85 */
    S->hw_meter=WM_CreateChild(0,0,160,16,m->hWin,2,(void*)cb_win,0);   /* D007: meter on top, like single VFO */
    if (!S->scope_off)                       /* D008/D011: scope off: cards fill the area, no scope window */
      S->hw_scope=WM_CreateChild(0,85,160,27,m->hWin,3,(void*)cb_win,0);
  }
  if (S->hw_meter) wf_show();                  /* D009: waterfall page if it was on */
  S->dirty=1;
}

/* the stock "receiving" info card (Name/Freq/RSSI) from the standby module:
   skipped while the S-meter strip is on screen, the strip shows RX instead */
void popup_hook(u32 a0,u32 a1,u32 a2,u32 a3,u32 a4){
  st_init();
  if (CFG.enable && (S->hw_meter || S->hw_scope)){ S->dirty=1; return; }
  RxPopup(a0,a1,a2,a3,a4);
}


/* D009: waterfall window over the panels of the main screen (opaque, so the stock widgets under it are
   not drawn); deleted again when the waterfall is turned off.  Keys stay with the stock main screen, so
   Up/Down/knob tune as usual and the waterfall follows (recentre). */
#define WM_DeleteWin FN(0x4a14c,void(*)(u32))     /* deferred delete, as GUI_EndDialog uses it */
__attribute__((minsize)) static void wf_show(void){
  if (S->hw_wf){ WM_DeleteWin(S->hw_wf); S->hw_wf=0; }
  if (S->wf && !S->scope_off && S->hdlg && S->hw_meter){ S->hw_wf=WM_CreateChild(0,16,160,96,S->hdlg,2,(void*)cb_win,0); S->wfnew=1; }
}
static void scope_set_off(u8 off);
/* D010: standby-screen keys (0x14fe2 calls this instead of the stock handler 0x14bec).  While the
   waterfall is shown: Up/Down move the marker (held ~5 s), Menu = Go: in frequency mode the VFO is stepped
   with the stock Up/Down handling until it is within half a step of the marker frequency. */
#define STBY_KEY FN(0x14bec,u32(*)(u32))
#define CUR_VFO  FN(0x3525a,u8*(*)(u8*,u32))
__attribute__((minsize)) u32 wf_key(u32 ctx){
  st_init();
  volatile u16 *k=(volatile u16*)(ctx+0xc); u32 c=*k&0xff, ev=*k>>8;
  if (!S->hw_wf || (c!=4 && c!=7 && c!=8 && c!=9)) return STBY_KEY(ctx);
  /* D016: if a keypad frequency entry is in progress (stock input sub-handler active,
     byte 0x1fff9855 nonzero), let Menu fall through to stock so it confirms/tunes the
     typed frequency instead of jumping to the waterfall marker. */
  if (c==4 && *(volatile u8*)0x1fff9855u) return STBY_KEY(ctx);
  int h=npts();
  if (c==9){                           /* D016/D017: top knob moves the marker in frequency mode */
    u8 *rp=radio_ptr(); if (!rp) return STBY_KEY(ctx);
    u8 v=CUR_VFO(rp,0xff)[2];
    if (rp[v*6+0xb4]!=2) return STBY_KEY(ctx);     /* channel mode: knob changes channels as usual */
    /* D017: match stock's own knob decode at 0x14b96 - event 5 = up (+1), any other event = down (-1).
       D016 wrongly required event 4 for down, so down was swallowed (only up worked) and the first
       turns felt dead until an event 5 happened to arrive. */
    int m=S->mk+(ev==5? 1 : -1); if (m>=0 && m<=2*h) S->mk=(u8)m;
    S->mkhold=75; S->wfnew=1; return 0;            /* hold ~5 s so Menu can tune; edge-stop, no retune */
  }
  if (ev!=3) return 0;
  if (c!=4){ int m=S->mk+(c==7? 1 : -1); if (m>=0 && m<=2*h) S->mk=(u8)m; S->mkhold=75; S->wfnew=1; return 0; }
  u8 *rp=radio_ptr(); if (!rp || !S->scope_center) return 0;
  u8 v=CUR_VFO(rp,0xff)[2];
  if (rp[v*6+0xb4]!=2) return 0;                    /* channel mode: no retune */
  u32 tgt=S->scope_center+(u32)(((s32)S->mk-h)*(s32)step_hz()), st=0; u16 sv=*k;
  for (int i=0;i<100;i++){
    u32 f=rd32(rp+v*40+0xd5); s32 d=(s32)(tgt-f); u32 ad=(u32)(d<0? -d : d);
    if (!d || (st && ad*2<=st)) break;
    *k=(u16)(0x300|(d>0? 7 : 8)); STBY_KEY(ctx);
    u32 g=rd32(rp+v*40+0xd5); if (g==f) break;
    st= g>f? g-f : f-g;
  }
  *k=sv; S->mkhold=0;
  return 0;
}
/* long press 0 / Band Scope side key: Bars -> Waterfall -> Off -> Bars */
__attribute__((minsize)) static void scope_cycle(void){
  scope_load();
  if (S->scope_off){ scope_set_off(0); return; }
  if (!S->wf){ S->wf=1; wf_show(); return; }
  scope_set_off(1);
}
static void scope_set_off(u8 off){
  if (off && S->wf){ S->wf=0; wf_show(); }
  if (S->scope_off==off) return;
  S->scope_off=off;
  if (S->layout>=2 && S->hdlg) S->rebuild=1;   /* D008/D011: 2/3-VFO cards change size with the scope */
  if (off) scope_reset();
  scope_save();
  if (S->hw_scope) WM_Invalidate(S->hw_scope);
}

/* ---------------- receiving panel turns green (2- and 3-VFO views) -------------------------------- */
#define WIN_SetBkColor   FN(0x44efe,void(*)(u32,u32))
#define TEXT_SetColor    FN(0x48746,void(*)(u32,u32))
#define PANEL_IDS ((const u32*)0x5a24c)       /* 13 widget groups x 3 panel slots (stock fill's id table) */
#define C_PSEL  0xFF0000FFu                   /* stock: selected panel blue, white text; others white, black text */
#define C_TXP   0xFFC80000u                   /* D003: transmitting panel red, white text */
static void panel_paint(u8 slot,int kind){   /* kind 0 stock colours, 1 green (RX), 2 red (TX) */
  if (!S->hdlg || slot>2) return;
  int sel = (slot==SELSLOT);
  u32 bg = kind==2? C_TXP : kind? C_RX : sel? C_PSEL : 0xFFFFFFFFu;
  u32 fg = (kind||sel)? 0xFFFFFFFFu : 0xFF000000u;
  u32 h=WM_GetDlgItem(S->hdlg,0x85b+slot); if (h) WIN_SetBkColor(h,bg);
  for (int g=0;g<13;g++){ u32 t=WM_GetDlgItem(S->hdlg,(int)PANEL_IDS[g*3+slot]); if (t) TEXT_SetColor(t,fg); }
}
__attribute__((minsize)) static u8 rx_slot(u8 *col){
  *col=1;
  if (S->layout<2) return 0xff;
  if (S->txon){                          /* D003: the transmitting VFO's panel turns red, selected or not */
    u8 n=VFOLIST[0]; if (n>3) n=3;
    if (!S->txset && SELSLOT<n){ S->txvfo=VFOLIST[3+SELSLOT]&3; S->txset=1; }   /* TX not from a PTT key (VOX...) */
    *col=2;
    for (u8 i=0;i<n;i++) if ((VFOLIST[3+i]&3)==S->txvfo) return i;
    return 0xff;
  }
  if (!S->rx) return 0xff;
  char l=home_letter(); if (!l) return 0xff;
  u8 n=VFOLIST[0]; if (n>3) n=3;
  for (u8 i=0;i<n;i++) if ((VFOLIST[3+i]&3)==(u8)(l-'A')) return i;
  return 0xff;
}
__attribute__((minsize)) static void rx_panels(int force){
  u8 col; u8 want=rx_slot(&col);
  if (want==0xff) col=0;
  if (!force && want==S->rxslot && col==S->hlcol) return;
  if (S->rxslot!=0xff && S->rxslot!=want) panel_paint(S->rxslot,0);
  if (want!=0xff) panel_paint(want,col);
  S->rxslot=want; S->hlcol=col;
}
/* wrappers for the stock panel fill (0x19148) and background (0x1925c) calls: they repaint the panels
   in stock colours, so the receiving panel is made green again right after */
#define PANEL_FILL FN(0x19148,void(*)(u32,u32,u32,u32,u32))
#define PANEL_BG   FN(0x1925c,void(*)(u32,u32,u32))
void fill_hook(u32 a,u32 b,u32 c,u32 d,u32 e){ PANEL_FILL(a,b,c,d,e); st_init(); if (S->rxslot!=0xff) panel_paint(S->rxslot,S->hlcol? S->hlcol : 1); }
void bg_hook(u32 a,u32 b,u32 c){ PANEL_BG(a,b,c); st_init(); if (S->rxslot!=0xff) panel_paint(S->rxslot,S->hlcol? S->hlcol : 1); }

/* ---------------- D008: 3-VFO cards 32 px with the CH-n row while the scope is off -------------------
   The main screen for 3 VFOs is created at 0x1b572 from template 0x5a9a0 (44 entries, 23-px cards set
   by build_vfo3.py).  With the scope off, tpl3_create() builds it from a RAM copy re-laid out to three
   32-px cards (y16/48/80) and moves the stock soft keys off screen.  Toggling the scope while the 3-VFO
   screen is up closes it (stock close message 0x400) and re-opens the standby screen on the next tick. */
#define T3RAM ((u8*)0x2001BB00)               /* 44 x 28 bytes -> 0x2001BFD0 */
/* big-card rects (x, dy from the card top, w, h) in template order; cards A/B/C are entries 2-14 / 15-27 /
   28-40 with the same widget order: card, CH-n, frequency, zone, channel, name, 4 icons, power, W/N, 0x83f */
static const u8 T3BIG[13][4]={{0,0,160,32},{2,22,60,10},{94,14,54,10},{2,1,40,10},{26,1,40,10},{2,9,90,16},
  {66,1,30,10},{78,1,30,10},{94,1,30,10},{118,1,30,10},{148,1,10,10},{148,14,10,10},{128,14,16,10}};
/* D011 2-VFO big cards: (dy, h) per widget, same order: card, CH, freq, zone, channel, name, 4 icons, power, W/N, 0x83f */
static const u8 T2BIG[13][2]={{0,39},{28,10},{28,10},{1,10},{1,10},{10,18},{1,10},{1,10},{1,10},{1,10},{1,10},{28,10},{28,10}};
#define GUI_CreateDialogBox3 FN(0x40c70,u32(*)(const void*,int,void*,u32,int,int))
__attribute__((minsize)) u32 tpl3_create(const u8 *tpl,int n,void *cb,u32 parent,int x0,int y0){
  st_init(); scope_load();
  /* D014: 3-VFO (n==44) + scope off: the three cards grow to 26 px each and fill the area evenly
     (A y16..42, B y42..68, C y68..94), stopping above the stock Menu/Exit soft-key row (y94), which
     stays visible.  Each card's whole block is shifted down by DY so its text keeps its place in the
     card (text layout unchanged); only the card panel height grows to 26.  The D008 32-px cards reached
     y112 and hid that row, so they stay reverted.  With the scope on, the flash template's compact 23-px
     cards are used as-is.  CH labels stay parked off-screen (no stray "CH 49"). */
  (void)T3BIG;
  if (S->scope_off && n==44){
    static const u8 DY[3]={0,3,6};
    for (int i=0;i<44*28;i++) T3RAM[i]=tpl[i];
    for (int e=2;e<41;e++){                        /* cards A/B/C = entries 2-14 / 15-27 / 28-40; soft keys 41-43 left alone */
      s16 *r=(s16*)(T3RAM+e*28+10);                /* x, y, w, h */
      r[1]=(s16)(r[1]+DY[(e-2)/13]);
      if ((e-2)%13==0) r[3]=26;                    /* the card panel fills its 26-px slot */
    }
    tpl=T3RAM;
  } else if (S->scope_off && n==31 && CFG.watch_view){   /* D011: 2 VFOs + scope off: 39-px cards y16..94, stock Menu/Exit row below */
    for (int i=0;i<31*28;i++) T3RAM[i]=tpl[i];
    for (int e=2;e<28;e++){
      s16 *r=(s16*)(T3RAM+e*28+10);
      const u8 *t=T2BIG[(e-2)%13];
      r[1]=(s16)(16+39*((e-2)/13)+t[0]); r[3]=t[1];
    }
    tpl=T3RAM;
  }
  return GUI_CreateDialogBox3(tpl,n,cb,parent,x0,y0);
}
#define WM_GetClient0 FN(0x4938e,u32(*)(u32))
#define WM_SendMsg0   FN(0x49c3a,void(*)(u32,u32))
#define GO_HOME0      FN(0x14fd8,u32(*)(u32,u32,u32,u32))
__attribute__((minsize)) static void main_rebuild(void){
  u32 h=*(volatile u32*)(MAINDLG+4), ctx=*(volatile u32*)(MAINDLG+8);
  if (!h || !ctx || MAINDLG[0]<2 || !S->hdlg) return;
  WM_SendMsg0(WM_GetClient0(h),0x400);     /* stock close of the main screen (0x14820) */
  GO_HOME0(ctx,0,3,0);                       /* standby re-open: new main screen with the new layout */
}

/* ---------------- Radio Setting -> 15 "Band Scope" (one list, stock Battery Display page style) ----- */
#define GUI_CreateDialogBox FN(0x40c70,u32(*)(const void*,int,void*,u32,int,int))
#define WM_GetDesktop    FN(0x493a4,u32(*)(void))
#define WM_GetClient     FN(0x4938e,u32(*)(u32))   /* WM_GetClientWindow(hWin): sends WM_GET_CLIENT_WINDOW (0x17) */
#define WM_SendMsg       FN(0x49c3a,void(*)(u32,u32))
#define GUI_EndDialog    FN(0x419f0,void(*)(u32,int))
#define HDR_SetTextColor FN(0x45100,void(*)(u32,u32))
#define HDR_SetFont      FN(0x44f48,void(*)(u32,const void*))
#define HDR_AddItem      FN(0x44ac0,void(*)(u32,int,const char*,int))
#define LB_SetSpacing    FN(0x4790a,void(*)(u32,int))
#define LB_SetFont       FN(0x478d4,void(*)(u32,const void*))
#define LB_Insert        FN(0x47938,void(*)(u32,const char*,int))
#define LB_SetSel        FN(0x479e8,void(*)(u32,int))
#define GO_HOME          FN(0x14fd8,u32(*)(u32,u32,u32,u32))
#define TPL_LIST ((const void*)0x5cee0)       /* stock Battery Display template: window, header, listbox, soft keys */
#define FONT16  ((const void*)0x6b010)
#define FONT10  ((const void*)0x6a570)       /* 10 px font of the 2-VFO panels */
#define FONT_SK ((const void*)0x69548)
#define BS_N 6
#define BS_TPL 0x2001BA00u   /* RAM copy of the dialog template (4 x 28 bytes) */
static const char *const BS_TXT[BS_N]={"Off","+/- 90 kHz","+/- 112.5 kHz","+/- 180 kHz","+/- 225 kHz","+/- 450 kHz"};
static const char *const BS_STEP[BS_N]={"","5 kHz","6.25 kHz","10 kHz","12.5 kHz","25 kHz"};
static const u8 BS_CODE[BS_N]={0,1,0,2,3,4};   /* list row -> span code (row 0 = scope off) */
static u8 bs_current(void){
  if (S->scope_off) return 0;
  for (u8 i=1;i<BS_N;i++) if (BS_CODE[i]==S->span) return i;
  return 2;
}
static const char *const PP_TXT[2]={"Off","On"};
static const char *const TH_TXT[3]={"Stock","Dark","Tactical"};   /* D020 */
static u8 pg_n(void){ return S->pg_which==2? 3 : S->pg_which? 2 : BS_N; }
static const char *pg_txt(int i){ return S->pg_which==2? TH_TXT[i] : S->pg_which? PP_TXT[i] : BS_TXT[i]; }
/* D020: theme code in EEPROM 0xFC bits 5-6 (0 Stock, 1 Dark, 2 Tactical; blank 3 = Stock) */
__attribute__((minsize)) static void th_apply(u8 row){
  if (row>2) return;
  u8 b=0; EE_READ(EE_SPAN,&b,1); b=(u8)((b&~0x60)|(row<<5));
  EE_WRITE(EE_SPAN,1,&b,1); S->theme=row; th_install();
}
__attribute__((minsize)) static void ptt_apply(u8 on){
  u8 b=0; EE_READ(EE_SPAN,&b,1); b=(u8)((b&~0x18)|(on? 0x08:0));
  EE_WRITE(EE_SPAN,1,&b,1); S->ptt_on=on; S->ptt_key=0; S->ptt_mine=0;
}
__attribute__((minsize)) static void bs_apply(u8 row){
  if (S->pg_which==2){ th_apply(row); return; }
  if (S->pg_which){ ptt_apply(row==1); return; }
  if (row>=BS_N) return;
  if (row==0){ scope_set_off(1); return; }
  u8 c=BS_CODE[row];
  if (c!=S->span){ S->span=c; u8 b=0; EE_READ(EE_SPAN,&b,1); b=(u8)((b&~7)|c); EE_WRITE(EE_SPAN,1,&b,1); scope_reset(); if (S->hw_scope) WM_Invalidate(S->hw_scope); }
  scope_set_off(0);
}
/* D007: the Band Scope list is drawn by a transparent child of the listbox (the listbox only draws the
   blue cursor bar): tick on the saved span, span label, step size right-aligned in grey.  Row pitch 14 px,
   10-px font 2 px down.  A small window above the list shows the column header "Span ... Step". */
#define C_DIM 0xFF6E6E78u
static const u8 TICK[6]={0x40,0x60,0x31,0x1b,0x0e,0x04};   /* 7x6 tick, bit0 = left column */
/* D012: the list is now drawn entirely by this opaque overlay over the whole listbox, for both the Band
   Scope and Side Key PTT pages.  It paints its own background and selection bar, so the stock listbox's
   blue bar (black text was invisible on it) and its dashed focus rectangle around the group are both
   hidden underneath.  Repainted whenever the selection moves (bs_cb invalidates S->pg_ov). */
__attribute__((minsize)) static void bs_list_cb(wmmsg_t *m){
  if (m->MsgId!=0x0f){ WM_DefaultProc(m); return; }
  u8 n=pg_n(), saved=S->pg_which==2? S->theme : S->pg_which? 0xff : bs_current();
  fill(TBG(C_BG),0,0,139,93);
  GUI_SetFont(FONT10); GUI_SetTextMode(2);
  for (int i=0;i<n;i++){
    int y=i*14, cur=(i==S->pg_val);
    if (cur) fill(TBG(C_BAR),0,y,139,y+13);                 /* selection bar, drawn by us (white text on top) */
    if (i==saved) for (int r=0;r<6;r++) for (int c=0;c<7;c++) if (TICK[r]>>c&1) fill(cur? 0xFFFFFFFFu : 0xFF009600u,3+c,y+4+r,3+c,y+4+r);
    GUI_SetColor(cur? 0xFFFFFFFFu : C_FG); text(pg_txt(i),13,y+2,136,y+12,0);
    if (!S->pg_which){ GUI_SetColor(cur? 0xFFFFFFFFu : C_DIM); text(BS_STEP[i],13,y+2,136,y+12,1); }
  }
}
__attribute__((minsize)) static void bs_hdr_cb(wmmsg_t *m){
  if (m->MsgId!=0x0f){ WM_DefaultProc(m); return; }
  GUI_SetFont(FONT8); GUI_SetTextMode(2); GUI_SetColor(C_DIM);
  text("Span",23,0,146,7,0); text("Step",23,0,146,7,1);
}
__attribute__((minsize)) static void bs_cb(wmmsg_t *m){
  u32 id=(u32)m->MsgId;
  if (id==0x1d){
    u32 h=WM_GetDlgItem(m->hWin,0x85a);
    HDR_SetTextColor(h,0xFFFFFFFFu); HDR_SetFont(h,FONT16); HDR_AddItem(h,0xa0,S->pg_which==2? "Theme" : S->pg_which? "Side Key PTT" : "Band Scope",0xe);
    h=WM_GetDlgItem(m->hWin,0x80a);
    LB_SetSpacing(h,14); LB_SetFont(h,FONT10);   /* row pitch 14 px: all 6 rows fit above the soft keys (stock 0x16 showed 3) */
    for (int i=0;i<pg_n();i++) LB_Insert(h,S->pg_which? pg_txt(i) : "",i);
    LB_SetSel(h,S->pg_val);
    S->pg_ov=WM_CreateChild(0,0,140,94,h,2,(void*)bs_list_cb,0);   /* D012: opaque overlay over the whole listbox (both pages) */
    if (!S->pg_which) WM_CreateChild(0,18,160,8,m->hWin,3,(void*)bs_hdr_cb,0);  /* D017: 2 px gap below the blue title bar (was y16, abutting it) */
    h=WM_GetDlgItem(m->hWin,0x85e);
    WIN_SetBkColor(h,0xFF00B2EDu); HDR_SetTextColor(h,0xFF000000u); HDR_SetFont(h,FONT_SK);
    HDR_AddItem(h,0x50,"Select",0xe); HDR_AddItem(h,0x50,"Exit",0xe);
    return;
  }
  if (id==0x401){ GUI_EndDialog(m->hWin,0); S->pg_hwin=0; return; }
  if (id==0x0b) S->pg_hwin=0;                       /* D005: page closed by anything else (WM_DELETE) */
  if (id==0x402 || id==0x403){
    S->pg_changed=1;
    if (id==0x402){ if (S->pg_val==0) S->pg_val=pg_n(); S->pg_val--; }
    else { if (++S->pg_val>=pg_n()) S->pg_val=0; }
    LB_SetSel(WM_GetDlgItem(m->hWin,0x80a),S->pg_val);
    if (S->pg_ov) WM_Invalidate(S->pg_ov);            /* D012: repaint our list so the new selected row shows */
    return;
  }
  WM_DefaultProc(m);
}
__attribute__((minsize)) static u32 bs_key(u32 ctx){
  u16 k=*(volatile u16*)(ctx+0xc); u32 code=k&0xff, ev=k>>8;
  if (!S->pg_hwin) return (u32)-1;
  typedef u32 (*mod_t)(u32,u32,u32,u32);
  switch (code){
  case 4: if (ev!=3) break;                         /* Menu: select + save */
    WM_SendMsg(WM_GetClient(S->pg_hwin),0x401);
    if (S->pg_changed) bs_apply(S->pg_val);
    if (S->pg_parent) ((mod_t)S->pg_parent)(ctx,0,3,0);
    return 1;
  case 5: if (ev!=3) break;                         /* Exit: back to Radio Setting, nothing saved */
    WM_SendMsg(WM_GetClient(S->pg_hwin),0x401);
    if (S->pg_parent) ((mod_t)S->pg_parent)(ctx,0,3,0);
    return 1;
  case 6: if (ev!=3) break;                         /* back to the main screen */
    WM_SendMsg(WM_GetClient(S->pg_hwin),0x401); GO_HOME(ctx,0,3,0); return 1;
  case 7: if (ev==3) WM_SendMsg(WM_GetClient(S->pg_hwin),0x402); break;   /* up */
  case 8: if (ev==3) WM_SendMsg(WM_GetClient(S->pg_hwin),0x403); break;   /* down */
  case 9: WM_SendMsg(WM_GetClient(S->pg_hwin), ev==5? 0x402 : 0x403); break; /* knob */
  }
  return (u32)-1;
}
/* module entry, called like the stock pages: ev 1 = open (r1 = parent module), 3 = re-open, else key */
__attribute__((minsize)) static u32 pg_module(u32 ctx,u32 parent,u32 ev,u32 which){
  st_init();
  if (ev==1 || ev==3){
    if (ev==1) S->pg_parent=parent;
    scope_load();
    S->pg_which=(u8)which;
    S->pg_ctx=ctx; S->pg_changed=0; S->pg_val= which==2? S->theme : which? (u8)S->ptt_on : bs_current();
    { const u8 *src=(const u8*)TPL_LIST; u8 *dst=(u8*)BS_TPL;   /* stock template, but its listbox has 3 rows */
      for (int i=0;i<4*28;i++) dst[i]=src[i];
      *(u32*)(dst+2*28+20) = (*(const u32*)(src+2*28+20) & ~0xffu) | pg_n(); }   /* Para low byte = row count */
    S->pg_hwin=GUI_CreateDialogBox((const void*)BS_TPL,4,(void*)bs_cb,WM_GetDesktop(),0,0);
    return 0;
  }
  return bs_key(ctx);
}
u32 bs_module(u32 ctx,u32 parent,u32 ev,u32 a3){ (void)a3; return pg_module(ctx,parent,ev,0); }
u32 pp_module(u32 ctx,u32 parent,u32 ev,u32 a3){ (void)a3; return pg_module(ctx,parent,ev,1); }
u32 th_module(u32 ctx,u32 parent,u32 ev,u32 a3){ (void)a3; return pg_module(ctx,parent,ev,2); }   /* D020 */

/* Radio Setting list: stock has 14 items in RAM (names 0x1fff96ac, 12-byte entries 0x1fff96e4).
   Copies with a 15th item live in free RAM above the stack; the list fill and key handler use them.
   D020: 16th item "Theme" (entries end exactly at 0x2001B900 = KF_NAMES). */
#define RS_NAMES ((u32*)0x2001B800)
#define RS_ENT   ((u32*)0x2001B840)
#define KF_NAMES ((u32*)0x2001B900)
#define KF_ENT   ((u32*)0x2001B940)
__attribute__((minsize)) void rs_tables(void){
  const u32 *n=(const u32*)0x1fff96ac, *e=(const u32*)0x1fff96e4;
  for (int i=0;i<14;i++){ RS_NAMES[i]=n[i]; RS_ENT[i*3]=e[i*3]; RS_ENT[i*3+1]=e[i*3+1]; RS_ENT[i*3+2]=e[i*3+2]; }
  RS_NAMES[14]=(u32)"Band Scope"; RS_ENT[42]=0; RS_ENT[43]=0; RS_ENT[44]=(u32)bs_module;
  RS_NAMES[15]=(u32)"Theme"; RS_ENT[45]=0; RS_ENT[46]=0; RS_ENT[47]=(u32)th_module;
}
/* D003: Radio Setting -> 5 Key Function: stock 3 items (state 0x1fff9c60: +0xc names, +0x18 12-byte
   entries, handler at +8), copies with a 4th item "Side Key PTT" */
#define KFM_NAMES ((u32*)0x2001BA80)
#define KFM_ENT   ((u32*)0x2001BA90)
__attribute__((minsize)) void kfm_tables(void){
  const u32 *n=(const u32*)0x1fff9c6c, *e=(const u32*)0x1fff9c78;
  for (int i=0;i<3;i++){ KFM_NAMES[i]=n[i]; KFM_ENT[i*3]=e[i*3]; KFM_ENT[i*3+1]=e[i*3+1]; KFM_ENT[i*3+2]=e[i*3+2]; }
  KFM_NAMES[3]=(u32)"Side Key PTT"; KFM_ENT[9]=0; KFM_ENT[10]=0; KFM_ENT[11]=(u32)pp_module;
}

/* Key Function Select (state 0x1fff9d28: [0] rows, [1] function id, [2] key 0..5, [4] u16 row):
   stock rows 0..11 + Prog PTT (long-press keys only).  Band Scope (id 40) goes in as row 12 for every
   key; Prog PTT moves to row 13. */
#define FN_SCOPE 40
static const u8 KF_IDS[14]={0,1,0x1c,0xf,2,0x14,0x15,3,5,0x1d,0x1e,0x20,FN_SCOPE,0x1f};
static int kf_long(u8 key){ return !(key==0 || key==1 || key==2 || key==4); }
__attribute__((minsize)) void kf_tables(void){
  const u32 *n=(const u32*)(0x1fff9d28+0x18), *e=(const u32*)(0x1fff9d28+0x4c);
  for (int i=0;i<14;i++){
    int j = i<12? i : i==12? 0 : 12;
    KF_NAMES[i]= i==12? (u32)"Band Scope" : n[j];
    KF_ENT[i*3]=e[j*3]; KF_ENT[i*3+1]=e[j*3+1]; KF_ENT[i*3+2]=e[j*3+2];
  }
}
__attribute__((minsize)) void kf_open(u8 *st){
  u8 id=st[1]; int lg=kf_long(st[2]); u16 row=0;
  for (u16 i=0;i<14;i++) if (KF_IDS[i]==id){ row=i; break; }
  if (id==0x1f && !lg) row=0;
  *(u16*)(st+4)=row; st[0]= lg? 14 : 13;
}
__attribute__((minsize)) void kf_sel(u8 *st){
  u16 row=*(u16*)(st+4); if (row>=14) return;
  u8 id=KF_IDS[row]; if (id==0x1f && !kf_long(st[2])) id=0;
  st[1]=id;
}
/* side/top key function -> key code (stock 0x36670); Band Scope toggles the scope on press */
#define SK_MAP FN(0x36670,void(*)(u32,u8*))
void sk_map(u32 id,u8 *msg){
  if (id==FN_SCOPE){
    u8 ev=msg[0xd];
    if (ev==2 || ev==3){ st_init(); scope_cycle(); }
    return;
  }
  SK_MAP(id,msg);
}

/* standby-screen key events (stock hidden-code handler 0x3b852): ev 1 = down, 2 = long press,
   3 = short release, 4 = release after long press.  Long press of the toggle key shows/hides the scope
   (and stops/starts the sweep); the key's own stock function is left alone. */
void key_hook(u32 key, u32 ev){
  st_init();
  if (!CFG.toggle_key || key!=CFG.toggle_key || ev!=2) return;
  scope_cycle();
}

/* ---------------- D003: side keys as PTT, by VFO view ---------------------------------------------
   Radio Setting -> 5 Key Function -> 4 "Side Key PTT" On: in the 2-VFO view SK1 transmits on the second panel's VFO, in
   the 3-VFO view SK1 on the second and SK2 on the third; the main PTT always transmits on the first
   (top) panel's VFO.  Single-VFO view: side keys and PTT are stock.  Every side key that went
   down as PTT also sends its release as a PTT release (releasing either key ends TX), so changing the
   view while holding a key cannot leave the radio in TX.  Not in Emergency / Weather Alert mode (stock rule).
   Side keys send the stock "Prog PTT" key code 0xd (same press/release events as stock Prog PTT); the
   PTT handler 0x38312 then asks ptt_target() which VFO to key. */
#define PTT_COUNT FN(0x3534a,u32(*)(void))   /* stock: number of VFOs shown */
/* 0x36796 in the side-key translator 0x36760 (raw = key event: [1] key 0x13 TK/0x14 SK1/0x15 SK2,
   [4] u32 event 1 down, 2 long press, 3 short release, 4 release after long; msg+0xc = code|event<<8).
   returns 0 = stock handling, 1 = swallow, 2 = msg filled */
static u8 side_slot(u8 key){ return key==0x14? 1 : key==0x15? 2 : 0; }   /* panel slot = latch bit */
/* would a side-key down start TX? (feature on, 2/3-VFO view, panel exists, not Emergency 4 / Weather Alert 8) */
__attribute__((minsize)) static int side_would(u8 slot,u8 *r){
  u8 n=VFOLIST[0]; if (n>3) n=3;
  u8 rs= r? r[0xc] : 0;
  return S->ptt_on && S->layout>=2 && slot<n && rs!=4 && rs!=8;
}
__attribute__((minsize)) u32 side_ptt(u8 *raw,u8 *msg){
  st_init(); span_load();
  u8 slot=side_slot(raw[1]); u32 ev=*(u32*)(raw+4);
  if (!slot) return 0;
  if (ev==1){
    if (!side_would(slot,*(u8**)(msg+4))){ S->ptt_key&=(u8)~slot; return 0; }
    S->ptt_key|=slot; S->ptt_vfo=VFOLIST[3+slot]&3; S->ptt_mine=1;
    *(volatile u16*)(msg+0xc)=0x100|0xd; return 2;
  }
  if (!(S->ptt_key&slot)) return 0;
  if (ev==2) return 1;                       /* held: stay in TX, no long-press function */
  S->ptt_key&=(u8)~slot; S->ptt_mine=0;      /* D005: each held key is latched, so no stock function on its release */
  *(volatile u16*)(msg+0xc)=(u16)((ev<<8)|0xd); return 2;
}
/* D006: key lock.  The lock check in the translator (0x36790, gate result 0 = locked) and the key
   dispatcher's skips (0x368f6: Key Lock Mode 2 or Weather Alert -> translator not called) would drop
   side-key events.  This says whether the event is side-key PTT anyway: a down that starts TX (side keys
   transmit while locked, like the main PTT) or any event of a key held as PTT, so its release always
   ends TX. */
__attribute__((minsize)) u32 side_pass(u8 *raw,u8 *r){
  st_init(); span_load();
  u8 slot=side_slot(raw[1]); if (!slot) return 0;
  return *(u32*)(raw+4)==1? side_would(slot,r) : (S->ptt_key&slot);
}
/* 0x383ce in the PTT handler: code 0xc main PTT / 0xd Prog PTT, cur = selected VFO id -> VFO to key */
__attribute__((minsize)) u32 ptt_target(u32 code,u32 cur){
  st_init();
  u32 v=cur;
  if (code==0xd){
    if (S->ptt_mine) v=S->ptt_vfo;
    else { u32 n=PTT_COUNT(); if (n>1){ v=cur+1; if (v>=n) v=0; } }   /* stock Prog PTT: next VFO */
  } else if (code==0xc && S->ptt_on && S->layout>=2 && VFOLIST[0]>=2) v=VFOLIST[3]&3;
  S->ptt_mine=0;
  if (code==0xc || code==0xd){ S->txvfo=(u8)v; S->txset=1; S->txidle=0; }
  return v;
}
