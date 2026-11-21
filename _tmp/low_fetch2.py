#!/usr/bin/env python3
"""Low-count run v2: leaner gather (wallhaven + yande only), render 9:16 previews."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("god eater", ["god eater", "alisa illinchina"], ["god_eater", "alisa_illinchina"]),
    ("initial d", ["initial d", "ae86"], ["initial_d", "fujiwara_takumi"]),
    ("soul eater", ["soul eater", "maka albarn"], ["soul_eater", "maka_albarn"]),
    ("seven deadly sins", ["seven deadly sins", "nanatsu no taizai"], ["nanatsu_no_taizai", "meliodas"]),
    ("clannad", ["clannad", "nagisa furukawa"], ["clannad", "furukawa_nagisa"]),
    ("kaiju no. 8", ["kaiju no 8", "kafka hibino"], ["kaijuu_8-gou", "hibino_kafka"]),
    ("princess mononoke", ["princess mononoke", "mononoke hime"], ["mononoke_hime", "san_(mononoke_hime)"]),
    ("black clover", ["black clover", "asta black clover"], ["black_clover", "noelle_silva"]),
    ("dungeon meshi", ["dungeon meshi", "marcille"], ["dungeon_meshi", "marcille_donato"]),
    ("nausicaa", ["nausicaa", "valley of the wind"], ["kaze_no_tani_no_nausicaa"]),
    ("touhou project", ["touhou", "reimu hakurei"], ["touhou", "hakurei_reimu"]),
    ("cyberpunk edgerunners", ["cyberpunk edgerunners", "lucy cyberpunk"], ["cyberpunk:_edgerunners", "lucy_(cyberpunk)"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "bad_pixiv_id", "bad_twitter_id", "official_art", "sketch", "monochrome", "greyscale",
       "partially_colored", "gun", "mecha", "vehicle", "blood", "gore", "censored", "manga", "scan", "sample",
       "food", "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties",
       "bra", "cleavage", "no_bra", "see_through", "cameltoe", "spread_legs", "large_breasts", "huge_breasts",
       "ass", "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob",
       "photo", "photograph", "real", "cosplay", "3d", "render", "screencap", "screenshot", "anime_screenshot",
       "reference_sheet", "concept_art", "wallpaper_engine", "upscaled", "jpeg_artifacts", "lowres"}

OUT = "_tmp/prevlow2"
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


def get(url, params=None, sleep=1.2, timeout=20):
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


def wallhaven(q, ratios):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "ratios": ratios,
                 "atleast": "1000x1600", "sorting": "favorites", "page": page}, sleep=1.4)
        if not r:
            break
        try:
            js = r.json()
        except Exception:
            break
        for d in js.get("data", []):
            out.append(dict(src="wallhaven", id=d["id"], score=(d.get("favorites") or 0),
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                            prev=(d.get("thumbs") or {}).get("large") or d["path"],
                            md5=d["id"], tags=" ".join(t["name"] for t in d.get("tags", []))))
        if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1):
            break
    return out


def yande(tag):
    out = []
    r = get("https://yande.re/post.json", {"tags": "%s rating:safe score:>20" % tag, "limit": 100}, sleep=0.8, timeout=25)
    if not r:
        return []
    try:
        arr = r.json()
    except Exception:
        return []
    for p in arr:
        out.append(dict(src="yande", id=p.get("id"), score=(p.get("score") or 0),
                        w=p.get("width"), h=p.get("height"),
                        url=p.get("file_url") or p.get("jpeg_url"),
                        prev=p.get("sample_url") or p.get("jpeg_url") or p.get("file_url"),
                        md5=p.get("md5"), tags=p.get("tags", "").replace("_", " ")))
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


for name, wqs, ytags in SERIES:
    pool = []
    for q in wqs:
        pool += wallhaven(q, "9x16,10x16,2x3")
    print("== %s: wallhaven=%d" % (name, len(pool)), flush=True)
    for q in wqs[:1]:
        pool += wallhaven(q, "16x9,16x10")
    for t in ytags:
        pool += yande(t)
    print("   pool=%d" % len(pool), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -({"wallhaven": 2.2, "yande": 1.0}[p["src"]] * (p["score"] or 0)))
    for p in pool:
        key = p["md5"] or p["url"]
        if key in seen:
            continue
        seen.add(key)
        ms = 2 if p["src"] == "wallhaven" else 15
        if ok(p, ms):
            kept.append(p)
    kept = kept[:26]
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

json.dump(cands, open("_tmp/candlow2.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
