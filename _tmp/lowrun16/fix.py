#!/usr/bin/env python3
"""Low-count run 2026-11-16: drop the few weak / mis-tagged entries and normalise version."""
import json, os, subprocess

REMOVE = {
    "wpx8a1adca144": "image is not Oshi no Ko art (mis-tagged upload)",
    "wpx1fbe6d0e32": "flat screencap-style, low effort",
    "wpx77835eca4e": "flat screencap-style close-up, low effort",
}
TODAY = "2026-11-16"

data = json.load(open("wallpapers.json", encoding="utf-8"))
removed = 0
for cat, items in data["categories"].items():
    keep = []
    for e in items:
        if e["id"] in REMOVE:
            removed += 1
            for p in ("%s/%s.jpg" % (cat, e["id"]), "%s/%s_thumb.jpg" % (cat, e["id"])):
                if os.path.exists(p):
                    os.remove(p)
            for tg in e.get("tags", "").split(","):
                tg = tg.strip()
                if tg in data["tags"] and e["id"] in data["tags"][tg]:
                    data["tags"][tg].remove(e["id"])
                    if not data["tags"][tg]:
                        del data["tags"][tg]
        else:
            keep.append(e)
    data["categories"][cat] = keep

counts = {}
for cat, items in data["categories"].items():
    for e in items:
        if e.get("date") == TODAY:
            first = e["tags"].split(",")[0]
            counts[first] = counts.get(first, 0) + 1
total = sum(counts.values())

data["version"] = 72
data["last_updated"] = TODAY
json.dump(data, open("wallpapers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

print("removed", removed, "remaining new", total, counts, flush=True)
subprocess.run(["git", "add", "-A"], check=True)
msg = "Wallpaper top-up - %s (%d new across %d series)" % (TODAY, total, len(counts))
subprocess.run(["git", "-c", "user.name=AniPix Bot", "-c", "user.email=nobelfamily537@gmail.com",
                "commit", "-m", msg], check=True)
subprocess.run(["git", "push"], check=True)
print("PUSHED:", msg, flush=True)
