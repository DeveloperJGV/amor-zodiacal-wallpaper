import numpy as np, pickle
from PIL import Image
from scipy import ndimage as nd
W,H = 1080,2340
src = Image.open(r"C:/dev/personal/wallpaper/Wallpaper001.jpeg").convert("RGB")
s = H/src.height
src = src.resize((round(src.width*s), H), Image.LANCZOS)
x0 = (src.width-W)//2
im = np.asarray(src.crop((x0,0,x0+W,H))).astype(np.float32)
# clean background per channel
small = im[::4,::4]
bg = np.stack([nd.median_filter(small[...,c], size=45) for c in range(3)],-1)
bg = nd.zoom(bg,(H/bg.shape[0],W/bg.shape[1],1),order=1)
bg = nd.gaussian_filter(bg,(6,6,0))
L = im.mean(2); d = L-bg.mean(2)
ink = np.clip((d-2)/14,0,1)
bin_ = nd.binary_closing(ink>0.25, iterations=2)
bin_ = nd.binary_fill_holes(bin_)
lab,n = nd.label(bin_)
objs = nd.find_objects(lab)
comps=[]
dbg = np.zeros((H,W,3),np.uint8)
cols={'dot':(90,90,90),'spark':(255,255,0),'heart':(255,60,120),'sign':(80,180,255),'line':(0,255,0)}
for i,sl in enumerate(objs):
    m = lab[sl]==i+1
    area=m.sum(); h=sl[0].stop-sl[0].start; w=sl[1].stop-sl[1].start
    fill=area/(h*w); mi=ink[sl][m].mean()
    if area<60: k='dot'
    elif max(h,w)>260 or fill<0.2: k='line'
    elif fill>0.55 and abs(h-w)<0.35*max(h,w): k='heart' if area>500 else 'dot'
    elif fill<0.45 and h>w*1.15 and max(h,w)<90: k='spark'
    elif area>2500: k='sign'
    else: k='line'
    comps.append(dict(sl=sl,k=k,area=int(area),cy=(sl[0].start+sl[0].stop)/2,cx=(sl[1].start+sl[1].stop)/2))
    dbg[sl][m]=cols[k]
from collections import Counter; print(n, Counter(c['k'] for c in comps))
Image.fromarray(dbg).resize((540,1170)).save("classes.png")
pickle.dump(dict(im=im,bg=bg,ink=ink,lab=lab,comps=comps),open("seg.pkl","wb"))
