#!/usr/bin/env python3
"""Low-count run v22: portrait-only wallhaven candidates."""
import os, io, json, time
import requests
from PIL import Image, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
OUT = "_tmp/lowrun22"
PREV = os.path.join(OUT, "prev3")
os.makedirs(PREV, exist_ok=True)
API = "https://wallhaven.cc/api/v1/search"
RATIOS = "9x16,10x16,9x18,9x19,9x21,2x3"

SERIES = [
    ("quintessential quintuplets", ["gotoubun no hanayome"]),
    ("a silent voice", ["koe no katachi"]),
    ("food wars", ["shokugeki no souma"]),
    ("natsume yuujinchou", ["natsume yuujinchou"]),
    ("yona of the dawn", ["akatsuki no yona"]),
    ("oregairu", ["yahari ore no seishun"]),
    ("the wind rises", ["kaze tachinu"]),
    ("jigokuraku", ["jigokuraku"]),
    ("kuroko no basket", ["kuroko no basket"]),
    ("fire force", ["enen no shouboutai"]),
    ("akame ga kill", ["akame ga kill"]),
    ("k-on", ["k-on"]),
    ("horimiya", ["horimiya"]),
    ("tokyo revengers", ["tokyo revengers"]),
    ("solo leveling", ["solo leveling"]),
    ("seraph of the end", ["owari no seraph"]),
    ("made in abyss", ["made in abyss"]),
    ("blue exorcist", ["ao no exorcist"]),
    ("mashle", ["mashle"]),
    ("nisekoi", ["nisekoi"]),
]

MAXC = 20


def get(params):
    for _ in range(2):
        try:
            r = requests.get(API, params=params, headers=UA, timeout=30)
            if r.status_code == 200:
                time.sleep(0.5)
                return r.json()
            print("  HTTP", r.status_code, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(2)
    return None


cands = []
for app, queries in SERIES:
    pool, seen = [], set()
    for q in queries:
        for sort in ("favorites", "relevance"):
            for page in (1, 2, 3, 4):
                js = get({"q": q, "categories": "010", "purity": "100", "ratios": RATIOS,
                          "atleast": "1080x1920", "sorting": sort, "page": page})
                if not js:
                    break
                items = js.get("data") or []
                for it in items:
                    if it["id"] in seen:
                        continue
                    seen.add(it["id"])
                    pool.append(it)
                if len(items) < 24:
                    break
    print("== %s pool=%d" % (app, len(pool)), flush=True)

    kept = [it for it in pool if it.get("purity") == "sfw"]
    kept.sort(key=lambda i: -int(i.get("favorites") or 0))

    idx = 0
    slug = "".join(c if c.isalnum() else "-" for c in app)[:26]
    for it in kept:
        if idx >= MAXC:
            break
        turl = (it.get("thumbs") or {}).get("large") or (it.get("thumbs") or {}).get("original")
        if not turl:
            continue
        try:
            r = requests.get(turl, headers=UA, timeout=45)
            if r.status_code != 200 or len(r.content) < 5000:
                continue
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception as e:
            print("  skip", type(e).__name__, it["id"], flush=True)
            continue
        name = "%s_%02d" % (slug, idx)
        im.save(os.path.join(PREV, name + ".jpg"), "JPEG", quality=85)
        cands.append(dict(series=app, idx=idx, name=name, site="wallhaven", pid=it["id"],
                          w=int(it["dimension_x"]), h=int(it["dimension_y"]),
                          url=it["path"], prev=turl,
                          tags=" ".join(it.get("tags") or []) if isinstance(it.get("tags"), list) else ""))
        idx += 1
        time.sleep(0.2)

json.dump(cands, open(os.path.join(OUT, "cand3.json"), "w"), indent=1)
print("total candidates:", len(cands), flush=True)

by = {}
for c in cands:
    by.setdefault(c["series"], []).append(c)
for s, items in by.items():
    slug = "".join(c if c.isalnum() else "-" for c in s)[:26]
    for part in range(0, len(items), 10):
        chunk = items[part:part + 10]
        cols, cw, ch = 5, 300, 560
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw, rows * ch), (18, 18, 22))
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(chunk):
            p = Image.open(os.path.join(PREV, c["name"] + ".jpg")).convert("RGB")
            p.thumbnail((cw - 10, ch - 24), Image.LANCZOS)
            x = (i % cols) * cw + (cw - p.width) // 2
            y = (i // cols) * ch + 22
            sheet.paste(p, (x, y))
            d.text(((i % cols) * cw + 6, 6 + (i // cols) * ch), "#%d" % c["idx"], fill=(255, 235, 0))
        sheet.save(os.path.join(OUT, "sh3_%s_%d.jpg" % (slug, part // 10)), "JPEG", quality=90)
    print("sheet", s, len(items), flush=True)
