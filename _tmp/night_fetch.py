#!/usr/bin/env python3
"""Nightly gap-fill: wallhaven + safebooru candidates for anime with ZERO app coverage."""
import os, io, json, time, re, html
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("steins-gate", "steins gate", ["steins_gate", "makise_kurisu", "okabe_rintarou", "shiina_mayuri", "steins;gate"]),
    ("code-geass", "code geass", ["code_geass", "lelouch_vi_britannia", "c.c.", "kouzuki_kallen", "lelouch_lamperouge"]),
    ("cowboy-bebop", "cowboy bebop", ["cowboy_bebop", "spike_spiegel", "faye_valentine", "edward_wong"]),
    ("monogatari", "monogatari", ["monogatari_series", "senjougahara_hitagi", "oshino_shinobu", "hachikuji_mayoi", "bakemonogatari"]),
    ("vinland-saga", "vinland saga", ["vinland_saga", "thorfinn_(vinland_saga)", "askeladd", "canute_(vinland_saga)"]),
    ("mob-psycho", "mob psycho 100", ["mob_psycho_100", "kageyama_shigeo", "reigen_arataka", "mob_psycho"]),
    ("kill-la-kill", "kill la kill", ["kill_la_kill", "matoi_ryuuko", "kiryuuin_satsuki", "mankanshoku_mako"]),
    ("overlord", "overlord", ["overlord_(anime)", "ainz_ooal_gown", "albedo_(overlord)", "shalltear_bloodfallen"]),
]

BAD = {"text","english_text","watermark","signature","artist_name","speech_bubble","comic","4koma",
       "multiple_views","character_sheet","translated","logo","border","frame","letterboxed",
       "twitter_username","web_address","dated","artist_logo","english_commentary","bad_id",
       "bad_pixiv_id","bad_twitter_id","official_art","sketch","monochrome","greyscale",
       "partially_colored","gun","mecha","vehicle","blood","gore","censored","manga","scan","sample",
       "no_humans","food","chibi","comic_panel","bikini","swimsuit","underwear","lingerie","panties",
       "bra","cleavage","no_bra","see_through","cameltoe","spread_legs","large_breasts","huge_breasts",
       "ass","nude","naked","topless","wet","bed","bottomless","sideboob","underboob","loli",
       "close-up","closeup","cropped","faceless","solo_focus","lower_body","upper_body","legs","thighs",
       "midriff","navel","stomach","skirt_lift","pantyshot","upskirt","weapon","sword","armor","armour"}

OUT = "_tmp/night_prev"; SHEETS = "_tmp/night_sheets"
os.makedirs(OUT, exist_ok=True); os.makedirs(SHEETS, exist_ok=True)

used = set()
wp = json.load(open("wallpapers.json"))
for cat, ents in wp["categories"].items():
    for e in ents:
        for f in (e.get("full"), e.get("thumb")):
            m = re.search(r"wallhaven-([a-z0-9]+)\.(?:jpg|png|jpeg|webp)", f or "")
            if m: used.add(m.group(1))
print("used ids:", len(used), flush=True)

def get(url, params=None, tries=3, sleep=1.0):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                time.sleep(sleep); return r
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", e, flush=True)
        time.sleep(4)
    return None

def okratio(w, h):
    if not w or not h: return False
    r = h / w
    return 1.40 <= r <= 1.95 and h >= 1500 and w >= 800

def render(im, size=(450, 800)):
    tw, th = size
    return ImageOps.fit(im, (tw, th), method=Image.LANCZOS)

# ---------- wallhaven ----------
def wallhaven(q):
    out = []
    for page in (1, 2):
        r = get("https://wallhaven.cc/api/v1/search",
                {"q": q, "categories": "010", "purity": "100", "ratios": "portrait",
                 "atleast": "1000x1500", "sorting": "favorites", "page": page})
        if not r: break
        try: js = r.json()
        except Exception: break
        for d in js.get("data", []):
            out.append(dict(src="wh", id=d["id"], score=(d.get("favorites") or 0),
                            w=d["dimension_x"], h=d["dimension_y"], url=d["path"],
                            prev=(d.get("thumbs") or {}).get("large") or d["path"],
                            tags=" ".join(t["name"] for t in d.get("tags", []))))
        if js.get("meta", {}).get("current_page", 1) >= js.get("meta", {}).get("last_page", 1): break
    return out

# ---------- safebooru ----------
def safebooru(tag):
    out = []
    for pid in (0, 1, 2):
        r = get("https://safebooru.org/index.php",
                {"page": "dapi", "s": "post", "q": "index", "tags": tag + " sort:score:desc",
                 "limit": 100, "pid": pid}, sleep=1.2)
        if not r: break
        for m in re.finditer(r"<post\b([^>]*)/?>", r.text):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            try:
                w, h, sc = int(a.get("width", 0)), int(a.get("height", 0)), int(a.get("score", 0))
            except Exception:
                continue
            if sc < 8: continue
            prev = a.get("sample_url") or ""
            if not prev or prev.endswith("sample.jpg") is False and "sample" not in prev:
                prev = f"https://safebooru.org/images/{a.get('directory')}/{a.get('image')}"
            out.append(dict(src="sb", id="sb" + a.get("id", ""), score=sc, w=w, h=h,
                            url=f"https://safebooru.org/images/{a.get('directory')}/{a.get('image')}",
                            prev=prev, tags=html.unescape(a.get("tags", ""))))
    return out

allc = []
for slug, whq, sbtags in SERIES:
    pool = []
    pool += wallhaven(whq)
    for t in sbtags:
        pool += safebooru(t)
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        if p["id"] in seen: continue
        seen.add(p["id"])
        if p["src"] == "wh" and p["id"] in used: continue
        if not okratio(p["w"], p["h"]): continue
        if set(p["tags"].split()) & BAD: continue
        kept.append(p)
    kept = kept[:16]
    print(f"== {slug}: pool={len(pool)} kept={len(kept)}", flush=True)
    mine = []
    for i, p in enumerate(kept):
        fn = f"{slug}_{i:02d}.jpg"
        try:
            r = requests.get(p["prev"], headers=UA, timeout=90); r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.width < 300: raise ValueError("tiny")
            render(im).save(os.path.join(OUT, fn), "JPEG", quality=82, optimize=True)
            rec = dict(slug=slug, file=fn, **p); allc.append(rec); mine.append(rec)
        except Exception as e:
            print("  err", fn, e, flush=True)
        time.sleep(0.2)
    if mine:
        cw, ch, cols = 240, 427, 4
        rows = (len(mine) + cols - 1) // cols
        sheet = Image.new("RGB", (cw*cols, ch*rows), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, rec in enumerate(mine):
            im = Image.open(os.path.join(OUT, rec["file"])).resize((cw, ch), Image.LANCZOS)
            x, y = (i % cols)*cw, (i//cols)*ch
            sheet.paste(im, (x, y))
            d.rectangle([x, y, x+44, y+26], fill=(0, 0, 0))
            d.text((x+6, y+6), f"{i}", fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, f"{slug}.jpg"), "JPEG", quality=80, optimize=True)

json.dump(allc, open("_tmp/night_cands.json", "w"), indent=1)
print("TOTAL", len(allc), flush=True)
