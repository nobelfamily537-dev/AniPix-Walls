#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-15) stage 1: fetch candidates + contact sheets."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
      "Referer": "https://konachan.net/"}

# (display name, konachan tags, tags to un-blacklist)
SERIES = [
    ("nanatsu no taizai", ["nanatsu_no_taizai"], set()),
    ("kaiju no 8", ["kaijuu_8_gou", "kaiju_no._8", "kaiju_no_8"], set()),
    ("saga of tanya the evil", ["youjo_senki"], set()),
    ("girls band cry", ["girls_band_cry"], set()),
    ("soul eater", ["soul_eater"], set()),
    ("berserk", ["berserk"], set()),
    ("dungeon meshi", ["dungeon_meshi"], set()),
    ("hunter x hunter", ["hunter_x_hunter"], set()),
    ("fate/stay night", ["fate/stay_night"], set()),
    ("wind breaker", ["wind_breaker"], set()),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "food", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "blood", "gore", "guro", "comic_panel", "game_cg", "cgi",
       "anime_screencap", "screen_capture", "redraw"}

OUT = "_tmp/lowrun15"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)

PER_SERIES = 26


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


def get(url, params, timeout=30):
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(1.0)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


def fetch_site(base, tag):
    out = []
    for page in (1, 2):
        r = get(base, {"tags": tag + " rating:s", "limit": 100, "page": page})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site=base, id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"), prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


# pids already used by earlier runs
used = set()
for fn in os.listdir("_tmp"):
    if fn.endswith(".json"):
        try:
            js = json.load(open(os.path.join("_tmp", fn)))
        except Exception:
            continue
        if isinstance(js, list):
            for e in js:
                if isinstance(e, dict) and "pid" in e:
                    used.add(e["pid"])
print("already-used pids:", len(used), flush=True)

cands = []
for name, tags, ignore in SERIES:
    bad = BAD - ignore
    pool = []
    for t in tags:
        got = fetch_site("https://konachan.net/post.json", t)
        print("  %s tag %s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 120:
            break
    if len(pool) < 40:
        for t in tags:
            pool += fetch_site("https://yande.re/post.json", t)
    print("== %s: pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen or p["id"] in used:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1300 or w < 700:
                continue
        elif r <= 0.8:
            if w < 1800:
                continue
        else:
            continue
        if set(p["tags"].split()) & bad:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=40)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.25)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands.json"), "w"), indent=1)

# contact sheets: 5 cols x 4 rows, cell 240x427, label top-left
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
print("sheets:", len(os.listdir(SHEETS)), flush=True)
