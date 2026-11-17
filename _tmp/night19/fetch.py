#!/usr/bin/env python3
"""Night gap-fill run (2026-11-17 21:00 IST): portrait candidates for series with ZERO coverage.
Primary source: wallhaven.cc API (9:16 phone wallpapers, SFW) with per-image TAG VERIFICATION
so every image really belongs to the series. Fallback: konachan.net (portrait posts only)."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

# name, wallhaven search queries, accepted tag names (lowercase) for verification, konachan tag
SERIES = [
    ("kuroko no basket", ["kuroko no basket", "kuroko"], ["kuroko no basket", "kuroko no basuke"], "kuroko_no_basket"),
    ("blue exorcist", ["blue exorcist", "ao no exorcist"], ["blue exorcist", "ao no exorcist"], "ao_no_exorcist"),
    ("fruits basket", ["fruits basket"], ["fruits basket", "fruits basket (2019)"], "fruits_basket"),
    ("samurai champloo", ["samurai champloo", "champloo"], ["samurai champloo"], "samurai_champloo"),
    ("no game no life", ["no game no life"], ["no game no life"], "no_game_no_life"),
]

OUT = "_tmp/night19"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 16


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


def get(url, params=None, timeout=30, tries=3):
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.35)
                return r
            print("  HTTP", r.status_code, url, flush=True)
            if r.status_code in (403, 429, 503):
                time.sleep(10 + 5 * attempt)
                continue
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(2)
    return None


def wh_search(q):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "atleast": "1080x1920", "purity": "100", "categories": "010",
                 "sorting": "favorites", "order": "desc", "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        items = js.get("data") or []
        for p in items:
            out.append(dict(site="wallhaven", id="wh" + str(p.get("id")), score=p.get("favorites") or 0,
                            w=int(p.get("dimension_x") or 0), h=int(p.get("dimension_y") or 0),
                            url=p.get("path"), prev=(p.get("thumbs") or {}).get("large") or p.get("path"),
                            tags="", rating="s"))
        if len(items) < 24:
            break
    return out


def wh_tags(wid):
    r = get("https://wallhaven.cc/api/v1/w/" + wid.replace("wh", "", 1))
    if not r:
        return []
    try:
        js = r.json().get("data") or {}
    except Exception:
        return []
    return [str(t.get("name", "")).lower() for t in (js.get("tags") or [])]


def kc_search(tag):
    out = []
    for page in (1, 2):
        r = get("https://konachan.net/post.json", {"tags": tag + " rating:s", "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site="konachan", id="kc" + str(p.get("id")), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0, url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


used = set()
for root, _, files in os.walk("_tmp"):
    for fn in files:
        if not fn.endswith(".json"):
            continue
        try:
            js = json.load(open(os.path.join(root, fn)))
        except Exception:
            continue
        for e in (js if isinstance(js, list) else []):
            if isinstance(e, dict) and "pid" in e:
                used.add(e["pid"])
print("already-used pids:", len(used), flush=True)

cands = []
for name, queries, accepted, kctag in SERIES:
    pool, seen = [], set()
    for q in queries:
        got = wh_search(q)
        print("  %s wallhaven %r -> %d" % (name, q, len(got)), flush=True)
        for p in got:
            if p["id"] not in seen:
                seen.add(p["id"])
                pool.append(p)
    print("== %s: wallhaven pool=%d" % (name, len(pool)), flush=True)

    kept = []
    checked = 0
    for p in pool:
        if p["id"] in used:
            continue
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        if h / w < 1.35 or h < 1600:
            continue
        if checked >= 70:
            break
        checked += 1
        tg = wh_tags(p["id"])
        if not any(a in tg for a in accepted):
            continue
        p["wh_tags"] = tg[:12]
        kept.append(p)
    print("   verified=%d (checked %d)" % (len(kept), checked), flush=True)

    if len(kept) < 6:
        extra = kc_search(kctag)
        print("   konachan %s -> %d" % (kctag, len(extra)), flush=True)
        for p in extra:
            w, h = p["w"], p["h"]
            if not w or not h or not p.get("url"):
                continue
            if h / w < 1.35 or h < 1500:
                continue
            if set(p["tags"].split()) & {"text", "watermark", "signature", "artist_name", "logo",
                                         "english_text", "speech_bubble", "manga", "comic", "chibi"}:
                continue
            kept.append(p)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        ok = False
        im = None
        for attempt in range(2):
            try:
                r = requests.get(p["prev"], headers=UA, timeout=40)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
                ok = True
                break
            except Exception as e:
                print("   dl err", p.get("id"), type(e).__name__, flush=True)
                time.sleep(2)
        if not ok:
            continue
        fn = "%s_%02d.jpg" % (slug, n)
        render(im).save(os.path.join(PREV, fn), "JPEG", quality=82, optimize=True)
        cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                          score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                          tags=p["tags"][:400], wh_tags=p.get("wh_tags", [])))
        n += 1
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands.json"), "w"), indent=1)

COLS, ROWS = 5, 4
CW, CH = 240, 427
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
            dr.rectangle([x, y, x + 30, y + 18], fill=(0, 0, 0))
            dr.text((x + 4, y + 4), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // per)), "JPEG", quality=88, optimize=True)

print("TOTAL candidates", len(cands), flush=True)
print("sheets:", sorted(os.listdir(SHEETS)), flush=True)
