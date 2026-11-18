#!/usr/bin/env python3
"""Low-count run stage 2: process picked candidates into <cat>/<id>.jpg + thumb, update wallpapers.json.
Usage: python _tmp/low21/process.py picks_batch1.json [--bump]"""
import io, json, os, sys, hashlib, time
import requests
from PIL import Image, ImageOps, ImageDraw

UA_BASE = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
REFERERS = {"k": "https://konachan.net/", "d": "https://danbooru.donmai.us/", "s": "https://safebooru.donmai.us/"}
def hdrs(pid):
    h = dict(UA_BASE)
    h["Referer"] = REFERERS.get(str(pid)[:1], "https://danbooru.donmai.us/")
    h["Accept"] = "image/avif,image/webp,image/jpeg,image/*,*/*"
    return h
OUT = "_tmp/low21"
TODAY = "2026-11-18"
BASE = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"

batch = sys.argv[1]
do_bump = "--bump" in sys.argv
picks = json.load(open(os.path.join(OUT, batch)))
data = json.load(open("wallpapers.json"))

existing = set()
for cat, arr in data["categories"].items():
    for w in arr:
        for k in ("full", "thumb", "alt"):
            if w.get(k):
                existing.add(w[k])

reg_path = os.path.join(OUT, "seen_urls.json")
seen_urls = set()
if os.path.exists(reg_path):
    try:
        seen_urls = set(json.load(open(reg_path)))
    except Exception:
        seen_urls = set()


def make_id(key):
    h = hashlib.sha1(("low21-%s" % key).encode()).hexdigest()
    return "wpx" + h[:10]


def fit916(im, crop="c"):
    w, h = im.size
    target = 16 / 9
    r = h / w
    fx = {"l": 0.12, "c": 0.5, "r": 0.88}.get(crop, 0.5)
    if r > target:
        nh = int(w * target)
        y = int((h - nh) * 0.30)
        im = im.crop((0, y, w, y + nh))
    else:
        nw = int(h / target)
        x = int((w - nw) * fx)
        x = max(0, min(x, w - nw))
        im = im.crop((x, 0, x + nw, h))
    return im.resize((1080, 1920), Image.LANCZOS)


added = []
stats = {}
for p in picks:
    pid = p["pid"]
    url = p["url"]
    cat = p["category"]
    if cat not in ("anime", "anime2", "game", "nature"):
        print("SKIP bad cat", cat, pid)
        continue
    if url in seen_urls:
        print("SKIP dup source", pid)
        continue
    wid = make_id(pid)
    full_url = "%s/%s/%s.jpg" % (BASE, cat, wid)
    thumb_url = "%s/%s/%s_thumb.jpg" % (BASE, cat, wid)
    if full_url in existing or thumb_url in existing:
        print("SKIP dup url", wid)
        continue
    im = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=hdrs(pid), timeout=90)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            break
        except Exception as e:
            print("  dl retry", pid, type(e).__name__, getattr(getattr(e, "response", None), "status_code", ""), flush=True)
            time.sleep(3)
    if im is None:
        print("SKIP dl err", pid)
        continue
    if im.width < 600 or im.height < 700:
        print("SKIP small", pid, im.size)
        continue
    final = fit916(im, p.get("crop", "c"))
    os.makedirs(cat, exist_ok=True)
    final.save(os.path.join(cat, wid + ".jpg"), "JPEG", quality=95, optimize=True, subsampling=1)
    final.resize((360, 640), Image.LANCZOS).save(os.path.join(cat, wid + "_thumb.jpg"), "JPEG", quality=80, optimize=True)
    tags = p["tags"].strip().strip(",")
    entry = {"id": wid, "thumb": thumb_url, "full": full_url, "alt": full_url, "tags": tags, "date": TODAY}
    data["categories"][cat].append(entry)
    existing.add(full_url)
    existing.add(thumb_url)
    seen_urls.add(url)
    added.append(entry)
    s = p.get("series", "?")
    stats[s] = stats.get(s, 0) + 1
    print("ADDED", cat, wid, s, flush=True)

if do_bump:
    data["version"] = int(data.get("version", 1)) + 1
    data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(sorted(seen_urls), open(reg_path, "w"), indent=0)

print("TOTAL ADDED", len(added))
print("PER SERIES", json.dumps(stats, indent=1))
with open(os.path.join(OUT, "stats.txt"), "w") as f:
    f.write("%d %d\n" % (len(added), len(stats)))
    for k, v in sorted(stats.items()):
        f.write("%s=%d\n" % (k, v))

COLS, ROWS = 6, 4
CW, CH = 200, 356
items = added
for i in range(0, len(items), COLS * ROWS):
    chunk = items[i:i + COLS * ROWS]
    sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
    for k, e in enumerate(chunk):
        fp = os.path.join("_tmp/low21/final", os.path.basename(e["full"]))
        if not os.path.exists(fp):
            continue
        im = Image.open(fp).convert("RGB").resize((CW, CH), Image.LANCZOS)
        sheet.paste(im, ((k % COLS) * CW, (k // COLS) * CH))
    os.makedirs(os.path.join(OUT, "finalsheets"), exist_ok=True)
    sheet.save(os.path.join(OUT, "finalsheets", "final_%d.jpg" % (i // (COLS * ROWS))), "JPEG", quality=88, optimize=True)
print("done")
