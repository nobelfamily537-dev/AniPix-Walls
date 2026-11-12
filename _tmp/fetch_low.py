#!/usr/bin/env python3
"""Fetch candidate wallpapers for low-count series from wallhaven.

Full images are downloaded, verified, then reduced to a portrait preview for the
contact sheet. Only previews are committed; candidates.json keeps the full URLs.

Writes:
  _tmp/cand/<slug>/<i>.jpg        preview images (max 360x640)
  _tmp/sheets/<slug>_<n>.jpg      contact sheets (10 per sheet, 5x2, labelled)
  _tmp/candidates.json            per series: index -> {src, full, w, h, q}
"""
import io, json, os, time, hashlib, traceback
import requests
from PIL import Image, ImageDraw, ImageFont

UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.environ.get("CONFIG", "series.json")
OUTJSON = os.environ.get("OUTJSON", "candidates.json")
CAND = os.environ.get("CAND", "cand")
SHEETS = os.environ.get("SHEETS", "sheets")
SERIES = json.load(open(os.path.join(HERE, CONFIG), encoding="utf-8"))
for d in (CAND, SHEETS):
    os.makedirs(os.path.join(HERE, d), exist_ok=True)

MAX_PER_SERIES = 24
PER_SHEET = 10
SEEN = set()
QM = "?"


def get(url, **kw):
    kw.setdefault("timeout", 60)
    kw.setdefault("headers", UA)
    r = requests.get(url, **kw)
    r.raise_for_status()
    return r


def portrait_ok(w, h):
    return w >= 1000 and h >= 1700 and h / float(w) >= 1.25


def wh_url(q, page, atleast=True):
    base = "https://wallhaven.cc/api/v1/search" + QM
    tail = "q=%s&categories=010&purity=100&ratios=portrait&sorting=relevance&page=%d"
    if atleast:
        tail = ("q=%s&categories=010&purity=100&ratios=portrait"
                "&atleast=1080x1920&sorting=relevance&page=%d")
    return base + (tail % (requests.utils.quote(q), page))


def wh_search(q, pages=2):
    out = []
    for atleast in (True, False):
        for page in range(1, pages + 1):
            try:
                js = get(wh_url(q, page, atleast)).json()
            except Exception as e:
                print("  wallhaven FAIL %s p%d: %s" % (q, page, e))
                break
            data = js.get("data", [])
            for it in data:
                try:
                    w, h = [int(x) for x in it["resolution"].split("x")]
                except Exception:
                    continue
                if not portrait_ok(w, h):
                    continue
                out.append({"src": "wallhaven", "full": it["path"],
                            "w": w, "h": h, "q": q})
            if len(data) < 24:
                break
        if len(out) >= MAX_PER_SERIES:
            break
    return out


def preview(path):
    r = get(path)
    im = Image.open(io.BytesIO(r.content))
    im.load()
    im = im.convert("RGB")
    im.thumbnail((360, 640), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=86)
    return buf.getvalue(), im.size


def make_sheets(slug, items):
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except Exception:
        font = ImageFont.load_default()
    cols, rows, cw, ch = 5, 2, 320, 569
    for n, start in enumerate(range(0, len(items), PER_SHEET)):
        chunk = items[start:start + PER_SHEET]
        sh = Image.new("RGB", (cols * cw, rows * ch), (18, 18, 20))
        dr = ImageDraw.Draw(sh)
        for k, it in enumerate(chunk):
            cx, cy = (k % cols) * cw, (k // cols) * ch
            try:
                im = Image.open(os.path.join(HERE, CAND, slug, "%d.jpg" % it["i"]))
                im = im.convert("RGB")
            except Exception:
                continue
            im.thumbnail((cw, ch), Image.LANCZOS)
            sh.paste(im, (cx + (cw - im.width) // 2, cy + (ch - im.height) // 2))
            dr.rectangle([cx + 4, cy + 4, cx + 78, cy + 46], fill=(0, 0, 0))
            dr.text((cx + 12, cy + 6), str(it["i"]), fill=(255, 255, 0), font=font)
            dr.rectangle([cx, cy, cx + cw - 1, cy + ch - 1], outline=(60, 60, 60))
        sh.save(os.path.join(HERE, SHEETS, "%s_%d.jpg" % (slug, n)),
                "JPEG", quality=86)


all_cand = {}
for s in SERIES:
    slug = s["slug"]
    os.makedirs(os.path.join(HERE, CAND, slug), exist_ok=True)
    pool = []
    for q in s["queries"]:
        found = wh_search(q, pages=2)
        pool += found
        print("  q=%-32s %d" % (q, len(found)))
        if len(pool) >= MAX_PER_SERIES * 3:
            break
    kept, i = [], 0
    for c in pool:
        if len(kept) >= MAX_PER_SERIES:
            break
        if c["full"] in SEEN:
            continue
        try:
            data, size = preview(c["full"])
        except Exception:
            continue
        hsh = hashlib.md5(data).hexdigest()
        if hsh in SEEN:
            continue
        SEEN.add(hsh)
        SEEN.add(c["full"])
        open(os.path.join(HERE, CAND, slug, "%d.jpg" % i), "wb").write(data)
        c["i"] = i
        c["pw"], c["ph"] = size
        kept.append(c)
        i += 1
    if kept:
        make_sheets(slug, kept)
    all_cand[slug] = kept
    print("%s: %d candidates" % (slug, len(kept)))
    time.sleep(1)

json.dump(all_cand, open(os.path.join(HERE, OUTJSON), "w"), indent=1)
print("TOTAL candidates:", sum(len(v) for v in all_cand.values()))
