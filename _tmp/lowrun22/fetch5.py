#!/usr/bin/env python3
"""Low-count run v22: Pinterest-style portrait candidates via Bing image search."""
import os, io, json, re, html, time, hashlib
import requests
from PIL import Image, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
OUT = "_tmp/lowrun22"
PREV = os.path.join(OUT, "prev5")
os.makedirs(PREV, exist_ok=True)

SERIES = [
    ("quintessential quintuplets", ["quintessential quintuplets", "gotoubun no hanayome"]),
    ("a silent voice", ["a silent voice", "koe no katachi"]),
    ("food wars", ["food wars shokugeki", "shokugeki no soma"]),
    ("natsume yuujinchou", ["natsume yuujinchou", "natsume book of friends"]),
    ("yona of the dawn", ["yona of the dawn", "akatsuki no yona"]),
    ("oregairu", ["oregairu", "yahari ore no seishun"]),
    ("the wind rises", ["the wind rises ghibli", "kaze tachinu"]),
    ("jigokuraku", ["jigokuraku", "hells paradise anime"]),
    ("kuroko no basket", ["kuroko no basket", "kuroko basketball"]),
    ("fire force", ["fire force anime", "enen no shouboutai"]),
    ("akame ga kill", ["akame ga kill"]),
    ("k-on", ["k on anime", "k-on hokago tea time"]),
    ("horimiya", ["horimiya"]),
    ("tokyo revengers", ["tokyo revengers"]),
    ("solo leveling", ["solo leveling"]),
    ("seraph of the end", ["seraph of the end"]),
    ("made in abyss", ["made in abyss"]),
    ("blue exorcist", ["blue exorcist"]),
    ("mashle", ["mashle magic and muscles"]),
    ("nisekoi", ["nisekoi"]),
]
SUFFIX = [" anime wallpaper", " phone wallpaper", " aesthetic wallpaper", " 4k wallpaper", " vertical wallpaper", " lockscreen"]

MAXC = 30


def bing(q, first=1):
    try:
        r = requests.get("https://www.bing.com/images/async",
                         params={"q": q, "first": first, "count": 35, "mkt": "en-US", "adlt": "off"},
                         headers=UA, timeout=30)
        if r.status_code != 200:
            print("  HTTP", r.status_code, q, flush=True)
            return []
    except Exception as e:
        print("  ERR", type(e).__name__, flush=True)
        return []
    out = []
    for blob in re.findall(r'class="iusc"[^>]*?m="(\{.*?\})"', r.text):
        try:
            j = json.loads(html.unescape(blob))
        except Exception:
            continue
        out.append((j.get("murl") or "", j.get("turl") or ""))
    return out


def key(u):
    m = re.search(r"/([0-9a-f]{20,})\.(?:jpg|png|webp)", u)
    return m.group(1) if m else hashlib.md5(u.encode()).hexdigest()


try:
    old = {c["pid"] for c in json.load(open(os.path.join(OUT, "cand4.json")))}
except Exception:
    old = set()
cands = []
for app, names in SERIES:
    pool, seen = [], set()
    for nm in names:
        for sfx in SUFFIX:
            for first in (1, 36, 71):
                for murl, turl in bing(nm + sfx, first):
                    if not murl or not turl or murl.startswith("data:"):
                        continue
                    k = key(murl)
                    if k in seen or k in old:
                        continue
                    seen.add(k)
                    pool.append((murl, turl, k))
                time.sleep(0.6)
    print("== %s pool=%d" % (app, len(pool)), flush=True)

    idx = 0
    slug = "".join(c if c.isalnum() else "-" for c in app)[:26]
    pool.sort(key=lambda p: 0 if "pinimg.com" in p[0] else 1)
    for murl, turl, k in pool:
        if idx >= MAXC:
            break
        try:
            r = requests.get(turl, headers=UA, timeout=30)
            if r.status_code != 200 or len(r.content) < 3000:
                continue
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception:
            continue
        w, h = im.size
        if w < 120 or h < 180:
            continue
        if h / w < 1.3:          # portrait only
            continue
        name = "%s_%02d" % (slug, idx)
        im.save(os.path.join(PREV, name + ".jpg"), "JPEG", quality=85)
        cands.append(dict(series=app, idx=idx, name=name, site="pinterest", pid=k,
                          w=w, h=h, url=murl, prev=turl, tags=""))
        idx += 1
        time.sleep(0.15)
    print("   kept=%d" % idx, flush=True)

json.dump(cands, open(os.path.join(OUT, "cand5.json"), "w"), indent=1)
print("total candidates:", len(cands), flush=True)

by = {}
for c in cands:
    by.setdefault(c["series"], []).append(c)
for s, items in by.items():
    slug = "".join(c if c.isalnum() else "-" for c in s)[:26]
    for part in range(0, len(items), 12):
        chunk = items[part:part + 12]
        cols, cw, ch = 6, 250, 460
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw, rows * ch), (18, 18, 22))
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(chunk):
            p = Image.open(os.path.join(PREV, c["name"] + ".jpg")).convert("RGB")
            p.thumbnail((cw - 8, ch - 20), Image.LANCZOS)
            x = (i % cols) * cw + (cw - p.width) // 2
            y = (i // cols) * ch + 18
            sheet.paste(p, (x, y))
            d.text(((i % cols) * cw + 5, 4 + (i // cols) * ch), "#%d" % c["idx"], fill=(255, 235, 0))
        sheet.save(os.path.join(OUT, "sh5_%s_%d.jpg" % (slug, part // 12)), "JPEG", quality=90)
    print("sheet", s, len(items), flush=True)
