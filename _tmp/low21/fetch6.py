#!/usr/bin/env python3
"""Low21 round 6: konachan + wallhaven for remaining series (danbooru is CF-blocked)."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# name, konachan tags, wallhaven query
SERIES = [
    ("hollow knight", ["hollow_knight", "hornet_(hollow_knight)"], "hollow knight"),
    ("rent a girlfriend", ["kanojo_okarishimasu", "mizuhara_chizuru"], "rent a girlfriend"),
    ("horimiya", ["horimiya", "hori_kyouko"], "horimiya"),
    ("mashle", ["mashle", "mash_burnedead"], "mashle"),
    ("mob psycho 100", ["mob_psycho_100", "kageyama_shigeo"], "mob psycho"),
    ("dr stone", ["dr_stone", "ishigami_senku"], "dr stone"),
    ("made in abyss", ["made_in_abyss"], "made in abyss"),
    ("digimon", ["digimon", "omegamon", "wargreymon"], "digimon"),
    ("no game no life", ["no_game_no_life"], "no game no life"),
    ("kuroko no basket", ["kuroko_no_basket"], "kuroko no basket"),
]

BADTAGS = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic",
           "4koma", "multiple_views", "character_sheet", "translated", "logo", "border", "frame",
           "letterboxed", "twitter_username", "web_address", "dated", "artist_logo", "bad_id",
           "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan",
           "sample", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties",
           "bra", "cleavage", "no_bra", "see_through", "nude", "naked", "topless", "bed", "bottomless",
           "photo", "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
           "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
           "vector", "lineart", "line_art", "blood", "gore", "guro", "game_cg", "cgi", "redraw",
           "loli", "child", "close-up", "eyes", "pantyhose", "spread_legs", "ass", "large_breasts",
           "huge_breasts", "sideboob", "underboob", "wet", "meme", "parody", "pixel_art", "3d",
           "map", "diagram", "chart", "poster", "cover", "wallpaper_(medium)"}

OUT = "_tmp/low21"
PREV = os.path.join(OUT, "prev6")
SHEETS = os.path.join(OUT, "sheets6")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 18


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


def get(url, params=None, referer=None, tries=2, timeout=35):
    hdr = dict(UA)
    if referer:
        hdr["Referer"] = referer
    for a in range(tries):
        try:
            r = requests.get(url, params=params, headers=hdr, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.5)
                return r
            print("  HTTP", r.status_code, url.split("?")[0], flush=True)
            if r.status_code in (429, 503):
                time.sleep(8 + 4 * a)
        except Exception as e:
            print("  ERR", type(e).__name__, url.split("?")[0], flush=True)
        time.sleep(2)
    return None


def konachan(tag):
    out = []
    for page in (1, 2):
        r = get("https://konachan.net/post.json", {"tags": tag + " rating:s", "limit": 100, "page": page},
                referer="https://konachan.net/")
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site="k", id="k" + str(p.get("id")), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0, url=p.get("file_url"),
                            prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                            tags=p.get("tags") or "", rating=p.get("rating")))
        if len(js) < 100:
            break
    return out


def wallhaven(q):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "sorting": "favorites",
                 "atleast": "900x1300", "page": page}, referer="https://wallhaven.cc/")
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        data = js.get("data") if isinstance(js, dict) else None
        if not data:
            break
        for p in data:
            tags = " ".join(t.get("name", "").replace(" ", "_") for t in (p.get("tags") or []))
            out.append(dict(site="w", id="w" + str(p.get("id")), score=int(p.get("favorites") or 0),
                            w=p.get("dimension_x") or 0, h=p.get("dimension_y") or 0,
                            url=p.get("path"), prev=(p.get("thumbs") or {}).get("large") or p.get("path"),
                            tags=tags, rating="s"))
        if len(data) < 24:
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
print("used pids", len(used), flush=True)

cands = []
for name, ktags, wq in SERIES:
    pool, seen = [], set()
    for t in ktags:
        got = konachan(t)
        print("  %s k %r -> %d" % (name, t, len(got)), flush=True)
        for p in got:
            if p["id"] not in seen:
                seen.add(p["id"]); pool.append(p)
    got = wallhaven(wq)
    print("  %s wallhaven %r -> %d" % (name, wq, len(got)), flush=True)
    for p in got:
        if p["id"] not in seen:
            seen.add(p["id"]); pool.append(p)
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    kept = []
    for p in pool:
        if p["id"] in used:
            continue
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1150 or w < 550:
                continue
        elif r <= 0.8:
            if w < 1700:
                continue
        else:
            continue
        if set(p["tags"].split()) & BADTAGS:
            continue
        kept.append(p)
    kept.sort(key=lambda p: (0 if (p["h"] / p["w"]) >= 1.2 else 1, -(p["score"] or 0)))
    print("   valid=%d portrait=%d" % (len(kept), sum(1 for p in kept if p["h"] / p["w"] >= 1.2)), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        ok, im = False, None
        ref = {"k": "https://konachan.net/", "w": "https://wallhaven.cc/"}[p["site"]]
        for a in range(2):
            try:
                hdr = dict(UA); hdr["Referer"] = ref
                r = requests.get(p["prev"], headers=hdr, timeout=40)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
                ok = True
                break
            except Exception as e:
                print("   dl err", p["id"], type(e).__name__, flush=True)
                time.sleep(2)
        if not ok:
            continue
        fn = "%s_%02d.jpg" % (slug, n)
        render(im).save(os.path.join(PREV, fn), "JPEG", quality=82, optimize=True)
        cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=p["id"], site=p["site"],
                          score=p["score"], w=p["w"], h=p["h"], url=p["url"], prev=p["prev"], tags=p["tags"][:500]))
        n += 1
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands6.json"), "w"), indent=1)

COLS, ROWS = 5, 4
CW, CH = 240, 427
by = {}
for c in cands:
    by.setdefault(c["slug"], []).append(c)
for slug, items in by.items():
    for si in range(0, len(items), COLS * ROWS):
        chunk = items[si:si + COLS * ROWS]
        sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for k, c in enumerate(chunk):
            im = Image.open(os.path.join(PREV, c["file"])).convert("RGB").resize((CW, CH), Image.LANCZOS)
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 30, y + 18], fill=(0, 0, 0))
            dr.text((x + 4, y + 4), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // COLS * ROWS)), "JPEG", quality=88, optimize=True)
print("TOTAL", len(cands), flush=True)
