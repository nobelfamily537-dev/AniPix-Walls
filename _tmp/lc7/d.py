import io, json
import numpy as np, requests
from PIL import Image
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}
for k in ("whq2x255","whpk5zgm","whwqv1kr"):
    wid=k[2:]
    for ext in ("jpg","png"):
        r=requests.get(f"https://w.wallhaven.cc/full/{wid[:2]}/wallhaven-{wid}.{ext}",headers=UA,timeout=90)
        if r.status_code==200 and len(r.content)>20000:
            im=Image.open(io.BytesIO(r.content)); im.load()
            print(k, ext, im.size, im.mode, im.getbands(), flush=True)
            if im.mode in ("RGBA","LA","P"):
                rgba=im.convert("RGBA"); a=np.asarray(rgba.getchannel("A"),dtype=np.uint8)
                print("  alpha<10 frac %.3f"%( (a<10).mean()), "min",a.min(),"max",a.max(), flush=True)
                print("  bottom20 alpha mean %.1f"%a[int(a.shape[0]*0.8):].mean(), flush=True)
            g=np.asarray(im.convert("L"))
            print("  bottom20 lum mean %.1f"%g[int(g.shape[0]*0.8):].mean(), flush=True)
            break
