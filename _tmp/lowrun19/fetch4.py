#!/usr/bin/env python3
"""Low-count run (17:00 IST, 2026-11-17) stage 1d: Pinterest search candidates + sheets."""
import io, json, os, re, time
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9"}

SERIES = [
    ("hyouka",            ["hyouka anime wallpaper"]),
    ("rurouni kenshin",   ["rurouni kenshin wallpaper"]),
    ("toradora",          ["toradora anime wallpaper"]),
    ("trigun",            ["trigun stampede wallpaper"]),
    ("hajime no ippo",    ["hajime no ippo wallpaper"]),
    ("digimon",           ["digimon anime wallpaper"]),
    ("code geass",        ["code geass wallpaper"]),
    ("cowboy bebop",      ["cowboy bebop wallpaper"]),
    ("fire force",        ["fire force anime wallpaper"]),
    ("horimiya",          ["horimiya anime wallpaper"]),
    ("noragami",          ["noragami anime wallpaper"]),
    ("your lie in april", ["your lie in april anime wallpaper"]),
    ("vinland saga",      ["vinland saga wallpaper"]),
    ("made in abyss",     ["made in abyss wallpaper"]),
    ("steins gate",       ["steins gate anime wallpaper"]),
    ("mob psycho 100",    ["mob psycho 100 wallpaper"]),
]

OUT = "_tmp/lowrun19"
PREV = os.path.join(OUT, "prev4")
SHEETS = os.path.join(OUT, "sheets4")
os.makedirs(PREV, exist_ok=True)
os.makedirs(SHEETS, exist_ok=True)
PER_SERIES = 20

IMG_RE = re.compile(r"https://i\.pinimg\.com/(")


def render(im, size=(360, 640)):
    w, h = im.size
    r = h / w
    tw, th = size
    t = 16 / 9
    if r > 2.2:
        bg = ImageOps.fit(im, (tw, th), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        fg = im.copy()
        fg.thumbnail((tw, th), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
        return bg
    if r > t:
        nh = int(w * t)
        y = int((h - nh) * 0.04)
        return im.crop((0, y, w, y + nh))
    nw = int(h / t)
    x = (w - nw) // 2
    return im.crop((x, 0, x + nw, h))


def search(q):
    urls = []
    for page in range(3):
        try:
            r = requests.get("https://www.pinterest.com/search/pins/",
                             params={"q": q}, headers=UA, timeout=45)
            if r.status_code != 200:
                print("  HTTP", r.status_code, flush=True)
                break
            found = IMG_RE.findall(r.text)
            for u in found:
                u = u.replace("/564x/", "/736x/").replace("/474x/", "/736x/")
                if u not in urls:
                    urls.append(u)
            print("   page %d html %d bytes -> %d imgs (total %d)" % (page, len(r.text), len(found), len(urls)), flush=True)
        except Exception as e:
            print("   ERR", type(e).__name__, flush=True)
            break
        if len(urls) >= 120:
            break
        time.sleep(1.5)
    return urls


cands = []
seen = set()
for name, queries in SERIES:
    pool = []
    for q in queries:
        got = search(q)
        print("  %s %r -> %d" % (name, q, len(got)), flush=True)
        pool += got
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    n = 0
    for u in pool:
        if n >= PER_SERIES:
            break
        key = u.rsplit("/", 1)[-1]
        if key in seen:
            continue
        seen.add(key)
        try:
            r = requests.get(u, headers=UA, timeout=45)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            w, h = im.size
            if h / w < 1.15 or h < 700:
                continue
            fn = "%s_%02d.jpg" % (slug, n)
            render(im).save(os.path.join(PREV, fn), "JPEG", quality=84, optimize=True)
            full = u.replace("/736x/", "/originals/")
            cands.append(dict(series=name, slug=slug, idx=n, file=fn, pid=key[:12], site="pinterest",
                              score=0, w=w, h=h, url=full, tags=""))
            n += 1
        except Exception as e:
            print("   dl err", type(e).__name__, flush=True)
        time.sleep(0.1)
    print("   previews=%d" % n, flush=True)

json.dump(cands, open(os.path.join(OUT, "cands4.json"), "w"), indent=1)

COLS, ROWS = 5, 4
CW, CH = 300, 533
per = COLS * ROWS
byseries = {}
for c in cands:
    byseries.setdefault(c["slug"], []).append(c)
for slug, items in byseries.items():
    for si in range(0, len(items), per):
        chunk = items[si:si + per]
        sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for k, c in enumerate(chunk):
            im = Image.open(os.path.join(PREV, c["file"])).convert("RGB").resize((CW, CH), Image.LANCZOS)
            x, y = (k % COLS) * CW, (k // COLS) * CH
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 34, y + 20], fill=(0, 0, 0))
            dr.text((x + 5, y + 5), str(c["idx"]), fill=(255, 255, 0))
        sheet.save(os.path.join(SHEETS, "%s_%d.jpg" % (slug, si // per)), "JPEG", quality=86, optimize=True)

print("TOTAL candidates", len(cands), flush=True)
print("sheets:", sorted(os.listdir(SHEETS)), flush=True)
