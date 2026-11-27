/* SPDX-License-Identifier: GPL-3.0-or-later
   Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root. */
MEMORY { CAVE (rx) : ORIGIN = 0x73350, LENGTH = 0x8000 }
SECTIONS {
  .text : { *(.text.start) *(.text*) *(.rodata*) } > CAVE
  .data : { *(.data*) *(.bss*) *(COMMON) } > CAVE
  /DISCARD/ : { *(.ARM.*) *(.comment) }
}
