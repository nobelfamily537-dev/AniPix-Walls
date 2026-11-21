#!/usr/bin/env python3
"""Night run 5: Pinterest search scrape for uncovered anime (phone wallpapers)."""
import os, io, json, time, re, urllib.parse
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json, text/javascript, */*; q=0.01",
      "Accept-Language": "en-US,en;q=0.9",
      "X-Requested-With": "XMLHttpRequest",
      "Referer": "https://www.pinterest.com/"}
OUT = "_tmp/nightrun5/pv"
os.makedirs(OUT, exist_ok=True)
diag = {}
QUERIES = [("dorohedoro", "dorohedoro anime wallpaper phone"),
           ("hellsing", "hellsing alucard wallpaper phone"),
           ("tower-of-god", "tower of god anime wallpaper phone"),
           ("samurai-champloo", "samurai champloo wallpaper phone"),
           ("mushishi", "mushishi anime wallpaper phone"),
           ("gachiakuta", "gachiakuta anime wallpaper phone"),
           ("nichijou", "nichijou anime wallpaper phone"),
           ("slam-dunk", "slam dunk anime wallpaper phone")]


def render(im, size=(540, 960)):
    w, h = im.size
    r = h / w
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, size, method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy(); fg.thumbnail(size, Image.LANCZOS)
        bg.paste(fg, ((size[0] - fg.width) // 2, (size[1] - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t); y = int((h - nh) * 0.05)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t); x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def search(q, n=30):
    urls = []
    data = {"options": {"query": q, "scope": "pins", "page_size": n, "bookmarks": []},
            "context": {}}
    try:
        r = requests.get("https://www.pinterest.com/resource/BaseSearchResource/get/",
                         params={"source_url": "/search/pins/?q=" + urllib.parse.quote(q),
                                 "data": json.dumps(data)},
                         headers=UA, timeout=35)
        diag.setdefault("api_status", r.status_code)
        if r.status_code == 200:
            js = r.json()
            res = (((js.get("resource_response") or {}).get("data") or {}).get("results") or [])
            diag.setdefault("api_results", len(res))
            for it in res:
                imgs = it.get("images") or {}
                u = (imgs.get("orig") or {}).get("url") or (imgs.get("736x") or {}).get("url")
                if u:
                    urls.append(u)
    except Exception as e:
        diag.setdefault("api_err", str(e)[:90])
    if not urls:
        try:
            r = requests.get("https://www.pinterest.com/search/pins/", params={"q": q}, headers=UA, timeout=35)
            diag.setdefault("html_status", r.status_code)
            found = re.findall(r'https://i\.pinimg\.com/originals/[^"\\ ]+?\.(?:jpg|jpeg|png)', r.text)
            if not found:
                found = re.findall(r'https://i\.pinimg\.com/736x/[^"\\ ]+?\.(?:jpg|jpeg|png)', r.text)
            urls += list(dict.fromkeys(found))
            diag.setdefault("html_urls", len(urls))
        except Exception as e:
            diag.setdefault("html_err", str(e)[:90])
    return urls


cands, summary = [], {}
for slug, q in QUERIES:
    urls = search(q)
    print("  pinterest %s -> %d urls" % (q, len(urls)), flush=True)
    n = 0
    for u in urls:
        if n >= 8:
            break
        try:
            r = requests.get(u, headers={"User-Agent": UA["User-Agent"]}, timeout=40)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            w, h = im.size
            if h / w < 1.15 or h < 1300 or w < 700:
                continue
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=slug, file=fn, pid=u.split("/")[-1].split(".")[0], site="pinterest",
                              w=w, h=h, url=u, tags=""))
            n += 1
        except Exception as e:
            print("   dl err", type(e).__name__, str(e)[:50], flush=True)
        time.sleep(0.2)
    summary[slug] = n
    print("   previews=%d" % n, flush=True)

json.dump(dict(cands=cands, summary=summary, diag=diag), open("_tmp/nightrun5/candidates.json", "w"), indent=1)
print("TOTAL", len(cands), "DIAG", diag, flush=True)
