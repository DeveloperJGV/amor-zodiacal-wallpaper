import numpy as np, pickle, sys, os, math
from PIL import Image
from scipy import ndimage as nd
D = pickle.load(open("seg.pkl","rb"))
im,bg,ink,lab,comps = D['im'],D['bg'],D['ink'],D['lab'],D['comps']
H,W,_ = im.shape
FPS=30; T=10.0; N=int(FPS*T)
rng = np.random.default_rng(7)
res = im-bg                      # ink residual rgb
GLOW = np.array([255,175,140],np.float32)/255
GOLD = np.array([255,215,170],np.float32)/255

def crop(c, m):
    sl=c['sl']; y0=max(sl[0].start-m,0); y1=min(sl[0].stop+m,H); x0=max(sl[1].start-m,0); x1=min(sl[1].stop+m,W)
    return (slice(y0,y1),slice(x0,x1))
items=[]
for i,c in enumerate(comps):
    k=c['k']
    if k=='dot' and c['area']<12: continue
    m = {'heart':40,'sign':30,'spark':26,'line':12,'dot':8}[k]
    sl=crop(c,m)
    msk=(lab[sl]==i+1)
    msk=nd.binary_dilation(msk,iterations=2)
    a=(ink[sl]*msk).astype(np.float32)
    r=res[sl]*msk[...,None]
    blur=nd.gaussian_filter(a, {'heart':14,'sign':12,'spark':8,'line':5,'dot':4}[k])
    blur/= max(blur.max(),1e-3)
    it=dict(k=k,sl=sl,a=a,r=r,blur=blur,cy=c['cy'],cx=c['cx'],ph=rng.random(),f=int(rng.integers(1,3)))
    if k=='spark':
        hh=sl[0].stop-sl[0].start; ww=sl[1].stop-sl[1].start
        yy,xx=np.mgrid[0:hh,0:ww]; cy,cx=(c['cy']-sl[0].start),(c['cx']-sl[1].start)
        dy,dx=np.abs(yy-cy),np.abs(xx-cx)
        flare=np.exp(-dx/1.2)*np.exp(-dy/(hh*0.35))+np.exp(-dy/1.2)*np.exp(-dx/(ww*0.35))+np.exp(-(dx**2+dy**2)/20)
        it['flare']=flare/flare.max(); it['big']=c['area']>250
    items.append(it)
hearts=[i for i in items if i['k']=='heart']
# heart: frame removes original heart residual and draws scaled one
base = im.copy()
for h in hearts: base[h['sl']] -= h['r']

# floating motes
NP=70
P=dict(x=rng.uniform(0,W,NP),y=rng.uniform(0,H,NP),k=rng.integers(1,3,NP),ph=rng.random(NP),
       sz=rng.uniform(1.5,4.0,NP),dr=rng.uniform(80,220,NP),sw=rng.uniform(10,30,NP))
def sprite(s):
    r=int(s*4); yy,xx=np.mgrid[-r:r+1,-r:r+1]; return np.exp(-(xx**2+yy**2)/(2*s*s))
SPR={i:sprite(P['sz'][i]) for i in range(NP)}

def beat(u):   # lub-dub in [0,1) -> 0..1
    return math.exp(-((u-0.0)/0.035)**2)+0.65*math.exp(-((u-0.13)/0.04)**2) + (math.exp(-((u-1)/0.035)**2))
def add(F, sl, arr):
    F[sl]+=arr
def frame(n):
    t=n/N
    F=base.copy()
    Y=-500+(H+1000)*t   # light wave top->bottom once per loop
    for it in items:
        k=it['k']; sl=it['sl']
        wave=math.exp(-((it['cy']-Y)/260)**2)
        if k=='spark':
            u=(it['f']*t+it['ph'])%1
            tw=math.sin(math.pi*u)**8          # sharp twinkle
            g=0.35*tw+0.5*wave
            F[sl]+= it['r']*(g*1.2) + (it['blur']*(0.45*tw+0.3*wave)*70)[...,None]*GLOW
            if it['big']: F[sl]+= (it['flare']*tw*110)[...,None]*GOLD
        elif k=='heart':
            u=(2*t+it['ph'])%1
            b=beat(u)
            sc=1+0.07*b
            hh=sl[0].stop-sl[0].start; ww=sl[1].stop-sl[1].start
            out=np.zeros((hh,ww,3),np.float32)
            for ch in range(3):
                img=Image.fromarray(it['r'][...,ch]).resize((round(ww*sc),round(hh*sc)),Image.BICUBIC)
                a=np.asarray(img); oy=(a.shape[0]-hh)//2; ox=(a.shape[1]-ww)//2
                out[...,ch]=a[oy:oy+hh,ox:ox+ww]
            F[sl]+= out*(1+0.5*b+0.4*wave) + (it['blur']*(0.5*b+0.3*wave)*80)[...,None]*GLOW
        elif k=='sign':
            br=0.5+0.5*math.sin(2*math.pi*(t+it['ph']))
            g=0.25*br+0.7*wave
            F[sl]+= it['r']*g + (it['blur']*(0.25*br+0.6*wave)*60)[...,None]*GLOW
        else:  # lines & dots: shimmer with wave + slow sparkle
            u=(it['f']*t+it['ph'])%1
            g=0.9*wave+ (0.3*math.sin(math.pi*u)**6 if k=='dot' else 0)
            F[sl]+= it['r']*g*1.3 + (it['blur']*g*50)[...,None]*GLOW
    for i in range(NP):
        u=(P['k'][i]*t+P['ph'][i])%1
        al=math.sin(math.pi*u)**2
        y=P['y'][i]-P['dr'][i]*u; x=P['x'][i]+P['sw'][i]*math.sin(2*math.pi*u)
        s=SPR[i]; r=s.shape[0]//2; yi,xi=int(y),int(x)
        if r<yi<H-r-1 and r<xi<W-r-1:
            F[yi-r:yi+r+1,xi-r:xi+r+1]+=(s*al*120)[...,None]*GOLD
    return np.clip(F,0,255).astype(np.uint8)
if __name__=="__main__":
    out=sys.argv[1]; os.makedirs(out,exist_ok=True)
    a,b=int(sys.argv[2]),int(sys.argv[3])
    for n in range(a,b):
        Image.fromarray(frame(n)).save(f"{out}/f{n:04d}.png",compress_level=1)
