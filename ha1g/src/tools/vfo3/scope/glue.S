/* SPDX-License-Identifier: GPL-3.0-or-later
   Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root. */
  .syntax unified
  .thumb
  .section .text.start,"ax"
  .global CFG
  .align 2
CFG:
  .word 0x31504353    @ magic 'SCP1'
  .word 1             @ enable
  .word 6250          @ step_hz
  .word 18            @ half_points  (37 bars, +-112.5 kHz)
  .word 2500          @ dwell_us
  .word 1             @ hop_ticks
  .word 1             @ pts_per_hop
  .word 5             @ redraw_ticks
  .word 0             @ rssi_cal_db
  .word -130          @ floor_dbm
  .word -70           @ top_dbm
  .word 3             @ quiet_ticks
  .word 1             @ watch_view
  .word 25            @ recentre_ticks (~0.5 s)
  .word 3             @ dw_pts (points per hop with two VFOs watched)
  .word 1             @ dw_quiet
  .word 1             @ toggle_key (internal code: key 0 = 1)
  .word 1             @ scope_on at power-on
  .word 1             @ even_hops
  .word 2             @ meter_gap
  .word 2             @ meter_every
  .word 15            @ lock_margin (D015: dB a peak must stand above the sweep average to dwell)

@ entered from 0x101e6 (b.w) in the radio tick: r0 = tick counter, r4 = radio,
@ r5 = rx cfg, stack holds {r4,r5,r6,lr} of the stock function 0x101a2
  .global tick_glue
  .thumb_func
tick_glue:
  lsls r0, r0, #31
  bne 1f
  mov r1, r5            @ even tick: run the stock RX poll/update (was a tail call to 0xfd7e)
  mov r0, r4
  ldr r2, =0xfd7f
  blx r2
  mov r5, r0            @ keep its return value (r5 is restored by the pop below)
  mov r0, r4
  bl scope_tick_even
  mov r0, r5
  pop {r4, r5, r6, pc}
1:
  mov r0, r4
  bl scope_tick
  pop {r4, r5, r6, pc}
  .ltorg

@ entered from 0x3b852 (b.w): r0 = module ctx, r1 = key code, r2 = event
  .global key_glue
  .thumb_func
key_glue:
  push {r0, r1, r2, r3, ip, lr}
  mov r0, r1
  mov r1, r2
  bl key_hook
  pop {r0, r1, r2, r3, ip, lr}
  push {r2, r3, r4, r5, r6, lr}
  mov r6, r0
  ldr ip, =0x3b857
  bx ip
  .ltorg

