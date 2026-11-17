#!/usr/bin/env python3
"""Night gap-fill run (2026-11-17 21:00 IST): candidates for series with ZERO coverage.
Sources: yande.re (Pixiv art, portrait-rich) + konachan.net. Portrait posts preferred."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

# name, extra tag queries, konachan/yande primary tag
SERIES = [
    ("kuroko no basket", ["kuroko_no_basket", "kagami_taiga", "aomine_daiki", "kise_ryouta",
                          "akashi_seijuurou", "midorima_shintarou", "murasakibara_atsushi"]),
    ("blue exorcist", ["ao_no_exorcist", "okumura_rin", "okumura_yukio"]),
    ("fruits basket", ["fruits_basket", "honda_tohru", "sohma_kyo", "sohma_yuki"]),
    ("samurai champloo", ["samurai_champloo", "mugen_(samurai_champloo)", "jin_(samurai_champloo)",
                          "fuu_(samurai_champloo)"]),
    ("no game no life", ["no_game_no_life", "shiro_(no_game_no_life)", "sora_(no_game_no_life)", "jibril"]),
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
           "huge_breasts", "sideboob", "underboob", "wet"}

OUT = "_tmp/night19"
PREV = os.path.join(OUT, "prev")
SHEETS = os.path.join(OUT, "sheets")
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


def get(url, params=None, timeout=30, tries=3, referer="https://yande.re/"):
    hdr = dict(UA)
    hdr["Referer"] = referer
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=hdr, timeout=timeout)
            if r.status_code == 200:
                time.sleep(0.6)
                return r
            print("  HTTP", r.status_code, url, flush=True)
            if r.status_code in (403, 429, 503):
                time.sleep(10 + 5 * attempt)
                continue
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(2)
    return None


def board_search(base, tag, site):
    ref = base.split("/post.json")[0] + "/"
    out = []
    for page in (1, 2):
        r = get(base, {"tags": tag + " rating:s", "limit": 100, "page": page}, referer=ref)
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        if not isinstance(js, list) or not js:
            break
        for p in js:
            out.append(dict(site=site, id=site[:2] + str(p.get("id")), score=p.get("score") or 0,
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
for name, queries in SERIES:
    pool, seen = [], set()
    for t in queries:
        got = board_search("https://yande.re/post.json", t, "yande")
        print("  %s yande %r -> %d" % (name, t, len(got)), flush=True)
        for p in got:
            if p["id"] not in seen:
                seen.add(p["id"])
                pool.append(p)
    if len(pool) < 40:
        for t in queries:
            got = board_search("https://konachan.net/post.json", t, "konachan")
            print("  %s konachan %r -> %d" % (name, t, len(got)), flush=True)
            for p in got:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    pool.append(p)
    print("== %s: pool=%d" % (name, len(pool)), flush=True)

    kept = []
    for p in pool:
        if p["id"] in used:
            continue
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.2:
            if h < 1300 or w < 650:
                continue
        elif r <= 0.8:
            if w < 1900:
                continue
        else:
            continue
        if set(p["tags"].split()) & BADTAGS:
            continue
        if p.get("rating") not in ("s", None):
            continue
        kept.append(p)
    kept.sort(key=lambda p: (0 if (p["h"] / p["w"]) >= 1.2 else 1, -(p["score"] or 0)))
    print("   valid=%d (portrait=%d)" % (len(kept), sum(1 for p in kept if p["h"] / p["w"] >= 1.2)), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for p in kept:
        if n >= PER_SERIES:
            break
        ok, im = False, None
        ref = "https://yande.re/" if p["site"] == "yande" else "https://konachan.net/"
        for attempt in range(2):
            try:
                hdr = dict(UA)
                hdr["Referer"] = ref
                r = requests.get(p["prev"], headers=hdr, timeout=40)
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
                          score=p["score"], w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:400]))
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
