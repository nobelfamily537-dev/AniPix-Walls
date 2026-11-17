#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-17) stage 1c: wallhaven portrait candidates + sheets."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from collections import Counter

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json"}

SERIES = [
    ("hyouka",            ["hyouka"]),
    ("rurouni kenshin",   ["rurouni kenshin"]),
    ("toradora",          ["toradora"]),
    ("trigun",            ["trigun"]),
    ("hajime no ippo",    ["hajime no ippo"]),
    ("digimon",           ["digimon"]),
    ("code geass",        ["code geass"]),
    ("cowboy bebop",      ["cowboy bebop"]),
    ("fire force",        ["fire force"]),
    ("horimiya",          ["horimiya"]),
    ("noragami",          ["noragami"]),
    ("your lie in april", ["your lie in april"]),
    ("vinland saga",      ["vinland saga"]),
    ("made in abyss",     ["made in abyss"]),
    ("steins gate",       ["steins gate", "steins;gate"]),
    ("mob psycho 100",    ["mob psycho 100"]),
]

OUT = "_tmp/lowrun19"
PREV = os.path.join(OUT, "prev3")
SHEETS = os.path.join(OUT, "sheets3")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 20


def render(im, size=(360, 640)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.04)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params, timeout=50):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.6)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(4)
    return None


def wallhaven(q):
    out = []
    for page in (1, 2, 3):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "ratios": "9x16",
                 "sorting": "toplist", "order": "desc", "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        data = js.get("data") or []
        for p in data:
            out.append(dict(site="wallhaven", id=p.get("id"), score=0,
                            w=p.get("dimension_x") or 0, h=p.get("dimension_y") or 0,
                            url=p.get("path"), prev=(p.get("thumbs") or {}).get("large"),
                            tags=" ".join(p.get("tags") or []), rating="s",
                            md5=p.get("id")))
        if len(data) < 24:
            break
    if not out:
        for page in (1, 2):
            r = get("https://wallhaven.cc/api/v1/search",
                    {"q": q, "categories": "010", "purity": "100",
                     "sorting": "toplist", "order": "desc", "page": page})
            if not r:
                break
            try:
                js = r.json()
            except Exception:
                break
            data = js.get("data") or []
            for p in data:
                out.append(dict(site="wallhaven", id=p.get("id"), score=0,
                                w=p.get("dimension_x") or 0, h=p.get("dimension_y") or 0,
                                url=p.get("path"), prev=(p.get("thumbs") or {}).get("large"),
                                tags=" ".join(p.get("tags") or []), rating="s",
                                md5=p.get("id")))
            if len(data) < 24:
                break
    return out


cands = []
seen_ids = set()
for name, queries in SERIES:
    pool = []
    for q in queries:
        got = wallhaven(q)
        print("  %s wallhaven %r -> %d" % (name, q, len(got)), flush=True)
        pool += got
        if len(pool) >= 60:
            break
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    for p in pool:
        key = p["id"]
        if key in seen or key in seen_ids:
            continue
        seen.add(key)
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r < 1.3:
            continue
        if h < 1500 or w < 800:
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=60)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
            seen_ids.add(p["id"])
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands3.json"), "w"), indent=1)

COLS, ROWS = 5, 4
CW, CH = 300, 533
per = COLS * ROWS
byseries = {}
for c in cands:
    byseries.setdefault(c["slug"], []).append(c)
for slug, items in byseries.items():
    for si in range(0, len(items), per):
        chunk = items[si:si + per]
        sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for k, c in enumerate(chunk):
            im = Image.open(os.path.join(PREV, c["file"])).convert("RGB").resize((CW, CH), Image.LANCZOS)
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 34, y + 20], fill=(0, 0, 0))
            dr.text((x + 5, y + 5), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // per)), "JPEG", quality=86, optimize=True)

print("TOTAL candidates", len(cands), flush=True)
print("sheets:", sorted(os.listdir(SHEETS)), flush=True)
