#!/usr/bin/env python3
"""Low-count run 22 - stage 2: build final wallpapers and update wallpapers.json."""
import os, io, json, time, re, hashlib
import requests
from PIL import Image, ImageStat

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://wallhaven.cc/"}
RAW = "https://raw.githubusercontent.com/nobelfamily537-dev/AniPix-Walls/main"
TODAY = os.environ.get("TODAY", "2026-11-22")
META = {"1boy","1girl","2boys","2girls","3girls","multiple_boys","multiple_girls","solo","solo_focus",
 "highres","absurdres","lowres","huge_filesize","incredibly_absurdres","male_focus","female_focus",
 "commentary_request","commentary","translated","bad_id","artist_name","watermark","signature","text",
 "english_text","character_request","anonymous","scenery","no_humans","upscaled","ai_assisted",
 "censored","monochrome","greyscale","partially_colored","crop","border","letterboxed","wide_image",
 "official_art","scan","sketch","lineart","chibi","comic","4koma","manga","doujin","crossover",
 "alternate_costume","alternate_hairstyle","alternate_eyes","promotional_art","game_cg","screencap",
 "screenshot","photo","photograph","cosplay","real_life","3d","realistic","vector","ai-generated",
 "minimalistic","silhouette","back","profile","from_behind","from_side","looking_at_viewer","looking_away",
 "portrait","close-up","upper_body","cowboy_shot","full_body"}


def avg_color(im):
    st = ImageStat.Stat(im.resize((48, 85)))
    r, g, b = st.mean
    mx, mn = max(r, g, b), min(r, g, b)
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


def build_tags(entry, color):
    out = []
    for t in list(entry["series_tags"]) + list(entry["alt_tags"]):
        out.append(t.strip().lower())
    for t in entry["tags"].split():
        t = t.replace("_", " ").strip()
        if not t or t in META:
            continue
        if re.search(r"(text|watermark|signature|logo|commentary|_id$|username|web address|dated|http)", t):
            continue
        out.append(t)
    out.append(color)
    out.append("portrait")
    seen, fin = set(), []
    for t in out:
        t = re.sub(r"\s+", " ", t).strip().lower()
        if t and t not in seen:
            seen.add(t); fin.append(t)
    # series tag must stay first
    return ",".join(fin[:15])


def render(im):
    w, h = im.size
    t = 1920 / 1080
    nw = min(w, int(h / t))
    x = (w - nw) // 2
    im = im.crop((x, 0, x + nw, h))
    return im.resize((1080, 1920), Image.LANCZOS)


approved = json.load(open("_tmp/lowrun22/approved_full.json"))
data = json.load(open("wallpapers.json", encoding="utf-8"))
existing_ids = {e["id"] for c in data["categories"].values() for e in c}
existing_full = {e["full"] for c in data["categories"].values() for e in c}
added, report = 0, {}

for a in approved:
    cat = a["category"]
    os.makedirs(cat, exist_ok=True)
    try:
        r = requests.get(a["url"], headers=UA, timeout=90)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print("dl fail", a.get("pid"), type(e).__name__, flush=True)
        continue
    if im.width < 900 or im.height < 1500:
        print("too small", a["pid"], im.size, flush=True)
        continue
    im = render(im)
    color = avg_color(im)
    wid = "wpx" + hashlib.sha1(("wh" + str(a["pid"])).encode()).hexdigest()[:10]
    if wid in existing_ids:
        continue
    full_url = f"{RAW}/{cat}/{wid}.jpg"
    if full_url in existing_full:
        continue
    im.save(f"{cat}/{wid}.jpg", "JPEG", quality=95, optimize=True, progressive=True)
    im.resize((360, 640), Image.LANCZOS).save(f"{cat}/{wid}_thumb.jpg", "JPEG", quality=80, optimize=True)
    tags = build_tags(a, color)
    entry = {"id": wid, "thumb": f"{RAW}/{cat}/{wid}_thumb.jpg", "full": full_url,
             "alt": full_url, "tags": tags, "date": TODAY}
    data["categories"][cat].append(entry)
    existing_ids.add(wid); existing_full.add(full_url)
    for t in tags.split(","):
        data["tags"].setdefault(t, []).append(wid)
    added += 1
    report[a["series"]] = report.get(a["series"], 0) + 1

data["version"] = int(data.get("version", 100)) + 1
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ADDED", added, json.dumps(report), flush=True)
print("VERSION", data["version"], flush=True)
