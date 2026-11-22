#!/usr/bin/env python3
"""Auto-tag untagged wallpapers with the WD14 anime tagger (ONNX, runs on CPU).

Env:
  LIMIT        max images to tag this run (default 300)
  THRESHOLD    min probability for a tag (default 0.35)
  MAXTAGS      max tags kept per image (default 15)
  CATEGORIES   comma list to restrict (default: all)
"""
import os, io, json, csv, sys, tempfile, urllib.request
import numpy as np
from PIL import Image
import onnxruntime as ort

MODEL = "https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3/resolve/main/model.onnx"
LABELS = "https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3/resolve/main/selected_tags.csv"

LIMIT = int(os.environ.get("LIMIT", "300"))
THR = float(os.environ.get("THRESHOLD", "0.35"))
MAXT = int(os.environ.get("MAXTAGS", "15"))
CATS = [c.strip() for c in os.environ.get("CATEGORIES", "").split(",") if c.strip()]

WJ = "wallpapers.json"
data = json.load(open(WJ, encoding="utf-8"))
data.setdefault("tags", {})


def dl(url, path):
    if not os.path.exists(path):
        print("downloading", os.path.basename(path), "...")
        urllib.request.urlretrieve(url, path)
    return path


MD = tempfile.mkdtemp()
M = dl(MODEL, os.path.join(MD, "model.onnx"))
L = dl(LABELS, os.path.join(MD, "selected_tags.csv"))

# labels
names, kinds = [], []
with open(L, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        names.append(row["name"])
        kinds.append(int(row.get("category", 0)))

sess = ort.InferenceSession(M, providers=["CPUExecutionProvider"])
inp = sess.get_inputs()[0]
_, H, W, _ = inp.shape
print("model input:", inp.shape)

def prepare(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(bg, im).convert("RGB")
    im = im.resize((W, H), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float32)[:, :, ::-1]  # BGR
    return np.expand_dims(a, 0)

def tag(path):
    out = sess.run(None, {inp.name: prepare(path)})[0][0]
    keep = []
    for i, p in enumerate(out):
        if kinds[i] == 9:      # rating tags - skip
            continue
        if p >= THR:
            keep.append((float(p), names[i].replace("_", " ")))
    keep.sort(reverse=True)
    return [n for _, n in keep[:MAXT]]


# gather untagged entries (in any requested category)
todo = []
for cat, arr in data["categories"].items():
    if CATS and cat not in CATS:
        continue
    for e in arr:
        if not e.get("tags") and e.get("thumb"):
            todo.append((cat, e))
print(f"untagged entries: {len(todo)}  (limit {LIMIT})")
todo = todo[:LIMIT]

import tempfile, urllib.request as u2
done = 0
for cat, e in todo:
    try:
        url = e["full"] or e["thumb"]
        rq = u2.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"})
        raw = u2.urlopen(rq, timeout=60).read()
        tmp = os.path.join(tempfile.gettempdir(), "t.jpg")
        open(tmp, "wb").write(raw)
        tags = tag(tmp)
        if not tags:
            continue
        e["tags"] = ",".join(tags)
        for t in tags:
            data["tags"].setdefault(t, [])
            if e["id"] not in data["tags"][t]:
                data["tags"][t].insert(0, e["id"])
        done += 1
        if done % 25 == 0:
            print(f"  tagged {done}...")
    except Exception as ex:
        print("skip", e["id"], ex)

json.dump(data, open(WJ, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"\nDONE: tagged {done} wallpapers")
