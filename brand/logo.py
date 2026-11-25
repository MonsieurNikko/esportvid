"""GGFEZ brand assets (run from the brand/ folder): avatar, wordmark, watermark, YouTube banner."""
import math, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
FONTS = Path(__file__).resolve().parent.parent / 'fonts'
ANTON = str(FONTS / 'Anton-Regular.ttf'); INTER = str(FONTS / 'Inter-Black.otf')
OR=(242,163,58); WH=(255,255,255); BG=(11,14,20); BG2=(24,30,44); CT=(96,172,255)
def F(p,s): return ImageFont.truetype(p,s)
def reticle(d, cx, cy, r, w, col, gap=0.32, tick=0.55, dot=True):
    d.ellipse((cx-r,cy-r,cx+r,cy+r), outline=col, width=w)
    for ang in (0,90,180,270):
        a=math.radians(ang); x0,y0=cx+math.cos(a)*r*(1-tick*0.5), cy+math.sin(a)*r*(1-tick*0.5)
        x1,y1=cx+math.cos(a)*r*(1+tick*0.45), cy+math.sin(a)*r*(1+tick*0.45)
        d.line((x0,y0,x1,y1), fill=col, width=w)
    if dot: d.ellipse((cx-w*0.9,cy-w*0.9,cx+w*0.9,cy+w*0.9), fill=col)
def text_center(d, cx, cy, txt, font, fill, stroke=0, skew=False):
    bb=d.textbbox((0,0),txt,font=font,stroke_width=stroke); w,h=bb[2]-bb[0],bb[3]-bb[1]
    d.text((cx-w/2-bb[0], cy-h/2-bb[1]), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=BG)
def glow(img, rad=18, strength=1.0):
    g=img.filter(ImageFilter.GaussianBlur(rad)); return Image.alpha_composite(Image.new('RGBA',img.size,(0,0,0,0)), g) if strength else img

# ---------- 1. avatar (square, circle-safe)
S=1080; av=Image.new('RGBA',(S,S),BG+(255,))
yy,xx=np.mgrid[0:S,0:S]; r=np.sqrt((xx-S/2)**2+(yy-S/2)**2)/(S/2)
bgarr=np.array(av).astype(float); m=np.clip(1-r,0,1)[...,None]
bgarr[...,:3]=np.array(BG)*(1-m*0.9)+np.array(BG2)*(m*0.9); av=Image.fromarray(bgarr.astype(np.uint8))
lay=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(lay)
reticle(d,S/2,S/2-10,380,22,OR+(255,),dot=False)
gl=lay.filter(ImageFilter.GaussianBlur(16)); av=Image.alpha_composite(av,gl); av=Image.alpha_composite(av,lay)
t=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(t)
text_center(d,S/2,S/2-60,'GG',F(ANTON,380),WH+(255,))
text_center(d,S/2,S/2+190,'F E Z',F(ANTON,120),OR+(255,))
sh=t.filter(ImageFilter.GaussianBlur(10)); sh2=Image.new('RGBA',(S,S),(0,0,0,0)); sh2.putalpha(sh.getchannel('A').point(lambda v:int(v*0.6)))
av=Image.alpha_composite(av,sh2); av=Image.alpha_composite(av,t)
av.convert('RGB').save('ggfez_avatar_1080.png')

# ---------- 2. horizontal wordmark (transparent)
Wm,Hm=2200,600; wm=Image.new('RGBA',(Wm,Hm),(0,0,0,0)); d=ImageDraw.Draw(wm)
reticle(d,300,300,170,18,OR+(255,),dot=True)
f=F(ANTON,330); x=560
for part,colr in (('GG',WH),('F',WH),('EZ',OR)):
    bb=d.textbbox((0,0),part,font=f); d.text((x-bb[0],300-(bb[3]-bb[1])/2-bb[1]),part,font=f,fill=colr+(255,)); x+=bb[2]-bb[0]+18
wm=wm.crop(wm.getbbox()); pad=40; out=Image.new('RGBA',(wm.width+2*pad,wm.height+2*pad),(0,0,0,0)); out.paste(wm,(pad,pad),wm)
out.save('ggfez_wordmark_transparent.png')
dark=Image.new('RGBA',out.size,BG+(255,)); Image.alpha_composite(dark,out).convert('RGB').save('ggfez_wordmark_dark.png')

# ---------- 3. watermark for videos (small reticle + @GGFEZ), transparent
wmk=Image.new('RGBA',(520,90),(0,0,0,0)); d=ImageDraw.Draw(wmk)
reticle(d,45,45,26,5,OR+(255,),dot=True)
d.text((92,45),'@ggfezstudio',font=F(INTER,40),fill=WH+(255,),anchor='lm',stroke_width=3,stroke_fill=(0,0,0,255))
wmk=wmk.crop(wmk.getbbox()); wmk.save('ggfez_watermark.png')

# ---------- 4. YouTube banner 2560x1440 (safe area centre 1546x423)
B=Image.new('RGBA',(2560,1440),BG+(255,)); d=ImageDraw.Draw(B,'RGBA')
for x in range(0,2560,64): d.line((x,0,x,1440),fill=(255,255,255,8))
for y in range(0,1440,64): d.line((0,y,2560,y),fill=(255,255,255,8))
reticle(d,1280,720,560,6,(242,163,58,60),dot=False)
wmS=out.resize((int(out.width*0.62),int(out.height*0.62)),Image.LANCZOS); B.paste(wmS,(1280-wmS.width//2,690-wmS.height//2),wmS)
d.text((1280,900),'CLUTCHES  ·  SCANDALS  ·  GUESS THE PRO',font=F(INTER,44),fill=(150,158,172,255),anchor='mm')
B.convert('RGB').save('ggfez_banner_2560x1440.png')
# preview sheet
pv=Image.new('RGB',(1600,900),(30,30,30)); a=av.convert('RGB').resize((520,520)); pv.paste(a,(30,30))
mask=Image.new('L',(520,520),0); ImageDraw.Draw(mask).ellipse((0,0,519,519),fill=255); c=Image.new('RGB',(520,520),(30,30,30)); c.paste(a,(0,0),mask); pv.paste(c,(30,560-170+200) if False else (580,30))
w2=Image.open('ggfez_wordmark_dark.png').convert('RGB'); w2=w2.resize((1000,int(1000*w2.height/w2.width))); pv.paste(w2,(560,600))
k=Image.new('RGB',(600,160),(40,48,62)); kw=Image.open('ggfez_watermark.png'); k.paste(kw,(40,(160-kw.height)//2),kw); pv.paste(k,(30,600))
bn=Image.open('ggfez_banner_2560x1440.png').convert('RGB').resize((440,248)); pv.paste(bn,(1130,30))
pv.save('brand_preview.jpg',quality=88)
