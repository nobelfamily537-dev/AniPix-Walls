#!/usr/bin/env python3
"""Night gap-fill run stage 2: process picked candidates, add to wallpapers.json, commit."""
import io, json, os, re, sys, hashlib
import requests
from PIL import Image, ImageOps, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://konachan.net/"}
OUT = "_tmp/night19"
TODAY = "2026-11-17"
BASE = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"

picks = json.load(open(os.path.join(OUT, "picks.json")))
cands = {}
for fn in ("cands.json", "cands2.json", "cands3.json"):
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        for c in json.load(open(p)):
            cands[c["pid"]] = c
data = json.load(open("wallpapers.json"))

existing = set()
for cat, arr in data["categories"].items():
    for w in arr:
        for k in ("full", "thumb", "alt"):
            if w.get(k):
                existing.add(w[k])


def make_id(pid):
    h = hashlib.sha1(("night19-%s" % pid).encode()).hexdigest()
    return "wpx" + h[:10]


def fit916(im):
    w, h = im.size
    target = 16 / 9
    r = h / w
    if r > target:
        nh = int(w * target)
        y = int((h - nh) * 0.35)
        im = im.crop((0, y, w, y + nh))
    else:
        nw = int(h / target)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    return im.resize((1080, 1920), Image.LANCZOS)


added = []
sheet_items = []
for p in picks:
    pid = p["pid"]
    c = cands.get(pid)
    if not c:
        print("SKIP no candidate", pid)
        continue
    cat = p["category"]
    assert cat in ("anime", "anime2"), cat
    wid = make_id(pid)
    full_url = "%s/%s/%s.jpg" % (BASE, cat, wid)
    thumb_url = "%s/%s/%s_thumb.jpg" % (BASE, cat, wid)
    if full_url in existing:
        print("SKIP dup url", wid)
        continue
    try:
        r = requests.get(c["url"], headers=UA, timeout=60)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print("SKIP dl err", pid, type(e).__name__)
        continue
    final = fit916(im)
    os.makedirs(cat, exist_ok=True)
    final.save(os.path.join(cat, wid + ".jpg"), "JPEG", quality=95, optimize=True, subsampling=1)
    final.resize((360, 640), Image.LANCZOS).save(os.path.join(cat, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
    tags = p["tags"]
    entry = {"id": wid, "thumb": thumb_url, "full": full_url, "alt": full_url, "tags": tags, "date": TODAY}
    data["categories"][cat].append(entry)
    for t in [x.strip() for x in tags.split(",") if x.strip()]:
        lst = data.setdefault("tags", {}).setdefault(t, [])
        if wid not in lst:
            lst.append(wid)
    added.append((cat, wid, p.get("series")))
    sheet_items.append((cat, wid, os.path.join(cat, wid + "_thumb.jpg")))

if not added:
    print("NOTHING ADDED")
    sys.exit(0)

data["version"] = int(data.get("version", 0)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))

COLS, ROWS = 5, 4
CW, CH = 240, 427
for i in range(0, len(sheet_items), COLS * ROWS):
    chunk = sheet_items[i:i + COLS * ROWS]
    sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
    dr = ImageDraw.Draw(sheet)
    for k, (cat, wid, path) in enumerate(chunk):
        im = Image.open(path).convert("RGB").resize((CW, CH), Image.LANCZOS)
        x, y = (k % COLS) * CW, (k // COLS) * CH
        sheet.paste(im, (x, y))
        dr.rectangle([x, y, x + 130, y + 16], fill=(0, 0, 0))
        dr.text((x + 4, y + 3), "%s %s" % (cat, wid), fill=(255, 255, 0))
    sheet.save(os.path.join(OUT, "final_%d.jpg" % (i // (COLS * ROWS))), "JPEG", quality=88, optimize=True)

json.dump([{"cat": a[0], "id": a[1], "series": a[2]} for a in added],
          open(os.path.join(OUT, "added.json"), "w"), indent=1)
print("ADDED", len(added))
for a in added:
    print("  ", a)
