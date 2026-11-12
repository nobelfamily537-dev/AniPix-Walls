#!/usr/bin/env python3
"""Process picked candidates into final 1080x1920 wallpapers + thumbs and add
them to wallpapers.json.

Inputs:
  _tmp/candidates.json   from fetch_low.py
  _tmp/picks.json        [{"slug","i","cat","tags"}...]
"""
import io, json, os, hashlib, sys
import requests
from PIL import Image, ImageOps

UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = "nobelfamily537-dev/AniPix-Walls"
RAW = "https://raw.githubusercontent.com/%s/main" % REPO
TODAY = "2026-11-12"

SERIES = {s["slug"]: s for s in json.load(open(os.path.join(HERE, "series.json"),
                                               encoding="utf-8"))}
cand = json.load(open(os.path.join(HERE, "candidates.json"), encoding="utf-8"))
picks = json.load(open(os.path.join(HERE, "picks.json"), encoding="utf-8"))

wj = json.load(open(os.path.join(ROOT, "wallpapers.json"), encoding="utf-8"))
cats = wj["categories"]
tags_idx = wj["tags"]
existing_ids = {e["id"] for lst in cats.values() for e in lst}
existing_urls = set()
for lst in cats.values():
    for e in lst:
        for k in ("full", "thumb", "alt"):
            if e.get(k):
                existing_urls.add(e[k])

added, per_series = [], {}
for p in picks:
    slug, idx, cat = p["slug"], int(p["i"]), p["cat"]
    meta = SERIES[slug]
    entry_meta = None
    for c in cand.get(slug, []):
        if c["i"] == idx:
            entry_meta = c
            break
    if not entry_meta:
        print("MISSING candidate %s/%s" % (slug, idx))
        continue
    url = entry_meta["full"]
    if url in existing_urls:
        print("SKIP duplicate url", url)
        continue
    wid = "wpx" + hashlib.md5(url.encode()).hexdigest()[:10]
    if wid in existing_ids:
        print("SKIP duplicate id", wid)
        continue
    try:
        r = requests.get(url, headers=UA, timeout=120)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im.load()
        im = im.convert("RGB")
    except Exception as e:
        print("SKIP download %s: %s" % (url, e))
        continue
    if im.width < 900 or im.height < 1500:
        print("SKIP small", im.size)
        continue
    full = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS, centering=(0.5, 0.5))
    os.makedirs(os.path.join(ROOT, cat), exist_ok=True)
    full.save(os.path.join(ROOT, cat, wid + ".jpg"), "JPEG", quality=95,
              optimize=True, progressive=True)
    full.resize((360, 640), Image.LANCZOS).save(
        os.path.join(ROOT, cat, wid + "_thumb.jpg"), "JPEG", quality=80,
        optimize=True, progressive=True)

    tl = [meta["series"], meta["alias"]]
    tl += [t.strip().lower() for t in p.get("tags", "").split(",") if t.strip()]
    out, seen_t = [], set()
    for t in tl:
        t = " ".join(t.split())
        if t and t not in seen_t:
            seen_t.add(t)
            out.append(t)
    out = out[:15]
    entry = {
        "id": wid,
        "thumb": "%s/%s/%s_thumb.jpg" % (RAW, cat, wid),
        "full": "%s/%s/%s.jpg" % (RAW, cat, wid),
        "alt": "%s/%s/%s.jpg" % (RAW, cat, wid),
        "tags": ",".join(out),
        "date": TODAY,
    }
    cats[cat].insert(0, entry)
    for t in out:
        tags_idx.setdefault(t, [])
        if wid not in tags_idx[t]:
            tags_idx[t].insert(0, wid)
    existing_ids.add(wid)
    existing_urls.add(entry["full"])
    added.append(wid)
    per_series[slug] = per_series.get(slug, 0) + 1
    print("ADDED %s %s %s" % (wid, cat, ",".join(out[:6])))

wj["version"] = int(wj.get("version", 0)) + 1
wj["last_updated"] = TODAY
json.dump(wj, open(os.path.join(ROOT, "wallpapers.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("\nDONE added %d wallpapers" % len(added))
for k, v in sorted(per_series.items(), key=lambda x: -x[1]):
    print("  %-12s %d" % (k, v))

# tidy temp artefacts
import shutil
for d in ("cand", "sheets"):
    shutil.rmtree(os.path.join(HERE, d), ignore_errors=True)
for f in ("candidates.json", "picks.json"):
    try:
        os.remove(os.path.join(HERE, f))
    except OSError:
        pass
