#!/usr/bin/env python3
"""Low-count run v3: konachan.net + danbooru + wallhaven, render 9:16 previews."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("god eater", ["god_eater", "alisa_illinchina"], ["god eater", "alisa illinchina"]),
    ("initial d", ["initial_d", "fujiwara_takumi"], ["initial d", "ae86"]),
    ("soul eater", ["soul_eater", "maka_albarn", "soul_evans"], ["soul eater", "maka albarn"]),
    ("seven deadly sins", ["nanatsu_no_taizai", "meliodas", "elizabeth_liones"], ["seven deadly sins", "nanatsu no taizai"]),
    ("clannad", ["clannad", "furukawa_nagisa", "sakagami_tomoyo"], ["clannad", "nagisa furukawa"]),
    ("kaiju no. 8", ["kaijuu_8-gou", "hibino_kafka", "ashiro_mina"], ["kaiju no 8", "kaiju no. 8"]),
    ("princess mononoke", ["mononoke_hime", "san_(mononoke_hime)", "ashitaka"], ["princess mononoke", "mononoke hime"]),
    ("black clover", ["black_clover", "asta_(black_clover)", "noelle_silva"], ["black clover", "asta black clover"]),
    ("dungeon meshi", ["dungeon_meshi", "marcille_donato", "laios_toudan"], ["dungeon meshi", "delicious in dungeon"]),
    ("nausicaa", ["kaze_no_tani_no_nausicaa", "nausicaa_(kaze_no_tani_no_nausicaa)"], ["nausicaa", "valley of the wind"]),
    ("touhou project", ["touhou", "hakurei_reimu", "kirisame_marisa", "izayoi_sakuya"], ["touhou", "reimu hakurei"]),
    ("cyberpunk edgerunners", ["cyberpunk:_edgerunners", "lucy_(cyberpunk)", "rebecca_(cyberpunk)"], ["cyberpunk edgerunners", "lucy cyberpunk"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "bad_pixiv_id", "bad_twitter_id", "sketch", "monochrome", "greyscale",
       "partially_colored", "gun", "mecha", "vehicle", "blood", "gore", "censored", "manga", "scan", "sample",
       "food", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties",
       "bra", "cleavage", "no_bra", "see_through", "cameltoe", "spread_legs", "large_breasts", "huge_breasts",
       "ass", "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob",
       "photo", "photograph", "cosplay", "screencap", "screenshot", "anime_screenshot",
       "reference_sheet", "concept_art", "upscaled", "jpeg_artifacts", "lowres", "highres", "absurdres"}

OUT = "_tmp/prevlow3"
os.makedirs(OUT, exist_ok=True)
cands = []


def render(im, size=(360, 640)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = 9 / 16
    if r > 2.05:
        bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w / t)
        y = int((h - nh) * (0.04 if r >= 1.55 else 0.18))
        return im.crop((0, y, w, y + nh))
    nw = int(h * t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def get(url, params=None, sleep=1.0, timeout=25):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        if r.status_code == 200:
            time.sleep(sleep)
            return r
        print("  HTTP", r.status_code, url, flush=True)
    except Exception as e:
        print("  ERR", type(e).__name__, flush=True)
    time.sleep(2)
    return None


def booru_json(url, tags, limit=100):
    r = get(url, {"tags": tags, "limit": limit})
    if not r:
        return []
    try:
        arr = r.json()
    except Exception:
        return []
    return arr if isinstance(arr, list) else []


def konachan(tag):
    out = []
    for p in booru_json("https://konachan.net/post.json", "%s rating:safe score:>10" % tag):
        out.append(dict(src="konachan", id=p.get("id"), score=(p.get("score") or 0),
                        w=p.get("width"), h=p.get("height"),
                        url=p.get("jpeg_url") or p.get("file_url"),
                        prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                        md5=p.get("md5"), tags=p.get("tags", "").replace("_", " ")))
    return out


def danbooru(tag):
    out = []
    for p in booru_json("https://danbooru.donmai.us/posts.json", "%s rating:g score:>15" % tag):
        url = p.get("file_url") or p.get("large_file_url")
        out.append(dict(src="danbooru", id=p.get("id"), score=(p.get("score") or 0),
                        w=p.get("image_width"), h=p.get("image_height"), url=url,
                        prev=p.get("large_file_url") or p.get("preview_file_url") or url,
                        md5=p.get("md5"), tags=p.get("tag_string", "").replace("_", " ")))
    return out


def wallhaven(q):
    out = []
    r = get("https://wallhaven.cc/api/v1/search",
            {"q": q, "categories": "010", "purity": "100", "ratios": "9x16,10x16,2x3",
             "atleast": "1000x1600", "sorting": "favorites"}, sleep=1.3)
    if not r:
        return []
    try:
        js = r.json()
    except Exception:
        return []
    for d in js.get("data", []):
        out.append(dict(src="wallhaven", id=d["id"], score=(d.get("favorites") or 0),
                        w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                        prev=(d.get("thumbs") or {}).get("large") or d["path"],
                        md5=d["id"], tags=" ".join(t["name"] for t in d.get("tags", []))))
    return out


def ok(p, ms):
    if not p["url"] or not p["w"] or not p["h"]:
        return False
    if p["h"] < 1400 or p["w"] < 700:
        return False
    if p["h"] / p["w"] < 1.25:
        return False
    if (p["score"] or 0) < ms:
        return False
    if set(p["tags"].split()) & BAD:
        return False
    return True


WEIGHT = {"konachan": 1.6, "danbooru": 1.0, "wallhaven": 2.2}
MIN = {"konachan": 8, "danbooru": 15, "wallhaven": 2}

for name, ktags, wqs in SERIES:
    pool = []
    for t in ktags:
        pool += konachan(t)
    print("== %s: konachan=%d" % (name, len(pool)), flush=True)
    for t in ktags[:2]:
        pool += danbooru(t)
    print("   + danbooru=%d" % len(pool), flush=True)
    for q in wqs:
        pool += wallhaven(q)
    print("   + wallhaven=%d" % len(pool), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -(WEIGHT[p["src"]] * (p["score"] or 0)))
    for p in pool:
        key = p["md5"] or p["url"]
        if key in seen:
            continue
        seen.add(key)
        if ok(p, MIN[p["src"]]):
            kept.append(p)
    kept = kept[:30]
    print("   kept %d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    for i, p in enumerate(kept):
        try:
            r = requests.get(p.get("prev") or p["url"], headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            prev = render(im)
            fn = "%s_%02d.jpg" % (slug, i)
            prev.save(os.path.join(OUT, fn), "JPEG", quality=80, optimize=True)
            cands.append(dict(series=name, file=fn, src=p["src"], pid=p["id"], score=p["score"],
                              w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
        except Exception as e:
            print("   dl err", p.get("id"), type(e).__name__, flush=True)
        time.sleep(0.1)

json.dump(cands, open("_tmp/candlow3.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
