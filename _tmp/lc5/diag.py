import io, json, os
import numpy as np, requests
from PIL import Image
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}
cfg=json.load(open("_tmp/lc5/rr.json"))
keys={i["id"]:i["key"] for i in cfg["items"]}
WANT=["wpx1927a9a127","wpx670be295e7","wpx2b8a2c056e","wpx5bb3e7ba7c","wpx81aa064347","wpxa66491f2f1"]
os.makedirs("_tmp/lc5/raw", exist_ok=True)
for i in WANT:
    k=keys.get(i)
    if not k:
        print("no key", i); continue
    wid=k[2:]
    got=False
    for ext in ("jpg","png"):
        u=f"https://w.wallhaven.cc/full/{wid[:2]}/wallhaven-{wid}.{ext}"
        r=requests.get(u,headers=UA,timeout=60)
        if r.status_code==200 and len(r.content)>20000:
            open(f"_tmp/lc5/raw/{i}.{ext}","wb").write(r.content)
            im=Image.open(io.BytesIO(r.content)); im.load()
            print(i, k, ext, im.size, im.mode, flush=True)
            got=True; break
    if not got: print(i, k, "FETCHFAIL", flush=True)
