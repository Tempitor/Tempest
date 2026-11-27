# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
import struct,sys
import os
# The stock emWin font tables are read from YOUR firmware file (any V1.01.14.002 image: stock or a
# Tempest build), named by the HA1G_IMG environment variable. build.sh sets it to the stock file.
if 'HA1G_IMG' not in os.environ: sys.exit('set HA1G_IMG to your stock HA1G_V1.01.14.002_20260422.bin')
d=open(os.environ['HA1G_IMG'],'rb').read(); B=0x4000
def u32(a): return struct.unpack_from('<I',d,a-B)[0]
def font(f):
    ys,yd=d[f-B+24],d[f-B+25]; p=u32(f+28)
    ranges=[]
    while p and B<=p<0x80000:
        first,last=struct.unpack_from('<HH',d,p-B); ci=u32(p+4); nxt=u32(p+8)
        ranges.append((first,last,ci)); p=nxt
        if len(ranges)>40: break
    return ys,ranges
def width(f,s):
    ys,r=font(f); w=0
    for ch in s:
        c=ord(ch)
        for first,last,ci in r:
            if first<=c<=last:
                w+=d[ci-B+(c-first)*8+1]; break
    return w
if __name__=='__main__':
  for f in (0x6ba98,0x6b010,0x68918,0x6a570,0x6dab0):
    ys,r=font(f); print(hex(f),'YSize',ys,[(hex(a),hex(b)) for a,b,_ in r][:4], {s:width(f,s) for s in ('462.56250','PICNIC POINT','2M CALL','GMRS 01','CH-35','A11','C35','MMMMMMMMMMMMMM','W')})
