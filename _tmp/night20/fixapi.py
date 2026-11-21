#!/usr/bin/env python3
"""Regenerate the 20 wallpaper image pairs and commit them via the GitHub Git Data API."""
import base64, io, json, os, hashlib
import requests
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 200_000_000
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
REPO = "nobelfamily537-dev/AniPix-Walls"
TOKEN = os.environ["GITHUB_TOKEN"]
API = "https://api.github.com/repos/" + REPO
H = {"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
     "X-GitHub-Api-Version": "2022-11-28"}
OUT = "_tmp/night20"

picks = json.load(open(os.path.join(OUT, "picks.json")))
cands = {}
for fn in ("cands.json", "cands3.json", "cands4.json"):
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        for c in json.load(open(p)):
            cands[str(c["pid"])] = c

wp = requests.get("https://raw.githubusercontent.com/%s/main/wallpapers.json" % REPO, timeout=60).json()
have = {}
for cat, arr in wp["categories"].items():
    for w in arr:
        have[w["id"]] = cat

def make_id(pid):
    return "wpx" + hashlib.sha1(("night20-%s" % pid).encode()).hexdigest()[:10]

def fit(im):
    return ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS, centering=(0.5, 0.42))

made = []
for p in picks:
    pid = str(p["pid"])
    wid = make_id(pid)
    cat = p["category"]
    if wid not in have:
        print("skip (not in json)", pid, flush=True)
        continue
    c = cands.get(pid)
    if not c:
        print("skip (no cand)", pid, flush=True)
        continue
    try:
        r = requests.get(c["url"], headers=UA, timeout=90)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        final = fit(im)
        b1 = io.BytesIO(); final.save(b1, "JPEG", quality=95, optimize=True, subsampling=1)
        b2 = io.BytesIO(); final.resize((360, 640), Image.LANCZOS).save(b2, "JPEG", quality=80, optimize=True)
        made.append((cat + "/" + wid + ".jpg", b1.getvalue()))
        made.append((cat + "/" + wid + "_thumb.jpg", b2.getvalue()))
        print("made", cat, wid, len(b1.getvalue()), len(b2.getvalue()), flush=True)
    except Exception as e:
        print("FAIL", pid, type(e).__name__, e, flush=True)

print("files", len(made), flush=True)
if not made:
    raise SystemExit("nothing to upload")

ref = requests.get(API + "/git/ref/heads/main", headers=H, timeout=60).json()
head = ref["object"]["sha"]
commit = requests.get(API + "/git/commits/" + head, headers=H, timeout=60).json()
base_tree = commit["tree"]["sha"]

tree = []
for path, data in made:
    b = requests.post(API + "/git/blobs", headers=H, timeout=120,
                      json={"content": base64.b64encode(data).decode(), "encoding": "base64"})
    b.raise_for_status()
    tree.append({"path": path, "mode": "100644", "type": "blob", "sha": b.json()["sha"]})
print("blobs", len(tree), flush=True)

t = requests.post(API + "/git/trees", headers=H, timeout=120,
                  json={"base_tree": base_tree, "tree": tree})
t.raise_for_status()
c = requests.post(API + "/git/commits", headers=H, timeout=60,
                  json={"message": "Nightly wallpaper add - 2026-11-20 (20 new)",
                        "tree": t.json()["sha"], "parents": [head]})
c.raise_for_status()
u = requests.patch(API + "/git/refs/heads/main", headers=H, timeout=60,
                   json={"sha": c.json()["sha"], "force": False})
u.raise_for_status()
print("COMMIT", c.json()["sha"], flush=True)
