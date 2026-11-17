#!/usr/bin/env python3
import json, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
S = requests.Session()
S.headers.update(UA)

NAMES = ["initial d", "ponyo", "apothecary diaries", "nausicaa", "howls moving castle",
         "seven deadly sins", "girls band cry", "detective conan", "eminence in shadow", "haikyuu",
         "overlord", "akame ga kill", "hunter x hunter", "weathering with you", "bleach",
         "cyberpunk edgerunners", "death note", "heavenly delusion", "serial experiments lain",
         "wind breaker", "dandadan", "fullmetal alchemist", "psycho pass", "tokyo revengers",
         "classroom of the elite", "dungeon meshi", "nisekoi", "sword art online", "sailor moon",
         "kaiju no 8", "konosuba", "oshi no ko", "fairy tail", "tokyo ghoul"]

for n in NAMES:
    tot = 0
    titles = []
    for page in (1, 2):
        try:
            r = S.get("https://wallhaven.cc/api/v1/search",
                      params={"q": n, "purity": "100", "categories": "010", "sorting": "relevance",
                              "page": page}, timeout=30)
            js = r.json()
        except Exception as e:
            print("%-22s ERR %s" % (n, type(e).__name__), flush=True)
            break
        data = js.get("data", [])
        tot += len(data)
        for p in data[:3]:
            titles.append("%s/%s" % (p.get("dimension_x"), p.get("dimension_y")))
        if len(data) < 24:
            break
        time.sleep(1)
    print("%-22s n=%d  %s" % (n, tot, " ".join(titles[:4])), flush=True)
    time.sleep(1)
