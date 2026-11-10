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
    "spice_and_wolf": ["spice and wolf", "holo", "holo the wise wolf", "ookami to koushinryou"],
    "kaguya": ["shinomiya kaguya", "kaguya-sama", "kaguya sama love is war",
               "fujiwara chika", "hayasaka ai"],
    "ranma": ["ranma", "saotome ranma", "shampoo ranma", "tendo akane"],
    "apothecary": ["maomao", "apothecary diaries", "kusuriya no hitorigoto"],
    "lycoris": ["lycoris recoil", "chisato nishikigi", "takina inoue"],
    "yofukashi": ["yofukashi no uta", "call of the night", "nazuna nanakusa"],
    "komi": ["komi san", "komi cant communicate", "shouko komi"],
    "horimiya": ["horimiya", "kyoko hori"],
    "classroom_elite": ["classroom of the elite", "ayanokoji", "kiyotaka ayanokoji"],
    "haikyuu": ["haikyuu", "hinata shouyou", "kageyama tobio"],
}

BAD = {"text", "english_text", "watermark", "signature", "comic", "multiple_views",
       "sketch", "monochrome", "greyscale", "lowres", "bad_id", "photo", "cosplay",
       "real_world", "border", "letterboxed", "scan", "cropped", "translation_request", "poster", "logo", "cover", "book", "manga",
       "character_request", "duo", "multiple_boys", "speech_bubble"}


def get(url, **kw):
    for _ in range(2):
        try:
            r = requests.get(url, headers=HDR, timeout=45, **kw)
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
              "sorting": "favorites", "order": "desc", "page": 1,
              "atleast": "900x1200"}
    if ratios:
        params["ratios"] = ratios
    r = get("https://wallhaven.cc/api/v1/search", params=params)
    if not r:
        return []
    out = []
    for d in r.json().get("data", []):
        tags = " ".join(t["name"].replace(" ", "_") for t in d.get("tags", []))
        out.append({"url": d["path"], "w": d["dimension_x"], "h": d["dimension_y"],
                    "score": d.get("favorites", 0), "id": f"wh{d['id']}", "tags": tags})
    print(f"   wallhaven '{q}' ratios={ratios} -> {len(out)}")
    return out


def do_fetch():
    per = int(CFG.get("per_series") or os.environ.get("PER", "14"))
    slugs = [x for x in (CFG.get("series") or os.environ.get("SERIES", "")).split() if x]
    os.makedirs("_cand", exist_ok=True)
    manifest = []
    for slug in slugs:
        qs = SERIES.get(slug)
        if not qs:
            print(f"unknown slug {slug}")
            continue
        outdir = os.path.join("_cand", slug)
        os.makedirs(outdir, exist_ok=True)
        cands, seen = [], set()
        for q in qs:
            for ratios in ("9x16", ""):
                for c in wh_search(q, ratios):
                    if c["url"] not in seen:
                        seen.add(c["url"])
                        cands.append(c)
        good = []
        for c in cands:
            w, h = int(c["w"] or 0), int(c["h"] or 0)
            if not w or not h or h < w * 1.05 or w < 800 or h < 1150:
                continue
            ts = set(c["tags"].lower().split())
            if ts & BAD:
                continue
            good.append(c)
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
            manifest.append({"slug": slug, "file": f"_cand/{slug}/{fn}", "src": c["id"],
                             "score": c["score"], "w": c["w"], "h": c["h"],
                             "tags": c["tags"][:300], "url": c["url"]})
            got += 1
            time.sleep(0.2)
        print(f"{slug}: saved {got}")
    json.dump(manifest, open("_cand/manifest.json", "w"), indent=1)
    print("TOTAL", len(manifest))


# ------------------------------------------------------------------ add mode
def crop_9x16(im, yfocus=0.28, xfocus=0.5):
    w, h = im.size
    t = 9 / 16
    if w / h > t:
        nw = int(h * t)
        x = int((w - nw) * xfocus)
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
        url = item["url"]
        cat = item["category"]
        tags = [t.strip().lower() for t in item["tags"].split(",") if t.strip()]
        try:
            wid = "wpx" + hashlib.md5(url.encode()).hexdigest()[:10]
            full_url = f"{RAW}/{cat}/{wid}.jpg"
            if wid in existing_ids or full_url in existing_urls:
                print(f"SKIP {url}: duplicate")
                continue
            resp = get(url)
            if not resp:
                print(f"SKIP {url}: download failed")
                continue
            im = Image.open(io.BytesIO(resp.content)).convert("RGB")
            if im.width < 700 or im.height < 900:
                print(f"SKIP {url}: too small {im.size}")
                continue
            out = ImageOps.fit(
                crop_9x16(im, item.get("yfocus", 0.28), item.get("xfocus", 0.5)),
                (1080, 1920), method=Image.LANCZOS)
            out.save(f"{cat}/{wid}.jpg", "JPEG", quality=95, optimize=True, progressive=True)
            out.resize((360, 640), Image.LANCZOS).save(
                f"{cat}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True, progressive=True)
            entry = {"id": wid, "thumb": f"{RAW}/{cat}/{wid}_thumb.jpg",
                     "full": full_url, "alt": full_url,
                     "tags": ",".join(tags), "date": TODAY}
            cats[cat].insert(0, entry)
            for t in tags:
                tagmap.setdefault(t, [])
                if wid not in tagmap[t]:
                    tagmap[t].insert(0, wid)
            existing_ids.add(wid)
            existing_urls.update([full_url, entry["thumb"]])
            added.append((wid, cat))
            print(f"ADDED {wid} {cat} <- {url}")
            time.sleep(0.2)
        except Exception as e:
            print(f"ERROR {url}: {e}")

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
