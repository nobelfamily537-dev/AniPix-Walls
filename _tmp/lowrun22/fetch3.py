#!/usr/bin/env python3
"""Low-count run 22 - stage 1c: wallhaven + safebooru candidates, 9:16 previews."""
import os, io, json, time, re
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}
OUT = "_tmp/lowrun22/preview"
os.makedirs(OUT, exist_ok=True)
picks = json.load(open("_tmp/lowrun22/picks.json"))
excl = set(json.load(open("_tmp/lowrun22/exclude.json")))
cands = json.load(open("_tmp/lowrun22/cands.json")) if os.path.exists("_tmp/lowrun22/cands.json") else []
have = {(c["site"], str(c["pid"])) for c in cands}

BADW = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
 "multiple_views","character_sheet","translated","logo","border","frame","letterboxed","twitter_username",
 "web_address","dated","artist_logo","english_commentary","bad_id","sketch","monochrome","greyscale",
 "partially_colored","censored","manga","scan","sample","food","chibi","comic_panel","bikini","swimsuit",
 "underwear","lingerie","panties","bra","cleavage","no_bra","see_through","spread_legs","large_breasts",
 "huge_breasts","ass","nude","naked","topless","wet","bed","bottomless","sideboob","underboob","photo",
 "photograph","cosplay","screencap","screenshot","reference_sheet","upscaled","jpeg_artifacts","lowres",
 "real_world_location","photo_background","collage","crossover","vector","lineart","line_art","3d",
 "realistic","ai-generated","ai_generated","tracing","poster","calendar","cover","magazine","doujin"}


def render(im, size=(420, 746)):
    w, h = im.size
    t = size[1] / size[0]
    if h / w > t:
        nw = int(h / t); x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:
        nh = int(w * t); y = int((h - nh) * 0.45)
        im = im.crop((0, y, w, y + nh))
    return im.resize(size, Image.LANCZOS)


def ok_dim(w, h):
    if not w or not h:
        return False
    if w < 950 or h < 1700:
        return False
    r = w / h
    return 0.45 <= r <= 0.72 or (r < 0.45 and w >= 900)


def wh_search(q, pages=2):
    out = []
    for page in range(1, pages + 1):
        try:
            r = requests.get("https://wallhaven.cc/api/v1/search",
                             params={"q": q, "categories": "010", "purity": "100",
                                     "sorting": "favorites", "order": "desc", "page": page},
                             headers=UA, timeout=30)
            if r.status_code != 200:
                print("  wh HTTP", r.status_code, q, flush=True); break
            js = r.json()
        except Exception as e:
            print("  wh ERR", type(e).__name__, q, flush=True); break
        d = js.get("data", [])
        for it in d:
            out.append(dict(site="wh", id=it["id"], score=it.get("favorites", 0),
                            w=it["dimension_x"], h=it["dimension_y"], url=it["path"],
                            prev=it["path"],
                            tags=" ".join(t["name"].replace(" ", "_") for t in it.get("tags", []))[:600]))
        if len(d) < 24:
            break
        time.sleep(0.8)
    return out


def sb_search(tag, pages=3):
    out = []
    for page in range(0, pages):
        try:
            r = requests.get("https://safebooru.org/index.php",
                             params={"page": "dapi", "s": "post", "q": "index", "json": "1",
                                     "limit": 100, "pid": page, "tags": tag},
                             headers=UA, timeout=40)
            if r.status_code != 200:
                print("  sb HTTP", r.status_code, tag, flush=True); break
            js = r.json()
        except Exception as e:
            print("  sb ERR", type(e).__name__, tag, flush=True); break
        if not js:
            break
        for p in js:
            out.append(dict(site="sb", id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width") or 0, h=p.get("height") or 0,
                            url=p.get("file_url"), prev=p.get("sample_url") or p.get("file_url"),
                            tags=p.get("tags") or ""))
        time.sleep(1.0)
    return out


for pk in picks:
    name, slug = pk["series"], pk["slug"]
    pool = wh_search(pk["booru"][0])
    n_wh = len(pool)
    for t in pk["booru"]:
        pool += sb_search(t.replace(" ", "_"))
    print("== %s wh=%d pool=%d" % (name, n_wh, len(pool)), flush=True)

    seen, kept = set(), []
    for p in sorted(pool, key=lambda p: -(p["score"] or 0)):
        key = (p["site"], str(p["id"]))
        if key in seen or key in have:
            continue
        seen.add(key)
        if p["site"] == "wh" and p["id"] in excl:
            continue
        if not ok_dim(p["w"], p["h"]):
            continue
        if p["site"] == "sb" and set(p["tags"].split()) & BADW:
            continue
        kept.append(p)
    print("   valid=%d" % len(kept), flush=True)

    n = 0
    for p in kept:
        if n >= 16:
            break
        try:
            r = requests.get(p["prev"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = "%s_x%02d.jpg" % (slug, n)
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, file=fn, pid=p["id"], site=p["site"], score=p["score"],
                              w=p["w"], h=p["h"], url=p["url"], tags=p["tags"][:600]))
            have.add((p["site"], str(p["id"])))
            n += 1
        except Exception as e:
            print("   dl err", p["id"], type(e).__name__, flush=True)
        time.sleep(0.2)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open("_tmp/lowrun22/cands.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
