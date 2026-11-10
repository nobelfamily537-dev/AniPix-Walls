#!/usr/bin/env python3
"""AniPix nightly bot.

MODE=fetch : pull high-score portrait art candidates from Danbooru into _cand/
MODE=add   : download approved posts, process to 1080x1920 + thumb, add to wallpapers.json
"""
import os, json, io, time, hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageOps

API = "https://danbooru.donmai.us"
HDR = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
REPO = os.environ.get("GITHUB_REPOSITORY", "nobelfamily537-dev/AniPix-Walls")
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
CFG = {}
try:
    CFG = json.load(open(".nightly/config.json"))
except Exception:
    pass
MODE = (CFG.get("mode") or os.environ.get("MODE", "fetch")).strip()

SERIES = {
    "mashle": {
        "wallhaven": ["mashle", "mashle magic and muscles"],
        "booru": ["mashle", "mashle_(manga)"],
        "chars": ["mash_burnedead", "lance_crown", "dot_barrett", "finn_ames"],
    },
    "ranma": {
        "wallhaven": ["ranma", "ranma 1/2"],
        "booru": ["ranma_1/2", "ranma_1/2_(series)"],
        "chars": ["saotome_ranma", "tendou_akane", "shampoo_(ranma_1/2)"],
    },
    "spice_and_wolf": {
        "wallhaven": ["spice and wolf", "holo spice and wolf"],
        "booru": ["ookami_to_koushinryou", "spice_and_wolf"],
        "chars": ["holo"],
    },
    "kaguya": {
        "wallhaven": ["kaguya", "kaguya sama"],
        "booru": ["kaguya-sama_wa_kokurasetai_~tensai-tachi_no_renai_zunousen~",
                  "kaguya-sama_wa_kokurasetai"],
        "chars": ["shinomiya_kaguya", "fujiwara_chika", "hayasaka_ai"],
    },
    "mob_psycho": {
        "wallhaven": ["mob psycho", "mob psycho 100"],
        "booru": ["mob_psycho_100"],
        "chars": ["kageyama_shigeo", "reigen_arataka"],
    },
    "apothecary": {
        "wallhaven": ["apothecary diaries", "maomao"],
        "booru": ["kusuriya_no_hitorigoto"],
        "chars": ["maomao_(kusuriya_no_hitorigoto)", "jinshi_(kusuriya_no_hitorigoto)"],
    },
    "haikyuu": {
        "wallhaven": ["haikyuu"],
        "booru": ["haikyuu!!"],
        "chars": ["hinata_shouyou", "kageyama_tobio"],
    },
}

BAD = {"text", "english_text", "watermark", "signature", "comic", "multiple_views",
       "sketch", "monochrome", "greyscale", "lowres", "bad_id", "photo", "cosplay",
       "real_world", "border", "letterboxed", "scan", "cropped", "translation_request",
       "character_request", "duo", "multiple_boys", "speech_bubble"}


def get(url, **kw):
    for _ in range(3):
        try:
            r = requests.get(url, headers=HDR, timeout=90, **kw)
            if r.status_code == 200:
                return r
            print("  http", r.status_code, url[:90])
        except Exception as e:
            print("  err", e)
        time.sleep(2)
    return None


# ---------------------------------------------------------------- fetch mode
def wh_search(q, ratios="9x16"):
    params = {"q": q, "categories": "010", "purity": "100",
              "sorting": "favorites", "order": "desc", "page": 1}
    if ratios:
        params["ratios"] = ratios
    r = get("https://wallhaven.cc/api/v1/search", params=params)
    if not r:
        return []
    out = []
    for d in r.json().get("data", []):
        out.append({"url": d["path"], "w": d["dimension_x"], "h": d["dimension_y"],
                    "score": d.get("favorites", 0), "id": f"wh{d['id']}",
                    "tags": " ".join(t["name"].replace(" ", "_") for t in d.get("tags", []))})
    print(f"   wallhaven '{q}' ratios={ratios} -> {len(out)}")
    return out


def booru_search(tag, limit=100):
    out = []
    for base, src in (("https://konachan.net/post.json", "kc"),
                      ("https://yande.re/post.json", "yd")):
        r = get(base, params={"tags": f"{tag} rating:safe", "limit": limit})
        if not r:
            continue
        try:
            posts = r.json()
        except Exception:
            continue
        n = 0
        for p in posts:
            if not p.get("file_url"):
                continue
            out.append({"url": p["file_url"], "w": p.get("width") or 0,
                        "h": p.get("height") or 0, "score": p.get("score") or 0,
                        "id": f"{src}{p['id']}", "tags": p.get("tags", "")})
            n += 1
        print(f"   {src} '{tag}' -> {n}")
    return out


