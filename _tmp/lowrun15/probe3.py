import io, requests
from PIL import Image
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json,*/*"}
r=requests.get("https://wallhaven.cc/api/v1/search",params={"q":"berserk","purity":"100","categories":"010"},headers=UA,timeout=25)
js=r.json(); d=js["data"][:3]
for p in d:
    print("post",p["id"],p["dimension_x"],p["dimension_y"],"thumbs",p["thumbs"],flush=True)
    for k in ("small","large","original"):
        u=p["thumbs"][k]
        try:
            rr=requests.get(u,headers=dict(UA, Referer="https://wallhaven.cc/"),timeout=25)
            print("  ",k,rr.status_code,rr.headers.get("content-type"),len(rr.content),flush=True)
            try:
                im=Image.open(io.BytesIO(rr.content)); print("    size",im.size,flush=True)
            except Exception as e: print("    img err",type(e).__name__,flush=True)
        except Exception as e:
            print("  ",k,"ERR",type(e).__name__,flush=True)
