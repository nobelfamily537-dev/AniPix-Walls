#!/usr/bin/env python3
"""Fetch candidate wallpapers for low-count series from wallhaven / konachan / danbooru.

Writes:
  _tmp/cand/<slug>/<i>.jpg        preview images
  _tmp/sheets/<slug>.jpg          contact sheet (8 per sheet, 4x2, index labels)
  _tmp/candidates.json            per series: index -> {src, full, w, h, extra}
"""
import io, json, os, time, hashlib
import requests
from PIL import Image, ImageDraw, ImageFont

UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}
HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = json.load(open(os.path.join(HERE, "series.json"), encoding="utf-8"))
os.makedirs(os.path.join(HERE, "cand"), exist_ok=True)
os.makedirs(os.path.join(HERE, "sheets"), exist_ok=True)

MAX_PER_SERIES = 24
SEEN = set()


def get(url, **kw):
    kw.setdefault("timeout", 45)
    kw.setdefault("headers", UA)
    r = requests.get(url, **kw)
    r.raise_for_status()
    return r


def portrait_ok(w, h):
    return w >= 1000 and h >= 1600 and h / float(w) >= 1.25


def wh_search(q):
    out = []
    try:
        u = ("https://wallhaven.cc/api/v1/search"
             "&ratios=portrait&atleast=1080x1920&sorting=relevance&page=1"
             % requests.utils.quote(q))
        js = get(u).json()
        for it in js.get("data", []):
            try:
                w, h = [int(x) for x in it["resolution"].split("x")]
            except Exception:
                continue
            if not portrait_ok(w, h):
                continue
            out.append({"src": "wallhaven", "full": it["path"],
                        "prev": it["thumbs"]["large"], "w": w, "h": h,
                        "extra": it.get("id", "")})
    except Exception as e:
        print(f"  wallhaven FAIL {q}: {e}")
    return out


def kc_search(tag):
    out = []
    try:
        u = ("https://konachan.net/post.json"
             % requests.utils.quote(tag))
        for it in get(u).json():
            w, h = it.get("width") or 0, it.get("height") or 0
            if not portrait_ok(w, h):
                continue
            prev = it.get("sample_url") or it.get("jpeg_url") or it.get("file_url")
            if not prev or not it.get("file_url"):
                continue
            out.append({"src": "konachan", "full": it["file_url"], "prev": prev,
                        "w": w, "h": h, "extra": it.get("tags", "")[:120]})
    except Exception as e:
        print(f"  konachan FAIL {tag}: {e}")
    return out


def db_search(tag):
    out = []
    try:
        u = ("https://danbooru.donmai.us/posts.json"
             "&limit=100" % requests.utils.quote(tag))
        for it in get(u).json():
            w, h = it.get("image_width") or 0, it.get("image_height") or 0
            if not portrait_ok(w, h):
                continue
            full = it.get("file_url")
            prev = it.get("large_file_url") or full
            if not full or not prev:
                continue
            out.append({"src": "danbooru", "full": full, "prev": prev,
                        "w": w, "h": h,
                        "extra": (it.get("tag_string_character") or "")[:120]})
    except Exception as e:
        print(f"  danbooru FAIL {tag}: {e}")
    return out


def sheet(slug, items):
    cols, rows, cw, ch = 4, 2, 400, 711
    sh = Image.new("RGB", (cols * cw, rows * ch), (18, 18, 20))
    dr = ImageDraw.Draw(sh)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except Exception:
        font = ImageFont.load_default()
    for k, it in enumerate(items):
        cx, cy = (k % cols) * cw, (k // cols) * ch
        try:
            im = Image.open(os.path.join(HERE, "cand", slug, "%d.jpg" % it["i"])).convert("RGB")
        except Exception:
            continue
        im.thumbnail((cw, ch), Image.LANCZOS)
        sh.paste(im, (cx + (cw - im.width) // 2, cy + (ch - im.height) // 2))
        dr.rectangle([cx + 4, cy + 4, cx + 76, cy + 48], fill=(0, 0, 0))
        dr.text((cx + 12, cy + 8), str(it["i"]), fill=(255, 255, 0), font=font)
        dr.rectangle([cx, cy, cx + cw - 1, cy + ch - 1], outline=(60, 60, 60))
    sh.save(os.path.join(HERE, "sheets", slug + ".jpg"), "JPEG", quality=88)


all_cand = {}
for s in SERIES:
    slug = s["slug"]
    os.makedirs(os.path.join(HERE, "cand", slug), exist_ok=True)
    pool = []
    for q in s.get("wh", []):
        pool += wh_search(q)
    for t in s.get("kc", []):
        pool += kc_search(t)
    for t in s.get("db", []):
        pool += db_search(t)
    # interleave sources so the first picks are not all from one site
    bysrc = {}
    for c in pool:
        bysrc.setdefault(c["src"], []).append(c)
    mixed = []
    for i in range(max([len(v) for v in bysrc.values()] or [0])):
        for src in ("wallhaven", "konachan", "danbooru"):
            v = bysrc.get(src, [])
            if i < len(v):
                mixed.append(v[i])
    kept, i = [], 0
    for c in mixed:
        if len(kept) >= MAX_PER_SERIES:
            break
        if c["full"] in SEEN:
            continue
        try:
            r = get(c["prev"])
        except Exception:
            continue
        hsh = hashlib.md5(r.content).hexdigest()
        if hsh in SEEN:
            continue
        SEEN.add(hsh)
        SEEN.add(c["full"])
        p = os.path.join(HERE, "cand", slug, "%d.jpg" % i)
        open(p, "wb").write(r.content)
        try:
            Image.open(p).verify()
        except Exception:
            os.remove(p)
            continue
        c["i"] = i
        kept.append(c)
        i += 1
    if kept:
        sheet(slug, kept)
    all_cand[slug] = [{k: v for k, v in c.items() if k != "prev"} for c in kept]
    print(f"{slug}: {len(kept)} candidates "
          f"({ {s2: sum(1 for c in kept if c['src'] == s2) for s2 in ('wallhaven','konachan','danbooru')} })")
    time.sleep(1)

json.dump(all_cand, open(os.path.join(HERE, "candidates.json"), "w"), indent=1)
print("TOTAL candidates:", sum(len(v) for v in all_cand.values()))
