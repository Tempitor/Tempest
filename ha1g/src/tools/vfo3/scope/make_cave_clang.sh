#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
# Compile scope.c + glue.S into scope_cave.bin (+ scope_cave.sym) with clang + ld.lld.
set -e
cd "$(dirname "$0")"
T=${TMPDIR:-/tmp}/vfo3cave; mkdir -p $T
F="--target=armv7em-none-eabi -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -Os -ffreestanding -fno-builtin -nostdlib -Wall -Wno-unused-function -fno-common -fno-jump-tables"
clang $F -c scope.c -o $T/scope.o
clang --target=armv7em-none-eabi -mcpu=cortex-m4 -mthumb -c glue.S -o $T/glue.o
ld.lld -T link.ld $T/glue.o $T/scope.o -o $T/scope_cave.elf
llvm-objcopy -O binary $T/scope_cave.elf scope_cave.bin
llvm-nm $T/scope_cave.elf | awk '$2=="T"||$2=="t"||$2=="R"||$2=="D"{print $3, $1}' | grep -v '^\$' > scope_cave.sym
grep -E '^(CFG|bg_hook|bs_module|fill_hook|kf_fill_glue|kf_open_glue|kf_sel_glue|rs_fill_glue|rs_key_glue|sk_map|dlg_hook|hf_hook|key_glue|key_hook|mon_dtmf_glue|mon_poll_glue|mon_tone_glue|popup_hook|scope_tick|scope_tick_even|tick_glue|side_glue|ptt_glue|side_ptt|ptt_target|pp_module|kfm_fill_glue|kfm_key_glue|lock_glue|kd_glue|side_pass|bs_list_cb|bs_hdr_cb|tpl3_create|wf_key|wf_push|th_pal|th_map|th_setcolor|th_setbk|TH_API|th_module) ' scope_cave.sym > s.tmp && mv s.tmp scope_cave.sym
cat scope_cave.sym; ls -l scope_cave.bin
