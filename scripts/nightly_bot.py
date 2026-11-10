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
    "mashle": ["mashle*"],
    "ranma": ["ranma*"],
    "spice_and_wolf": ["ookami_to_koushinryou*", "spice_and_wolf*"],
    "kaguya": ["kaguya*sama*"],
    "mob_psycho": ["mob_psycho*"],
    "apothecary": ["kusuriya*"],
    "classroom_elite": ["youkoso_jitsuryoku*"],
    "haikyuu": ["haikyuu*"],
    "overlord": ["overlord_*"],
    "gintama": ["gintama*"],
    "lycoris": ["lycoris_recoil*"],
    "yofukashi": ["yofukashi_no_uta*"],
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
def do_fetch():
    per = int(CFG.get("per_series") or os.environ.get("PER", "24"))
    slugs = [x for x in (CFG.get("series") or os.environ.get("SERIES", "")).split() if x]
    os.makedirs("_cand", exist_ok=True)
    manifest = []

    def resolve(pattern):
        r = get(f"{API}/tags.json", params={
            "search[name_matches]": pattern, "search[category]": 3, "limit": 30})
        if not r:
            return None, 0
        tags = [t for t in r.json() if t.get("post_count", 0) > 0]
        if not tags:
            return None, 0
        tags.sort(key=lambda t: -t["post_count"])
        return tags[0]["name"], tags[0]["post_count"]

    for slug in slugs:
        best, bestc = None, 0
        for p in SERIES.get(slug, [slug + "*"]):
            name, cnt = resolve(p)
            print(f"{slug}: {p} -> {name} ({cnt})")
            if cnt > bestc:
                best, bestc = name, cnt
        if not best:
            print(f"NO TAG for {slug}")
            continue
        outdir = os.path.join("_cand", slug)
        os.makedirs(outdir, exist_ok=True)
        got, seen = 0, set()
        for page in (1, 2):
            r = get(f"{API}/posts.json", params={
                "tags": f"{best} rating:general", "limit": 200, "page": page})
            if not r:
                break
            posts = r.json()
            posts.sort(key=lambda p: -(p.get("score") or 0))
            for p in posts:
                if got >= per:
                    break
                w, h = int(p.get("image_width") or 0), int(p.get("image_height") or 0)
                if not w or not h or h < w * 1.15 or w < 700 or h < 900:
                    continue
                if (p.get("score") or 0) < 10:
                    continue
                if set((p.get("tag_string") or "").split()) & BAD:
                    continue
                furl = p.get("file_url") or ""
                if not furl or p["id"] in seen:
                    continue
                seen.add(p["id"])
                ext = os.path.splitext(furl)[1] or ".jpg"
                fn = f"{got:02d}_{p['id']}{ext}"
                resp = get(furl)
                if not resp or len(resp.content) < 40000:
                    continue
                with open(os.path.join(outdir, fn), "wb") as f:
                    f.write(resp.content)
                manifest.append({
                    "slug": slug, "file": f"_cand/{slug}/{fn}", "post": p["id"],
                    "score": p.get("score"), "w": w, "h": h,
                    "chars": p.get("tag_string_character", ""),
                    "tags": p.get("tag_string", "")[:400],
                })
                got += 1
                time.sleep(0.3)
            if got >= per:
                break
        print(f"{slug}: {got} candidates from {best}")
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
