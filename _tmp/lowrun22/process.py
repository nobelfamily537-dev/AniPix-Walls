#!/usr/bin/env python3
"""Low-count run 22 - stage 2: process approved candidates into final wallpapers + JSON."""
import os, io, json, time, re, hashlib
import requests
from PIL import Image, ImageStat

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://konachan.net/"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
TODAY = os.environ.get("TODAY", "2026-11-22")

META = {"1boy","1girl","2boys","2girls","3girls","multiple_boys","multiple_girls","solo","solo_focus",
 "highres","absurdres","lowres","huge_filesize","incredibly_absurdres","male_focus","female_focus",
 "commentary_request","commentary","translated","bad_id","bad_pixiv_id","bad_twitter_id",
 "artist_name","watermark","signature","text","english_text","character_request","anonymous",
 "scenery","no_humans","absurdres_","upscaled","ai_assisted","ai-generated","censored","monochrome",
 "greyscale","partially_colored","crop","border","letterboxed","wide_image","official_art","scan",
 "sketch","lineart","chibi","comic","4koma","manga","doujin","crossover","alternate_costume",
 "alternate_hairstyle","alternate_eyes","official_art_","promotional_art","game_cg","anime_screencap",
 "screencap","screenshot","photo","photograph","cosplay","real_life","3d","realistic","vector"}

COLORS = [("blue","blue theme"),("red","red theme"),("pink","pink theme"),("purple","purple theme"),
          ("green","green theme"),("orange","orange theme"),("yellow","yellow theme"),
          ("white","white theme"),("black","black theme"),("teal","teal theme"),("gold","gold theme")]


def avg_color(im):
    st = ImageStat.Stat(im.resize((60, 106)))
    r, g, b = st.mean
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 55:
        return "black theme"
    if mn > 195:
        return "white theme"
    if mx - mn < 22:
        return "grey theme"
    if r == mx and g > b * 1.25 and r > 120:
        return "orange theme" if g < r * 0.78 else "yellow theme"
    if r == mx and b > g * 1.1:
        return "pink theme" if g < r * 0.72 else "purple theme"
    if b == mx and r > g * 1.2:
        return "purple theme"
    if b == mx:
        return "blue theme"
    if g == mx:
        return "green theme"
    return "blue theme"


def clean_tag(t):
    t = t.replace("_", " ").strip()
    t = re.sub(r"\s+", " ", t)
    return t


def build_tags(entry, series_tags, alt_tags):
    raw = entry["tags"].split()
    keep = []
    for t in raw:
        if t in META:
            continue
        if re.search(r"(text|watermark|signature|logo|commentary|_id$|username|web_address|dated)", t):
            continue
        if len(keep) < 8:
            keep.append(clean_tag(t))
    out = list(series_tags) + list(alt_tags)
    for k in keep:
        if k and k not in out:
            out.append(k)
    out.append(entry["color"])
    out.append("anime")
    out.append("portrait")
    # dedupe, cap 15
    seen, fin = set(), []
    for t in out:
        t = t.strip().lower()
        if t and t not in seen:
            seen.add(t)
            fin.append(t)
    return ",".join(fin[:15])


def render(im):
    w, h = im.size
    t = 1920 / 1080
    r = h / w
    if r > t:
        nw = int(h / t)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:
        nh = int(w * t)
        y = int((h - nh) * 0.45)
        im = im.crop((0, y, w, y + nh))
    return im.resize((1080, 1920), Image.LANCZOS)


approved = json.load(open("_tmp/lowrun22/approved.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))
existing_ids = {e["id"] for c in data["categories"].values() for e in c}
existing_full = {e["full"] for c in data["categories"].values() for e in c}
added = 0
report = {}

for a in approved:
    cat = a["category"]
    os.makedirs(cat, exist_ok=True)
    try:
        r = requests.get(a["url"], headers=UA, timeout=60)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print("dl fail", a.get("pid"), type(e).__name__, flush=True)
        continue
    im = render(im)
    color = avg_color(im)
    a["color"] = color
    wid = "wpx" + hashlib.sha1((str(a["pid"]) + a["site"] + a["series"]).encode()).hexdigest()[:10]
    if wid in existing_ids:
        continue
    full_url = f"{RAW}/{cat}/{wid}.jpg"
    if full_url in existing_full:
        continue
    im.save(f"{cat}/{wid}.jpg", "JPEG", quality=95, optimize=True, progressive=True)
    im.resize((360, 640), Image.LANCZOS).save(f"{cat}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True)
    tags = build_tags(a, a["series_tags"], a.get("alt_tags", []))
    entry = {"id": wid, "thumb": f"{RAW}/{cat}/{wid}_thumb.jpg", "full": full_url,
             "alt": full_url, "tags": tags, "date": TODAY}
    data["categories"][cat].append(entry)
    existing_ids.add(wid)
    existing_full.add(full_url)
    for t in tags.split(","):
        data["tags"].setdefault(t, []).append(wid)
    added += 1
    report[a["series"]] = report.get(a["series"], 0) + 1

data["version"] = int(data.get("version", 100)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ADDED", added, json.dumps(report), flush=True)
