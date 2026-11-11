#!/usr/bin/env python3
"""Stage 1: gather candidate art per series from booru APIs, save small 9:16 previews."""
import os, io, json, time, re
import requests
from PIL import Image

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
SERIES = [
    ("nisekoi", ["nisekoi"], ["kirisaki_chitoge", "onodera_kosaki", "tsugumi_seishirou", "ichijou_raku"]),
    ("tokyo revengers", ["tokyo_revengers"], ["sano_manjirou", "hanagaki_takemichi", "baji_keisuke", "matsuno_chifuyu", "hanemiya_kazutora", "ryuuguji_ken"]),
    ("seraph of the end", ["owari_no_seraph", "seraph_of_the_end"], ["hyakuya_mikaela", "hyakuya_yuuichirou", "shinoa_hiragi", "krul_tepes"]),
    ("heavenly delusion", ["tengoku_daimakyou"], ["kiruko_(tengoku_daimakyou)", "maru_(tengoku_daimakyou)"]),
    ("wind breaker", ["wind_breaker"], ["sakura_haruka", "suo_hayato", "nirei_akihiko", "umemiya_hajime"]),
    ("makeine", ["makeine", "make_heroine_ga_oosugiru!"], ["yanami_anna", "nukumizu_kazuhiko", "komari_chika", "shikiya_yoshimi"]),
    ("girls band cry", ["girls_band_cry"], ["iseri_nina", "kawaragi_momoka", "awa_subaru", "ebizuka_tomo", "rupa_(girls_band_cry)"]),
    ("yuru camp", ["yuru_camp"], ["kagamihara_nadeshiko", "shima_rin", "oogaki_chiaki", "inaoka_aoi"]),
    ("blue archive", ["blue_archive"], ["shiroko_(blue_archive)", "arona_(blue_archive)", "hina_(blue_archive)", "aru_(blue_archive)", "yuuka_(blue_archive)", "mika_(blue_archive)"]),
    ("arknights", ["arknights"], ["amiya_(arknights)", "surtr_(arknights)", "skadi_(arknights)", "texas_(arknights)", "chen_(arknights)", "nearl_(arknights)"]),
]
BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic",
       "4koma","multiple_views","character_sheet","translated","logo","border","frame",
       "letterboxed","twitter_username","web_address","dated","artist_logo","english_commentary",
       "bad_id","bad_pixiv_id","bad_twitter_id","official_art","sketch","monochrome","greyscale",
       "partially_colored","gun","mecha","vehicle","blood","gore","censored","absurdres_bad"}
OUT = "_tmp/prev"
os.makedirs(OUT, exist_ok=True)
cands = []

def get(url, params=None, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                return r
            print("HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("ERR", e, flush=True)
        time.sleep(3)
    return None

def resolve(tag):
    r = get("https://danbooru.donmai.us/tags.json",
            {"search[name_matches]": tag, "limit": 20})
    if not r: return None
    try: arr = r.json()
    except Exception: return None
    for t in arr:
        if t["name"] == tag: return tag
    for t in arr:
        if t["name"].startswith(tag): return t["name"]
    return None

def posts_danbooru(q):
    out = []
    for page in (1, 2):
        r = get("https://danbooru.donmai.us/posts.json",
                {"tags": q + " rating:g", "limit": 200, "page": page})
        if not r: break
        try: arr = r.json()
        except Exception: break
        if not arr: break
        for p in arr:
            out.append(dict(src="danbooru", id=p.get("id"), score=p.get("score", 0),
                            w=p.get("image_width"), h=p.get("image_height"),
                            url=p.get("file_url"), md5=p.get("md5"),
                            tags=p.get("tag_string", ""), rating=p.get("rating", "")))
        time.sleep(1)
    return out

def posts_safebooru(q):
    r = get("https://safebooru.donmai.us/posts.json", {"tags": q, "limit": 200})
    if not r: return []
    try: arr = r.json()
    except Exception: return []
    return [dict(src="safebooru", id=p.get("id"), score=p.get("score", 0),
                 w=p.get("image_width"), h=p.get("image_height"),
                 url=p.get("file_url"), md5=p.get("md5"),
                 tags=p.get("tag_string", ""), rating=p.get("rating", "")) for p in arr]

def posts_konachan(q):
    r = get("https://konachan.net/post.json", {"tags": q + " rating:safe", "limit": 100})
    if not r: return []
    try: arr = r.json()
    except Exception: return []
    return [dict(src="konachan", id=p.get("id"), score=p.get("score", 0),
                 w=p.get("width"), h=p.get("height"),
                 url=p.get("file_url"), md5=p.get("md5"),
                 tags=p.get("tags", ""), rating="s") for p in arr]

def ok(p, min_score):
    if not p["url"] or not p["w"] or not p["h"]: return False
    if p["h"] < 1500 or p["w"] < 800: return False
    if p["h"] / p["w"] < 1.30: return False
    if p["score"] < min_score: return False
    if set(p["tags"].split()) & BAD: return False
    return True

for name, copyrights, chars in SERIES:
    tags_found = []
    for g in copyrights:
        t = resolve(g)
        if t: tags_found.append(t)
    ch_found = []
    for c in chars:
        t = resolve(c)
        if t: ch_found.append(t)
    print(f"== {name}: copyright={tags_found} chars={ch_found}", flush=True)
    pool = []
    for t in tags_found:
        pool += posts_danbooru(t) + posts_safebooru(t) + posts_konachan(t)
    if len(pool) < 40:
        for t in ch_found:
            pool += posts_danbooru(t) + posts_safebooru(t)
    seen, kept = set(), []
    pool.sort(key=lambda p: -p["score"])
    for p in pool:
        if p["md5"] in seen: continue
        seen.add(p["md5"])
        ms = 25 if p["src"] == "danbooru" else (8 if p["src"] == "safebooru" else 10)
        if ok(p, ms): kept.append(p)
    kept = kept[:36]
    print(f"   kept {len(kept)} of {len(pool)}", flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name)
    for i, p in enumerate(kept):
        try:
            r = requests.get(p["url"], headers=UA, timeout=90)
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
            cands.append(dict(series=name, file=fn, src=p["src"], pid=p["id"],
                              score=p["score"], w=p["w"], h=p["h"], url=p["url"],
                              tags=p["tags"]))
        except Exception as e:
            print("   dl err", p.get("id"), e, flush=True)
        time.sleep(0.3)

json.dump(cands, open("_tmp/candidates.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
