#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-15) stage 1b: wallhaven + danbooru candidates."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

SERIES = [
    ("nanatsu no taizai", ["seven deadly sins", "nanatsu no taizai", "the seven deadly sins"], ["nanatsu_no_taizai"]),
    ("kaiju no 8", ["kaiju no. 8", "kaiju no 8", "kaijuu 8 gou"], ["kaijuu_8_gou", "kaiju_no._8"]),
    ("saga of tanya the evil", ["tanya the evil", "youjo senki"], ["youjo_senki"]),
    ("girls band cry", ["girls band cry", "togenashi togeari"], ["girls_band_cry"]),
    ("soul eater", ["soul eater"], ["soul_eater"]),
    ("berserk", ["berserk", "guts berserk"], ["berserk"]),
    ("dungeon meshi", ["dungeon meshi", "delicious in dungeon", "laios"], ["dungeon_meshi"]),
    ("hunter x hunter", ["hunter x hunter", "killua", "gon freecss"], ["hunter_x_hunter"]),
    ("fate/stay night", ["fate stay night", "saber fate", "rin tohsaka"], ["fate/stay_night", "fate_(series)"]),
    ("wind breaker", ["wind breaker", "sakura haruka", "bofurin"], ["wind_breaker"]),
]

BAD_WORDS = {"text", "watermark", "signature", "logo", "sketch", "monochrome", "greyscale", "grayscale",
             "comic", "manga", "4koma", "chibi", "lineart", "line art", "screencap", "screenshot",
             "cosplay", "photo", "photograph", "vector", "minimal", "quote", "quotes", "typography",
             "collage", "crossover", "food", "meme", "pixel art", "8bit"}

OUT = "_tmp/lowrun15"
PREV = os.path.join(OUT, "prev2")
SHEETS = os.path.join(OUT, "sheets2")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 30


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
    nw = int(h * t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params=None, timeout=30, tries=2):
    for _ in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r
            print("  HTTP", r.status_code, url, flush=True)
            if r.status_code == 429:
                time.sleep(10)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(2)
    return None


def wallhaven(q):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "purity": "100", "categories": "010", "sorting": "toplist",
                 "order": "desc", "page": page, "atleast": "1200x1200"})
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        data = js.get("data") or []
        for p in data:
            out.append(dict(site="wallhaven", id=p.get("id"), score=p.get("favorites") or 0,
                            w=p.get("dimension_x") or 0, h=p.get("dimension_y") or 0,
                            url=p.get("path"), prev=p.get("thumbs", {}).get("original") or p.get("path"),
                            tags=" ".join(t.get("name", "") for t in (p.get("tags") or [])),
                            rating="s", views=p.get("views") or 0))
        if len(data) < 24:
            break
        time.sleep(1.2)
    return out


def danbooru(tag):
    out = []
    r = get("https://danbooru.donmai.us/posts.json",
            {"tags": tag + " rating:g highres", "limit": 100, "only": "id,score,image_width,image_height,file_url,large_file_url,tag_string_general,tag_string_character,tag_string_copyright"})
    if not r:
        return out
    try:
        js = r.json()
    except Exception:
        return out
    for p in js if isinstance(js, list) else []:
        out.append(dict(site="danbooru", id=p.get("id"), score=p.get("score") or 0,
                        w=p.get("image_width") or 0, h=p.get("image_height") or 0,
                        url=p.get("file_url"), prev=p.get("large_file_url") or p.get("file_url"),
                        tags=" ".join(x for x in [p.get("tag_string_general", ""),
                                                  p.get("tag_string_character", ""),
                                                  p.get("tag_string_copyright", "")] if x),
                        rating="s"))
    return out


cands = []
for name, wq, dq in SERIES:
    pool = []
    for q in wq:
        got = wallhaven(q)
        print("  %s | wallhaven '%s' -> %d" % (name, q, len(got)), flush=True)
        pool += got
        if len(pool) >= 90:
            break
    if len(pool) < 30:
        for t in dq:
            got = danbooru(t)
            print("  %s | danbooru '%s' -> %d" % (name, t, len(got)), flush=True)
            pool += got
            if len(pool) >= 90:
                break
    print("== %s pool=%d" % (name, len(pool)), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url"):
            continue
        r = h / w
        if r >= 1.15:
            if h < 1300 or w < 700:
                continue
        elif r <= 0.85:
            if w < 2200:
                continue
        else:
            continue
        tl = (p.get("tags") or "").lower()
        if any(b in tl for b in BAD_WORDS):
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if min(im.size) < 500:
                continue
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=82, optimize=True)
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid="%s:%s" % (p["site"], p["id"]),
                              site=p["site"], score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"][:400]))
            n += 1
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.15)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands2.json"), "w"), indent=1)

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
