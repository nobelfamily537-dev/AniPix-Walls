#!/usr/bin/env python3
"""Low-count run: gather candidates for the emptiest series, render 9:16 previews."""
import os, io, json, time, re
import requests
from PIL import Image, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("god eater", ["god eater", "alisa illinchina", "god eater 2"], ["god_eater", "alisa_illinchina", "soma_schicksal"]),
    ("initial d", ["initial d", "ae86", "fujiwara takumi"], ["initial_d", "fujiwara_takumi", "ae86"]),
    ("soul eater", ["soul eater", "maka albarn", "soul evans"], ["soul_eater", "maka_albarn", "soul_evans", "death_the_kid"]),
    ("seven deadly sins", ["seven deadly sins", "nanatsu no taizai", "meliodas"], ["nanatsu_no_taizai", "meliodas", "elizabeth_liones", "escanor"]),
    ("clannad", ["clannad", "nagisa furukawa", "tomoyo sakagami"], ["clannad", "furukawa_nagisa", "fujibayashi_kyou", "sakagami_tomoyo"]),
    ("kaiju no. 8", ["kaiju no 8", "kaiju no. 8", "kafka hibino"], ["kaijuu_8-gou", "hibino_kafka", "ashiro_mina", "shinomiya_kikoru"]),
    ("princess mononoke", ["princess mononoke", "mononoke hime", "san mononoke"], ["mononoke_hime", "san_(mononoke_hime)", "ashitaka"]),
    ("black clover", ["black clover", "asta black clover", "noelle silva"], ["black_clover", "asta_(black_clover)", "yuno_(black_clover)", "noelle_silva"]),
    ("dungeon meshi", ["dungeon meshi", "delicious in dungeon", "marcille"], ["dungeon_meshi", "marcille_donato", "laios_toudan", "izutsumi"]),
    ("nausicaa", ["nausicaa", "nausicaa valley of the wind", "kaze no tani no nausicaa"], ["kaze_no_tani_no_nausicaa", "nausicaa_(kaze_no_tani_no_nausicaa)"]),
    ("touhou project", ["touhou", "reimu hakurei", "marisa kirisame", "sakuya izayoi"], ["touhou", "hakurei_reimu", "kirisame_marisa", "izayoi_sakuya", "konpaku_youmu"]),
    ("cyberpunk edgerunners", ["cyberpunk edgerunners", "lucy cyberpunk", "rebecca cyberpunk"], ["cyberpunk:_edgerunners", "lucy_(cyberpunk)", "rebecca_(cyberpunk)"]),
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

OUT = "_tmp/prevlow"
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


def get(url, params=None, tries=2, sleep=1.1, timeout=60):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                time.sleep(sleep)
                return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(3)
    return None


def wallhaven(q, ratios):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "ratios": ratios,
                 "atleast": "1000x1600", "sorting": "favorites", "page": page}, sleep=1.6)
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
    r = get("https://yande.re/post.json", {"tags": "%s rating:safe score:>20" % tag, "limit": 100}, sleep=0.9)
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


def safebooru(tag):
    out = []
    for pid in (0, 1):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "tags": tag,
                 "json": "1", "limit": 100, "pid": pid}, sleep=0.9)
        if not r:
            break
        try:
            arr = r.json()
        except Exception:
            break
        if not isinstance(arr, list):
            break
        for p in arr:
            d = p.get("directory")
            im = p.get("image")
            if not im:
                continue
            out.append(dict(src="safebooru", id=p.get("id"), score=(p.get("score") or 0),
                            w=p.get("width"), h=p.get("height"),
                            url="https://safebooru.org/images/%s/%s" % (d, im),
                            prev="https://safebooru.org/thumbnails/%s/thumbnail_%s" % (d, im),
                            md5=p.get("hash") or ("%s/%s" % (d, im)),
                            tags=p.get("tags", "").replace("_", " ")))
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
    for q in wqs[:3]:
        pool += wallhaven(q, "9x16,10x16,2x3")
    n_portrait = len(pool)
    for q in wqs[:2]:
        pool += wallhaven(q, "16x9,16x10,3x2")
    print("== %s: wallhaven portrait=%d all=%d" % (name, n_portrait, len(pool)), flush=True)
    for t in ytags[:3]:
        pool += yande(t)
    print("   + yande=%d" % len(pool), flush=True)
    for t in ytags[:3]:
        pool += safebooru(t)
    print("   + safebooru=%d" % len(pool), flush=True)

    seen, kept = set(), []
    pool.sort(key=lambda p: -({"wallhaven": 2.2, "yande": 1.0, "safebooru": 0.9}[p["src"]] * (p["score"] or 0)))
    for p in pool:
        key = p["md5"] or p["url"]
        if key in seen:
            continue
        seen.add(key)
        ms = 2 if p["src"] == "wallhaven" else (15 if p["src"] == "yande" else 5)
        if ok(p, ms):
            kept.append(p)
    kept = kept[:28]
    print("   kept %d" % len(kept), flush=True)

    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    for i, p in enumerate(kept):
        try:
            r = requests.get(p.get("prev") or p["url"], headers=UA, timeout=120)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            prev = render(im)
            fn = "%s_%02d.jpg" % (slug, i)
            prev.save(os.path.join(OUT, fn), "JPEG", quality=80, optimize=True)
            cands.append(dict(series=name, file=fn, src=p["src"], pid=p["id"], score=p["score"],
                              w=p["w"], h=p["h"], url=p["url"], tags=p["tags"]))
        except Exception as e:
            print("   dl err", p.get("id"), e, flush=True)
        time.sleep(0.15)

json.dump(cands, open("_tmp/candlow.json", "w"), indent=1)
print("TOTAL candidates", len(cands), flush=True)
