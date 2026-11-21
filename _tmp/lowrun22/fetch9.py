#!/usr/bin/env python3
"""Low-count run v22: Bing /images/search -> Pinterest originals."""
import os, io, json, re, html, time, hashlib, urllib.parse
import requests
from PIL import Image, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"}
OUT = "_tmp/lowrun22"
PREV = os.path.join(OUT, "prev9")
os.makedirs(PREV, exist_ok=True)

SERIES = [
    ("quintessential quintuplets", ["quintessential quintuplets anime", "gotoubun no hanayome"]),
    ("a silent voice", ["a silent voice anime", "koe no katachi"]),
    ("food wars", ["food wars anime", "shokugeki no soma"]),
    ("natsume yuujinchou", ["natsume yuujinchou anime"]),
    ("yona of the dawn", ["yona of the dawn anime"]),
    ("oregairu", ["oregairu anime", "yahari ore no seishun"]),
    ("jigokuraku", ["jigokuraku anime"]),
    ("k-on", ["k-on anime"]),
    ("solo leveling", ["solo leveling anime"]),
    ("seraph of the end", ["seraph of the end anime"]),
    ("blue exorcist", ["blue exorcist anime"]),
    ("nisekoi", ["nisekoi anime"]),
]
SUFFIX = [" wallpaper", " phone wallpaper", " aesthetic wallpaper"]
MAXC = 26


def bing_page(q, first):
    url = "https://www.bing.com/images/search"
    try:
        r = requests.get(url, params={"q": q, "first": first, "count": 35, "mkt": "en-US",
                                      "form": "HDRSC3", "qft": "+filterui:aspect-tall"},
                         headers=UA, timeout=30)
        if r.status_code != 200:
            print("  HTTP", r.status_code, q, flush=True)
            return []
    except Exception as e:
        print("  ERR", type(e).__name__, flush=True)
        return []
    out = []
    for blob in re.findall(r'm="(\{&quot;.*?\})"', r.text):
        try:
            j = json.loads(html.unescape(blob))
        except Exception:
            continue
        out.append((j.get("murl") or "", j.get("turl") or ""))
    return out


def key(u):
    m = re.search(r"/([0-9a-f]{20,})\.(?:jpg|png|webp)", u)
    return m.group(1) if m else hashlib.md5(u.encode()).hexdigest()


cands = []
for app, names in SERIES:
    pool, seen = [], set()
    for nm in names:
        for sfx in SUFFIX:
            for first in (1, 36, 71):
                res = bing_page(nm + sfx, first)
                for murl, turl in res:
                    if not murl or not turl or murl.startswith("data:"):
                        continue
                    k = key(murl)
                    if k in seen:
                        continue
                    seen.add(k)
                    pool.append((murl, turl))
                time.sleep(0.7)
    print("== %s pool=%d" % (app, len(pool)), flush=True)

    idx = 0
    slug = "".join(c if c.isalnum() else "-" for c in app)[:26]
    pool.sort(key=lambda p: 0 if "pinimg.com" in p[0] else 1)
    for murl, turl in pool:
        if idx >= MAXC:
            break
        try:
            r = requests.get(turl, headers=UA, timeout=30)
            if r.status_code != 200 or len(r.content) < 3000:
                continue
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception:
            continue
        if im.height / im.width < 1.25:
            continue
        name = "%s_%02d" % (slug, idx)
        im.save(os.path.join(PREV, name + ".jpg"), "JPEG", quality=85)
        cands.append(dict(series=app, idx=idx, name=name, site="pinterest", pid=key(murl),
                          w=im.width, h=im.height, url=murl, prev=turl, tags=""))
        idx += 1
        time.sleep(0.15)
    print("   kept=%d" % idx, flush=True)

json.dump(cands, open(os.path.join(OUT, "cand9.json"), "w"), indent=1)
print("total:", len(cands), flush=True)

by = {}
for c in cands:
    by.setdefault(c["series"], []).append(c)
for s, items in by.items():
    slug = "".join(c if c.isalnum() else "-" for c in s)[:26]
    for part in range(0, len(items), 20):
        chunk = items[part:part + 20]
        cols, cw, ch = 5, 265, 475
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw, rows * ch), (16, 16, 20))
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(chunk):
            p = Image.open(os.path.join(PREV, c["name"] + ".jpg")).convert("RGB")
            p.thumbnail((cw - 8, ch - 20), Image.LANCZOS)
            x = (i % cols) * cw + (cw - p.width) // 2
            y = (i // cols) * ch + 18
            sheet.paste(p, (x, y))
            d.text(((i % cols) * cw + 5, 4 + (i // cols) * ch), "#%d" % c["idx"], fill=(255, 235, 0))
        sheet.save(os.path.join(OUT, "sh9_%s_%d.jpg" % (slug, part // 20)), "JPEG", quality=90)
    print("sheet", s, len(items), flush=True)
