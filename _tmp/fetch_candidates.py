#!/usr/bin/env python3
"""Stage 1: gather candidates from wallhaven / yande.re / safebooru.org, save 9:16 previews."""
import os, io, json, time, re
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SERIES = [
    ("nisekoi", "nisekoi", ["kirisaki_chitoge","onodera_kosaki","tachibana_marika","tsugumi_seishirou"]),
    ("tokyo revengers", "tokyo revengers", ["sano_manjirou","hanagaki_takemichi","baji_keisuke","matsuno_chifuyu","hanemiya_kazutora"]),
    ("seraph of the end", "seraph of the end", ["owari_no_seraph","hyakuya_mikaela","hyakuya_yuuichirou","shinoa_hiragi"]),
    ("heavenly delusion", "heavenly delusion", ["tengoku_daimakyou","kiruko","maru_(tengoku_daimakyou)"]),
    ("wind breaker", "wind breaker", ["wind_breaker","sakura_haruka","suo_hayato","umemiya_hajime"]),
    ("makeine", "makeine", ["makeine","make_heroine_ga_oosugiru","yanami_anna"]),
    ("girls band cry", "girls band cry", ["girls_band_cry","iseri_nina","kawaragi_momoka","awa_subaru"]),
    ("yuru camp", "yuru camp", ["yuru_camp","kagamihara_nadeshiko","shima_rin"]),
    ("blue archive", "blue archive", ["blue_archive","shiroko_(blue_archive)","arona_(blue_archive)","hina_(blue_archive)","mika_(blue_archive)"]),
    ("arknights", "arknights", ["arknights","amiya_(arknights)","surtr_(arknights)","skadi_(arknights)","texas_(arknights)"]),
]
BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
       "multiple_views","character_sheet","translated","logo","border","frame","letterboxed",
       "twitter_username","web_address","dated","artist_logo","english_commentary","bad_id",
       "bad_pixiv_id","bad_twitter_id","official_art","sketch","monochrome","greyscale",
       "partially_colored","gun","mecha","vehicle","blood","gore","censored","manga","scan","sample",
       "back","no_humans","food","chibi","comic_panel"}
OUT = "_tmp/prev"
os.makedirs(OUT, exist_ok=True)
cands = []

def get(url, params=None, tries=2, sleep=1.0):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                time.sleep(sleep)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(3)
    return None

def wallhaven(q):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "ratios": "9x16",
                 "atleast": "1080x1920", "sorting": "favorites", "page": page})
        if not r: break
        try: js = r.json()
        except Exception: break
        for d in js.get("data", []):
            out.append(dict(src="wallhaven", id=d["id"], score=d.get("favorites") or 0,
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                            prev=(d.get("thumbs") or {}).get("large") or d["path"],
                            md5=d["id"], tags=" ".join(t["name"] for t in d.get("tags", [])),
                            rating="s"))
        if not js.get("meta", {}).get("current_page", 1) < js.get("meta", {}).get("last_page", 1):
            break
    return out

def yande(tag):
    out = []
    r = get("https://yande.re/post.json", {"tags": tag + " rating:safe", "limit": 100})
    if not r: return []
    try: arr = r.json()
    except Exception: return []
    for p in arr:
        out.append(dict(src="yande", id=p.get("id"), score=p.get("score") or 0,
                        w=p.get("width"), h=p.get("height"),
                        url=p.get("file_url") or p.get("jpeg_url"),
                        prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                        md5=p.get("md5"), tags=p.get("tags", "").replace("_", " "), rating=p.get("rating")))
    return out

def safebooru_org(tag):
    out = []
    for pid in (0, 1):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "tags": tag,
                 "json": "1", "limit": 100, "pid": pid})
        if not r: break
        try: arr = r.json()
        except Exception: break
        if not isinstance(arr, list): break
        for p in arr:
            d = p.get("directory"); im = p.get("image")
            if not im: continue
            out.append(dict(src="safebooruorg", id=p.get("id"), score=p.get("score") or 0,
                            w=p.get("width"), h=p.get("height"),
                            url=f"https://safebooru.org/images/{d}/{im}",
                            prev=f"https://safebooru.org/images/{d}/{im}",
                            md5=p.get("hash") or f"{d}/{im}", tags=p.get("tags", "").replace("_", " "),
                            rating="s"))
    return out

def ok(p, ms):
    if not p["url"] or not p["w"] or not p["h"]: return False
    if p["h"] < 1500 or p["w"] < 800: return False
    if p["h"] / p["w"] < 1.30: return False
    if p["score"] < ms: return False
    if set(p["tags"].split()) & BAD: return False
    return True

for name, wq, ytags in SERIES:
    pool = wallhaven(wq)
    print(f"== {name}: wallhaven={len(pool)}", flush=True)
    for t in ytags:
        pool += yande(t)
    print(f"   + yande total={len(pool)}", flush=True)
    if len([p for p in pool if ok(p, 3)]) < 30:
        for t in ytags:
            pool += safebooru_org(t)
        print(f"   + safebooru.org total={len(pool)}", flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        key = p["md5"] or p["url"]
        if key in seen: continue
        seen.add(key)
        ms = 3 if p["src"] == "wallhaven" else (12 if p["src"] == "yande" else 6)
        if ok(p, ms): kept.append(p)
    kept = kept[:26]
    print(f"   kept {len(kept)}", flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name)
    for i, p in enumerate(kept):
        try:
            r = requests.get(p.get("prev") or p["url"], headers=UA, timeout=120)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            w, h = im.size; t = 9/16
            if w/h > t:
                nw = int(h*t); x = (w-nw)//2; im = im.crop((x, 0, x+nw, h))
            else:
                nh = int(w/t); y = int((h-nh)*0.22); im = im.crop((0, y, w, y+nh))
            im = im.resize((450, 800), Image.LANCZOS)
            fn = f"{slug}_{i:02d}.jpg"
            im.save(f"{OUT}/{fn}", "JPEG", quality=80, optimize=True)
            cands.append(dict(series=name, file=fn, src=p["src"], pid=p["id"], score=p["score"],
                              w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
        except Exception as e:
            print("   dl err", p.get("id"), e, flush=True)
        time.sleep(0.25)

json.dump(cands, open("_tmp/candidates.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
