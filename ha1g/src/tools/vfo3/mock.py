# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
from PIL import Image, ImageDraw
from font import d,u32,font,B,width
F8,F16=0x68918,0x6ba98
def text(img,f,x,y,s,col,clip=None):
    ys,r=font(f); first,last,ci=r[0]
    for ch in s:
        e=ci+(ord(ch)-first)*8; xs,xd,bpl=d[e-B],d[e-B+1],d[e-B+2]; p=u32(e+4)
        for yy in range(ys):
            row=d[p-B+yy*bpl:p-B+(yy+1)*bpl]; bits=''.join(f'{b:08b}' for b in row)
            for xx in range(xs):
                X,Y=x+xx,y+yy
                if bits[xx]=='1' and 0<=X<160 and 0<=Y<128 and (clip is None or (clip[0]<=X<clip[2] and clip[1]<=Y<clip[3])):
                    img.putpixel((X,Y),col)
        x+=xd
BLUE=(30,100,230); WHITE=(245,248,255); BLK=(10,10,20); WHT=(255,255,255)
panels=[('A11','C35','','','L','2M CALL','146.52000','CH-35'),
        ('A11','C29','+','CTC','L','PICNIC POINT','462.70000','CH-29'),
        ('Z1','C1','','','H','GMRS 01','462.56250','CH-1')]
def screen(new,sel=1):
    im=Image.new('RGB',(160,128),WHITE); dr=ImageDraw.Draw(im)
    text(im,F8,120,5,'61%',BLUE); dr.rectangle((117,2,157,14),outline=BLUE)
    for i,(zone,ch,ic1,ic2,pw,name,freq,chl) in enumerate(panels):
        y0=16+31*i; bg=WHITE if i==sel else BLUE
        dr.rectangle((0,y0,159,y0+30),fill=bg)
        c=BLK if i==sel else (WHT if i==0 else BLK)
        text(im,F8,2,y0+4,zone,c); text(im,F8,26,y0+4,ch,c)
        if ic1: text(im,F8,70,y0+3,ic1,c)
        if ic2: text(im,F8,118,y0+3,ic2,c)
        text(im,F8,149,y0+4,pw,c)
        if not new:
            text(im,F16,34,y0+11,name,BLK,(33,y0+10,133,y0+28))
            text(im,F8,2,y0+21,chl,c); text(im,F8,34,y0+21,freq,c)
            text(im,F8,149,y0+21,'W',c)
        else:
            text(im,F16,3,y0+12,name,BLK,(2,y0+11,92,y0+29))
            text(im,F8,95,y0+14,freq,c); text(im,F8,95,y0+23,chl,c)
            text(im,F8,149,y0+21,'W',c)
    # scope strip (y110..127)
    dr.rectangle((0,110,159,127),fill=(225,240,255)); dr.rectangle((2,111,70,113),fill=BLUE)
    import random; random.seed(3)
    for k in range(37):
        h=random.choice([1,1,2,2,3]) if k!=18 else 6
        dr.rectangle((4+k*4,127-h,6+k*4,127),fill=(40,200,220) if k==18 else BLUE)
    return im
if __name__=="__main__":
  S=4
  now,new=screen(False),screen(True)
  out=Image.new('RGB',(160*S*2+60,128*S+60),(40,40,40)); dr=ImageDraw.Draw(out)
  out.paste(now.resize((160*S,128*S),Image.NEAREST),(20,40)); out.paste(new.resize((160*S,128*S),Image.NEAREST),(160*S+40,40))
  dr.text((20,12),'NOW (stock 3-panel layout)',fill=(255,255,255)); dr.text((160*S+40,12),'NEW (proposed)',fill=(255,255,255))
  import sys; out.save(sys.argv[1]); new.resize((320,256),Image.NEAREST).save(sys.argv[1].replace('.png','_new_2x.png'))
  print(width(F16,'PICNIC POINT'), 'max name px 89')
