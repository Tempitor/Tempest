# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""Fix the main-screen frequency/tone display for Talk Around (TA) and
Freq Reversal (FR) on an HA1G V1.01.14.002 image.

usage: build_tafr.py IN.bin OUT.bin
  IN may be the stock image or any earlier mod build in this folder
  (CTCSS, SCR, MON, CTCSS_MON, SCR_MON); the fix is stacked on top.

What stock actually does
------------------------
Channel record (0x25 bytes, current channel at radio+0x144):
  +0x10 RX freq   +0x14 TX freq   +0x18 RX tone   +0x1b TX tone
  +0x1e bit3 = FR (Freq Reversal)   bit4 = TA (Talk Around)
Menu "Talkaround & Reversal": "Talk Around" -> bit4, "Freq Reversal" -> bit3.
Status icon (0x18d3c): bit4 -> "TA", bit3 -> "FR".           (correct)

Radio side (all correct, matches the labels):
  RX setup 0x1062e / 0x10a96 / 0x10b06 / 0x38730:
       bit3 -> receive on +0x14 with tone +0x1b (reverse); bit4 -> unchanged
  TX setup 0x10792 / 0x10a1a, TX-permit check 0x38270:
       bit3 or bit4 -> transmit on +0x10 with tone +0x18
  => TA = talkaround (RX on output, TX on output)
     FR = reverse    (RX on input,  TX on output)

Display side (the bug, display copy of the record at disp+0xc5, flags at +0xe3):
  0x1884a  frequency-mode standby: shows the TX freq when bit4 (TA) is set
  0x18de0  tone-type indicator:   shows the TX tone when bit4 (TA) is set
  0x187da  name-mode frequency:   RX field in standby (ignores FR), TX field
           while transmitting (ignores TA/FR)
  0x18dd8  tone indicator while TX: always shows the TX tone
So with TA on, the screen shows the repeater INPUT although the radio is
still listening on the output; with FR on, the screen shows the output
although the radio is listening on the input. That makes TA look like
reverse and FR look like "nothing but TX on the output".

Fix (display only, RF code untouched):
  0x1884a  lsls r0,r0,#27 -> lsls r0,r0,#28   (standby freq follows FR)
  0x187da  cmp/beq -> b.w caveA  (name mode: RX view follows FR, TX view
                                  with TA/FR shows +0x10, the frequency
                                  actually transmitted on)
  0x18dd8  cmp/beq -> b.w caveB  (tone indicator: RX view follows FR, TX
                                  view with TA/FR shows the RX tone, which
                                  is the tone actually transmitted)
  version  Radio Information suffix gains 'R'
"""
import sys,hashlib,keystone

KNOWN={
 '267bee83b844d99f76a008ab2698a822c78fd8fecc27ab6cd79e4f869e8f2d77':'stock',
 '191a4c40dc10980b3b4686a4cb34c1e74ff91c032f2c654389677d240a0e2acc':'ctcss',
 '775aa384331babf7c973c9bf1af350b42deab9c458a9af10a99a775b401bba4a':'scr',
 'b7df4ee42928c20772b7390234d9ddea1ee862b32982d1c3dd7ea204f1e24167':'mon',
 '56a1acf53d586a7ab3628269698ef98dfdfe6118f4156c07f34d3ee6d118eccf':'ctcss_mon',
 '2f987e696a65f59dc4ebb8fc9d8c8142be50945d831004baddc24795b6dda902':'scr_mon',
}
BASE=0x4000

def build(d):
    d=bytearray(d)
    assert len(d)%4==0
    ks=keystone.Ks(keystone.KS_ARCH_ARM,keystone.KS_MODE_THUMB)
    def asm(s,addr):
        b,_=ks.asm(s,addr); return bytes(b)
    def put(addr,old,new):
        o=addr-BASE
        assert d[o:o+len(old)]==bytes(old),(hex(addr),d[o:o+len(old)].hex())
        assert len(old)==len(new),(hex(addr),len(old),len(new))
        d[o:o+len(new)]=new

    caveA=BASE+len(d)
    # only unconditional b.w to far targets (keystone mis-encodes far bcc.w)
    srcA=f"""
      cmp r1, #1
      ldrb.w r1, [r0, #0xe3]
      bne rx
      tst.w r1, #0x18
      bne showrx
      b.w #{0x18c3c}
    rx:
      tst.w r1, #0x08
      beq showrx
      b.w #{0x18c3c}
    showrx:
      b.w #{0x187de}
    """
    a=asm(srcA,caveA); a+=b'\0'*(-len(a)%4)
    caveB=caveA+len(a)
    srcB=f"""
      cmp r1, #1
      ldrb.w r1, [r5, #0xe3]
      bne rx
      tst.w r1, #0x18
      bne rxtone
      b.w #{0x18e02}
    rx:
      tst.w r1, #0x08
      beq rxtone
      b.w #{0x18de4}
    rxtone:
      b.w #{0x18e6a}
    """
    b=asm(srcB,caveB); b+=b'\0'*(-len(b)%4)

    put(0x1884a,bytes.fromhex('c006'),asm('lsls r0, r0, #28',0x1884a))
    put(0x187da,bytes.fromhex('012941d0'),asm(f'b.w #{caveA}',0x187da))
    put(0x18dd8,bytes.fromhex('012912d0'),asm(f'b.w #{caveB}',0x18dd8))

    # version marker: every 20-byte "V...%03d<suffix>" slot gets an extra 'R'
    n=0; i=d.find(b'V%')
    while i>=0:
        s=bytes(d[i:i+20]); z=s.find(b'\0')
        if b'%03d' in s and 0<z and s[z:]==b'\0'*(20-z):
            suf=s[s.index(b'%03d')+4:z]
            assert suf.isalpha() or suf==b'',s
            new=(b'V%d.%02d.%d.%03d'+suf+b'R').ljust(20,b'\0')
            assert len(new)==20 and new[19]==0,new
            d[i:i+20]=new; n+=1; i+=20
        else: i+=1
        i=d.find(b'V%',i)
    assert n>=1,'version format string not found'
    d+=a+b
    return bytes(d),caveA,caveB,n

if __name__=='__main__':
    src,dst=sys.argv[1],sys.argv[2]
    d=open(src,'rb').read()
    kind=KNOWN.get(hashlib.sha256(d).hexdigest())
    assert kind,'input is not stock V1.01.14.002 or a known mod build from this folder'
    out,ca,cb,n=build(d)
    open(dst,'wb').write(out)
    print(f'base={kind} caveA@{ca:#x} caveB@{cb:#x} fmt_strings={n} size={len(out)}')
    print(hashlib.sha256(out).hexdigest())
