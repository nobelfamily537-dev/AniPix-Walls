#!/usr/bin/env python3
"""Remove watermarked/signature images from today's batch, then clean temp files."""
import os, json, subprocess, shutil, glob
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).strftime("%Y-%m-%d")

DROP = ["wpxf43b782359", "wpxdce5d96998", "wpxeeda7e1b99", "wpx3f42861b45",
        "wpx34841d63e1", "wpx7273d120f5", "wpx7dd0f3dc42", "wpx071b04c3ee",
        "wpxbccf0b9e19", "wpxb4ffe1a45b", "wpx5759497e5b", "wpx4f4ad326c5"]


def git(*a):
    subprocess.run(["git"] + list(a), check=True)


git("config", "user.email", "nobelfamily537@gmail.com")
git("config", "user.name", "AniPix Bot")

data = json.load(open("wallpapers.json", encoding="utf-8"))
removed = 0
for wid in DROP:
    for cat, lst in data["categories"].items():
        keep = [e for e in lst if e["id"] != wid]
        if len(keep) != len(lst):
            data["categories"][cat] = keep
            for suf in (".jpg", "_thumb.jpg"):
                p = f"{cat}/{wid}{suf}"
                if os.path.exists(p):
                    os.remove(p)
            removed += 1
    for t in list(data["tags"].keys()):
        if wid in data["tags"][t]:
            data["tags"][t] = [i for i in data["tags"][t] if i != wid]
            if not data["tags"][t]:
                del data["tags"][t]

data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
git("add", "-A", "wallpapers.json", "anime", "anime2", "game")
git("commit", "-m", "Drop 12 watermarked images from 2026-11-14 low-count top-up")
for _ in range(4):
    try:
        git("push", "origin", "main")
        break
    except subprocess.CalledProcessError:
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
print("removed", removed)

# ---- clean temp artefacts ----
for p in glob.glob("_tmp/lowrun*") + glob.glob(".github/workflows/lowrun-*.yml") + \
        ["_tmp/prior_ids.txt", "_tmp/probe_write.txt"]:
    if os.path.isdir(p):
        shutil.rmtree(p)
    elif os.path.exists(p):
        os.remove(p)
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "chore: remove low-count run temp files"], check=False)
for _ in range(4):
    try:
        git("push", "origin", "main")
        break
    except subprocess.CalledProcessError:
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
print("cleanup done")