@ ---- monitor: also bypass tone-mismatch mute and DTMF-decode (selective call) mute ----
@ entered from 0xfdb8 in the RX state update 0xfd7e, right after the RX poll returned (r0 = poll
@ result, r4 = radio).  [sp,#0x14] is the poll's "tone mismatch, keep audio muted" flag.
  .global mon_poll_glue
  .thumb_func
mon_poll_glue:
  mov r6, r0              @ poll result (stock: mov r6,r0)
  ldrb r1, [r4, #8]
  lsls r1, r1, #30        @ radio[8] bit1 = monitor on
  bpl 1f
  movs r1, #0
  strb r1, [sp, #0x14]    @ tone-mismatch mute flag
  movs r1, #1
  strb r1, [sp, #0x10]    @ REG_0C bit1 copy: with a tone set and this 0, 0xff48 closes the audio
  ldr r1, =0x1fff947c     @ RX state byte [2]: 2/6 = squelch open but waiting for the RX tone
  ldrb r2, [r1, #2]
  cmp r2, #2
  beq 3f
  cmp r2, #6
  bne 1f
3:
  adds r2, #1             @ -> 3/7 = open, audio allowed (stock then turns the speaker on)
  strb r2, [r1, #2]
1:
  mov r0, r4
  ldr ip, =0xfdbd
  bx ip

@ entered from 0x1001e: stock tests DTMF-decode enable (cfg[6] bit2) and, if set, keeps audio muted
@ until a DTMF code from the channel's list is received.  With monitor on, take the no-decode path.
  .global mon_dtmf_glue
  .thumb_func
mon_dtmf_glue:
  ldrb r0, [r4, #8]
  lsls r0, r0, #30
  bpl 2f
  ldr ip, =0x100d1        @ decode-off path: audio allowed
  bx ip
2:
  ldrb r0, [r5, #6]
  lsls r0, r0, #0x1d      @ flags for the stock bpl at 0x10022
  ldr ip, =0x10023
  bx ip
  .ltorg

@ entered from 0xfc88 in the RX state machine 0xfc5c (r5 = radio, r6 = rx cfg) when the squelch has
@ just opened: stock goes to "open, waiting for tone" (state 2/6, no audio) if cfg[4] (RX tone) is set.
@ With monitor on, take the no-tone path (state 3/7, audio).  On reverse the TX tone becomes the RX
@ tone and the stock monitor tone-off does not clear it.
  .global mon_tone_glue
  .thumb_func
mon_tone_glue:
  ldrb r0, [r5, #8]
  lsls r0, r0, #30
  bpl 1f
  ldr ip, =0xfcbd
  bx ip
1:
  ldrb r0, [r6, #4]
  cbz r0, 2f
  ldr ip, =0xfc8d
  bx ip
2:
  ldr ip, =0xfcbd
  bx ip
  .ltorg

@ ---- Radio Setting list with a 15th item (Band Scope) ----
@ 0x15920 (list fill loop set-up: ldr.w r8,=0x1fff96a0; add.w r8,#0xc; add.w sb,r8,#0x38)
  .global rs_fill_glue
  .thumb_func
rs_fill_glue:
  bl rs_tables
  ldr r8, =0x2001B800
  ldr sb, =0x2001B840
  ldr ip, =0x1592d
  bx ip
@ 0x159ea in the Radio Setting key handler (add.w r8,r5,#0x44 = entry table; then cmp r0,#0)
  .global rs_key_glue
  .thumb_func
rs_key_glue:
  ldr r8, =0x2001B840
  cmp r0, #0
  ldr ip, =0x159f1
  bx ip
  .ltorg

@ ---- Key Function Select with Band Scope ----
@ 0x1d31c (list fill set-up: ldr.w r8,=0x1fff9d28; add.w r8,#0x18; add.w sb,r8,#0x34)
  .global kf_fill_glue
  .thumb_func
kf_fill_glue:
  bl kf_tables
  ldr r8, =0x2001B900
  ldr sb, =0x2001B940
  ldr ip, =0x1d329
  bx ip
@ 0x1d3d0 (function id -> row + row count), r4 = state
  .global kf_open_glue
  .thumb_func
kf_open_glue:
  mov r0, r4
  bl kf_open
  ldr ip, =0x1d489
  bx ip
@ 0x1d55c (row -> function id on Select), r4 = state
  .global kf_sel_glue
  .thumb_func
kf_sel_glue:
  mov r0, r4
  bl kf_sel
  ldr ip, =0x1d619
  bx ip
  .ltorg

@ ---- D003: side keys as PTT by VFO view ----
@ 0x36796 in the side-key translator 0x36760 (stock: ldrb.w r0,[sb,#1]); sb = raw key event, r4 = msg
  .global side_glue
  .thumb_func
side_glue:
  mov r0, sb
  mov r1, r4
  bl side_ptt
  cbz r0, 1f
  subs r5, r0, #1         @ 1 -> swallowed (return 0), 2 -> msg filled (return 1)
  ldr ip, =0x368c5        @ mov r0,r5; return
  bx ip
1:
  ldrb.w r0, [sb, #1]
  ldr ip, =0x3679b
  bx ip
@ 0x383ce in the PTT handler 0x38312 (stock: cmp r5,#0xd; beq): r5 = key code, r6 = selected VFO id
  .global ptt_glue
  .thumb_func
ptt_glue:
  mov r0, r5
  mov r1, r6
  bl ptt_target
  mov r6, r0
  ldr ip, =0x383dd        @ TX on VFO r6 (skips the stock debug printf)
  bx ip
  .ltorg

@ ---- D003: Key Function menu (Radio Setting 5) with a 4th item, Side Key PTT ----
@ 0x1c518 (list fill set-up: ldr.w r8,=0x1fff9c60; add.w r8,#0xc; add.w sb,r8,#0xc)
  .global kfm_fill_glue
  .thumb_func
kfm_fill_glue:
  bl kfm_tables
  ldr r8, =0x2001BA80
  ldr sb, =0x2001BA90
  ldr ip, =0x1c525
  bx ip
@ 0x1c5e0 in the key handler (add.w r7,r4,#0x18 = entry table; then cmp r0,#0)
  .global kfm_key_glue
  .thumb_func
kfm_key_glue:
  ldr r7, =0x2001BA90
  cmp r0, #0
  ldr ip, =0x1c5e7
  bx ip
  .ltorg

@ ---- D006: side-key PTT not dropped by the key lock ----
@ 0x36794 in the translator (stock: cbz r0,0x367c8 = locked -> lock tip, no function); r0 = lock check
@ result, sb = raw key event, r4 = msg
  .global lock_glue
  .thumb_func
lock_glue:
  cbz r0, 1f
  b side_glue             @ not locked: as before
1:
  ldr r1, [r4, #4]        @ radio
  mov r0, sb
  bl side_pass
  cbz r0, 2f
  b side_glue             @ side-key PTT event: handled even while locked
2:
  ldr ip, =0x367c9        @ stock lock path
  bx ip
@ 0x368f6 in the key dispatcher (stock: cmp r0,#2; beq skip; ldrb r0,[r6,#0xc]; cmp r0,#8; beq skip),
@ r0 = Key Lock Mode (settings 0x22 & 3), r5 = raw key event, r6 = radio
  .global kd_glue
  .thumb_func
kd_glue:
  cmp r0, #2
  beq 1f
  ldrb r0, [r6, #0xc]
  cmp r0, #8
  beq 1f
3:
  ldr ip, =0x36901        @ call the translator
  bx ip
1:
  mov r0, r5
  mov r1, r6
  bl side_pass
  cmp r0, #0
  bne 3b
  ldr ip, =0x3690d        @ stock skip
  bx ip
  .ltorg