def do_fetch():
    per = int(CFG.get("per_series") or os.environ.get("PER", "20"))
    slugs = [x for x in (CFG.get("series") or os.environ.get("SERIES", "")).split() if x]
    os.makedirs("_cand", exist_ok=True)
    manifest = []

    for slug in slugs:
        cfg = SERIES.get(slug)
        if not cfg:
            print(f"unknown slug {slug}")
            continue
        outdir = os.path.join("_cand", slug)
        os.makedirs(outdir, exist_ok=True)
        cands, seen_url = [], set()
        for q in cfg["wallhaven"]:
            for ratios in ("9x16", ""):
                for c in wh_search(q, ratios):
                    if c["url"] not in seen_url:
                        seen_url.add(c["url"])
                        cands.append(c)
                if len(cands) >= per * 3:
                    break
        for t in cfg["booru"]:
            for c in booru_search(t):
                if c["url"] not in seen_url:
                    seen_url.add(c["url"])
                    cands.append(c)

        # rank: prefer portrait, decent resolution, high score
        def ok(c):
            w, h = int(c["w"] or 0), int(c["h"] or 0)
            if not w or not h:
                return False
            if h < w * 1.05 or w < 640 or h < 1000:
                return False
            if set(c["tags"].lower().split()) & BAD:
                return False
            return True

        good = [c for c in cands if ok(c)]
        good.sort(key=lambda c: -(c["score"] or 0))
        print(f"{slug}: {len(cands)} raw, {len(good)} usable")
        got = 0
        for c in good:
            if got >= per:
                break
            resp = get(c["url"])
            if not resp or len(resp.content) < 40000:
                continue
            ext = os.path.splitext(c["url"].split("?")[0])[1] or ".jpg"
            fn = f"{got:02d}_{c['id']}{ext}"
            with open(os.path.join(outdir, fn), "wb") as f:
                f.write(resp.content)
            manifest.append({"slug": slug, "file": f"_cand/{slug}/{fn}",
                             "src": c["id"], "score": c["score"],
                             "w": c["w"], "h": c["h"],
                             "tags": c["tags"][:300], "url": c["url"]})
            got += 1
            time.sleep(0.2)
        print(f"{slug}: saved {got}")

    json.dump(manifest, open("_cand/manifest.json", "w"), indent=1)
    print("TOTAL", len(manifest))


# ------------------------------------------------------------------ add mode
def crop_9x16(im, yfocus=0.28):
    w, h = im.size
    t = 9 / 16
    if w / h > t:
        nw = int(h * t)
        x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = int(w / t)
    y = int((h - nh) * yfocus)
    return im.crop((0, y, w, y + nh))


def do_add():
    spec = CFG.get("spec") or json.loads(os.environ.get("SPEC", "[]"))
    data = json.load(open("wallpapers.json", encoding="utf-8"))
    cats = data["categories"]
    tagmap = data.setdefault("tags", {})
    existing_urls = set()
    for items in cats.values():
        for e in items:
            for k in ("full", "thumb", "alt"):
                if e.get(k):
                    existing_urls.add(e[k])
    existing_ids = {e["id"] for items in cats.values() for e in items}
    added = []
    for item in spec:
        pid = item["post_id"]
        cat = item["category"]
        tags = [t.strip().lower() for t in item["tags"].split(",") if t.strip()]
        try:
            r = get(f"{API}/posts/{pid}.json")
            if not r:
                print(f"SKIP {pid}: no post json")
                continue
            p = r.json()
            furl = p.get("file_url")
            if not furl:
                print(f"SKIP {pid}: no file_url")
                continue
            wid = "wpx" + hashlib.md5(f"db{pid}".encode()).hexdigest()[:10]
            if wid in existing_ids:
                print(f"SKIP {pid}: id exists {wid}")
                continue
            full_url = f"{RAW}/{cat}/{wid}.jpg"
            if full_url in existing_urls:
                print(f"SKIP {pid}: url exists")
                continue
            resp = get(furl)
            if not resp:
                print(f"SKIP {pid}: download failed")
                continue
            im = Image.open(io.BytesIO(resp.content)).convert("RGB")
            if im.width < 700 or im.height < 900:
                print(f"SKIP {pid}: too small {im.size}")
                continue
            out = ImageOps.fit(crop_9x16(im), (1080, 1920), method=Image.LANCZOS)
            out.save(f"{cat}/{wid}.jpg", "JPEG", quality=95, optimize=True, progressive=True)
            out.resize((360, 640), Image.LANCZOS).save(
                f"{cat}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True, progressive=True)
            entry = {
                "id": wid,
                "thumb": f"{RAW}/{cat}/{wid}_thumb.jpg",
                "full": full_url,
                "alt": full_url,
                "tags": ",".join(tags),
                "date": TODAY,
            }
            cats[cat].insert(0, entry)
            for t in tags:
                tagmap.setdefault(t, [])
                if wid not in tagmap[t]:
                    tagmap[t].insert(0, wid)
            existing_ids.add(wid)
            existing_urls.update([full_url, entry["thumb"]])
            added.append((wid, cat, pid))
            print(f"ADDED {wid} {cat} post={pid}")
            time.sleep(0.3)
        except Exception as e:
            print(f"ERROR {pid}: {e}")

    data["version"] = int(data.get("version", 1)) + 1
    data["last_updated"] = TODAY
    json.dump(data, open("wallpapers.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"DONE added {len(added)}: {added}")


if MODE == "fetch":
    do_fetch()
elif MODE == "cleanup":
    import subprocess
    for f in (".github/workflows/nightly-bot.yml", "scripts/nightly_bot.py",
              ".nightly/config.json", ".nightly_probe"):
        subprocess.run(["git", "rm", "-q", "-f", f], check=False)
    subprocess.run(["git", "push", "origin", "--delete", "nightly-candidates"], check=False)
    print("cleanup staged")
else:
    do_add()
