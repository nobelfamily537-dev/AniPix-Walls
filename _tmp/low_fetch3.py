#!/usr/bin/env python3
"""Stage 1 (low-count run): gather candidates from wallhaven / yande.re / safebooru.org
for the 10 emptiest series, render 9:16 previews, dedupe against wallpapers.json."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SERIES = [
    ("sword art online", "sword art online", ["sword_art_online", "kirigaya_kazuto", "yuuki_asuna"], ["sword_art_online"]),
    ("one punch man", "one punch man", ["one-punch_man", "saitama_(one-punch_man)", "tatsumaki"], ["one-punch_man"]),
    ("detective conan", "detective conan", ["meitantei_conan", "mouri_ran", "edogawa_conan"], ["meitantei_conan"]),
    ("persona 5", "persona 5", ["persona_5", "persona_5_royal"], ["persona_5"]),
    ("fullmetal alchemist", "fullmetal alchemist", ["fullmetal_alchemist", "edward_elric", "riza_hawkeye"], ["fullmetal_alchemist"]),
    ("cyberpunk edgerunners", "cyberpunk edgerunners", ["cyberpunk:_edgerunners", "cyberpunk_(series)"], ["cyberpunk_edgerunners"]),
    ("initial d", "initial d", ["initial_d", "fujiwara_takumi"], ["initial_d"]),
    ("spice and wolf", "spice and wolf", ["ookami_to_koushinryou", "holo_(spice_and_wolf)"], ["spice_and_wolf"]),
    ("inuyasha", "inuyasha", ["inuyasha", "higurashi_kagome"], ["inuyasha"]),
    ("puella magi madoka magica", "madoka magica", ["mahou_shoujo_madoka_magica", "kaname_madoka", "akemi_homura"], ["mahou_shoujo_madoka_magica"]),
]
BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
       "multiple_views","character_sheet","translated","logo","border","frame","letterboxed",
       "twitter_username","web_address","dated","artist_logo","english_commentary","bad_id",
       "bad_pixiv_id","bad_twitter_id","official_art","sketch","monochrome","greyscale",
       "partially_colored","gun","mecha","vehicle","blood","gore","censored","manga","scan","sample",
       "no_humans","food","chibi","comic_panel","bikini","swimsuit","underwear","lingerie","panties",
       "bra","cleavage","no_bra","see_through","cameltoe","spread_legs","large_breasts","huge_breasts",
       "ass","nude","naked","topless","wet","bed","bottomless","sideboob","underboob","cosplay",
       "photo","photorealistic","realistic","3d","vocaloid","hatsune_miku","copyright_request",
       "highres","absurdres","upscaled","jpeg_artifacts","lowres","bad_anatomy","bad_proportions",
       "extra_limbs","extra_fingers","missing_fingers","deformed","collage","sticker","meme",
       "reaction_image","screenshot","anime_screenshot","video_game_screenshot","ui","subtitled",
       "cyrillic_text","chinese_text","korean_text","japanese_text","speech_bubble_translation",
       "white_background","simple_background","transparent_background","close-up","closeup","upper_body",
       "portrait","bust","cowboy_shot","crop","partially_off-screen","character_request","vector_trace",
       "flat_color","sketch_page","rough","unfinished","ai-generated","ai_assisted","novelty",
       "artist_request","signature_request","bad_hands","extra_arms","fusion","crossover","parody",
       "greyscale_background","two-tone_background","gradient_background","spot_color"}
OUT = "_tmp/prev_low"
os.makedirs(OUT, exist_ok=True)

data = json.load(open("wallpapers.json", encoding="utf-8"))
existing_urls = set()
for cat, items in data["categories"].items():
    for e in items:
        for k in ("full", "thumb", "alt"):
            if e.get(k): existing_urls.add(e[k])
print("existing urls", len(existing_urls), flush=True)

cands = []

def render(im, size=(400, 711)):
    tw, th = size
    bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(18))
    fg = im.copy()
    fg.thumbnail((tw, th), Image.LANCZOS)
    bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
    return bg

def get(url, params=None, tries=1, sleep=0.6):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=15)
            if r.status_code == 200:
                time.sleep(sleep); return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(3)
    return None

def wallhaven(q):
    out = []
    for page in (1, 2, 3):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100",
                 "atleast": "1000x1400", "sorting": "favorites", "page": page}, sleep=1.2)
        if not r: break
        try: js = r.json()
        except Exception: break
        for d in js.get("data", []):
            out.append(dict(src="wallhaven", id=d["id"], score=(d.get("favorites") or 0),
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                            prev=(d.get("thumbs") or {}).get("large") or d["path"],
                            md5=d["id"], tags=" ".join(t["name"] for t in d.get("tags", []))))
        if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1): break
    return out

def yande(tag):
    out = []
    r = get("https://yande.re/post.json", {"tags": f"{tag} rating:safe score:>8", "limit": 100}, sleep=0.8)
    if not r: return []
    try: arr = r.json()
    except Exception: return []
    for p in arr:
        out.append(dict(src="yande", id=p.get("id"), score=(p.get("score") or 0),
                        w=p.get("width"), h=p.get("height"),
                        url=p.get("file_url") or p.get("jpeg_url"),
                        prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                        md5=p.get("md5"), tags=p.get("tags", "").replace("_", " ")))
    return out

def konachan(tag):
    out = []
    r = get("https://konachan.net/post.json", {"tags": f"{tag} rating:safe score:>5", "limit": 100}, sleep=0.6)
    if not r: return []
    try: arr = r.json()
    except Exception: return []
    for p in arr:
        out.append(dict(src="konachan", id=p.get("id"), score=(p.get("score") or 0),
                        w=p.get("width"), h=p.get("height"),
                        url=p.get("file_url") or p.get("jpeg_url"),
                        prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                        md5=p.get("md5"), tags=p.get("tags", "").replace("_", " ")))
    return out

def safebooru_org(tag):
    out = []
    for pid in (0, 1):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "tags": tag,
                 "json": "1", "limit": 100, "pid": pid}, sleep=0.8)
        if not r: break
        try: arr = r.json()
        except Exception: break
        if not isinstance(arr, list): break
        for p in arr:
            d = p.get("directory"); im = p.get("image")
            if not im: continue
            out.append(dict(src="safebooruorg", id=p.get("id"), score=(p.get("score") or 0),
                            w=p.get("width"), h=p.get("height"),
                            url=f"https://safebooru.org/images/{d}/{im}",
                            prev=f"https://safebooru.org/images/{d}/{im}",
                            md5=p.get("hash") or f"{d}/{im}", tags=p.get("tags", "").replace("_", " ")))
    return out

def ok(p, ms):
    if not p["url"] or not p["w"] or not p["h"]: return False
    if p["h"] < 1400 or p["w"] < 1000: return False
    if p["h"] / p["w"] < 1.34: return False
    if p["score"] < ms: return False
    if set(p["tags"].split()) & BAD: return False
    if p["url"] in existing_urls or p.get("prev") in existing_urls: return False
    return True

QUERIES = {
    "one punch man": ["saitama", "tatsumaki one punch", "genos"],
    "initial d": ["takumi fujiwara", "toyota ae86", "initial d anime"],
    "detective conan": ["conan edogawa", "ran mouri"],
    "cyberpunk edgerunners": ["lucy cyberpunk", "cyberpunk 2077 anime", "david martinez"],
}
PER = int(os.environ.get("PER", "26"))
IDX = int(os.environ.get("SERIES_IDX", "-1"))
SEL = SERIES if IDX < 0 else [SERIES[IDX]]
for name, wq, ytags, stags in SEL:
    pool = wallhaven(wq)
    for q2 in QUERIES.get(name, []):
        pool += wallhaven(q2)
    print(f"== {name}: wallhaven={len(pool)}", flush=True)
    for t in ytags[:3]:
        pool += yande(t)
    print(f"   + yande={len(pool)}", flush=True)
    for t in stags:
        pool += safebooru_org(t)
    for t in stags[:1]:
        pool += konachan(t)
    print(f"   + safebooru.org={len(pool)}", flush=True)
    seen, kept = set(), []
    pool.sort(key=lambda p: -({"wallhaven": 2.2, "yande": 1.0, "konachan": 1.1, "safebooruorg": 0.9}[p["src"]] * (p["score"] or 0)))
    for p in pool:
        key = p["md5"] or p["url"]
        if key in seen: continue
        seen.add(key)
        ms = {"wallhaven": 4, "yande": 12, "konachan": 8, "safebooruorg": 6}[p["src"]]
        if ok(p, ms): kept.append(p)
    kept = kept[:PER]
    print(f"   kept {len(kept)}", flush=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name)
    for i, p in enumerate(kept):
        try:
            r = requests.get(p["url"], headers=UA, timeout=60)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            fn = f"{slug}_{i:02d}.jpg"
            render(im).save(f"{OUT}/{fn}", "JPEG", quality=84, optimize=True)
            cands.append(dict(series=name, file=fn, src=p["src"], pid=p["id"], score=p["score"],
                              w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
        except Exception as e:
            print("   dl err", p.get("id"), e, flush=True)
        time.sleep(0.15)

import re as _re
_slug = _re.sub(r"[^a-z0-9]+", "-", SEL[0][0])
json.dump(cands, open(f"_tmp/cand_{_slug}.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
