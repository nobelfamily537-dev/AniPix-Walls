import io, json
import numpy as np, requests
from PIL import Image
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}
cfg=json.load(open("_tmp/lc5/rr.json"))
for it in cfg["items"][:6]:
    k=it["key"]; wid=k[2:]
    for ext in ("jpg","png"):
        u=f"https://w.wallhaven.cc/full/{wid[:2]}/wallhaven-{wid}.{ext}"
        r=requests.get(u,headers=UA,timeout=60)
        if r.status_code==200 and len(r.content)>20000:
            im=Image.open(io.BytesIO(r.content)); im.load()
            a=np.asarray(im.convert("L").resize((135,240)),dtype=np.float32)
            m=a>20
            ys=np.where(m.any(axis=1))[0]; xs=np.where(m.any(axis=0))[0]
            print(k, ext, im.size, im.mode, "cov=%.2f"%(m.mean()),
                  "yb=%.2f-%.2f"%(ys[0]/240,(ys[-1]+1)/240) if len(ys) else "noy",
                  "xb=%.2f-%.2f"%(xs[0]/135,(xs[-1]+1)/135) if len(xs) else "nox", flush=True)
            break
