#!/usr/bin/env python3
"""Probe which image sources respond from an Actions runner."""
import json, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/plain,*/*"}

SERIES = {
    "quintessential quintuplets": "gotoubun_no_hanayome",
    "a silent voice": "koe_no_katachi",
    "food wars": "shokugeki_no_souma",
    "natsume yuujinchou": "natsume_yuujinchou",
    "yona of the dawn": "akatsuki_no_yona",
    "oregairu": "yahari_ore_no_seishun_love_comedy_wa_machigatteiru",
    "the wind rises": "kaze_tachinu",
    "jigokuraku": "jigokuraku",
    "kuroko no basket": "kuroko_no_basuke",
    "fire force": "enen_no_shouboutai",
    "akame ga kill": "akame_ga_kiru",
    "k-on": "k-on!",
    "horimiya": "horimiya",
    "wind breaker": "wind_breaker",
    "tokyo revengers": "tokyo_revengers",
    "solo leveling": "solo_leveling",
}

SOURCES = {
    "konachan.net": ("https://konachan.net/post.json", lambda t: {"tags": t, "limit": 100}),
    "konachan.com": ("https://konachan.com/post.json", lambda t: {"tags": t, "limit": 100}),
    "yande.re": ("https://yande.re/post.json", lambda t: {"tags": t, "limit": 100}),
    "safebooru.org": ("https://safebooru.org/index.php",
                      lambda t: {"page": "dapi", "s": "post", "q": "index", "tags": t, "limit": 100, "json": 1}),
    "gelbooru": ("https://gelbooru.com/index.php",
                 lambda t: {"page": "dapi", "s": "post", "q": "index", "tags": t, "limit": 100, "json": 1}),
    "safebooru.donmai": ("https://safebooru.donmai.us/posts.json", lambda t: {"tags": t, "limit": 100}),
    "wallhaven": ("https://wallhaven.cc/api/v1/search",
                  lambda t: {"q": t.replace("_", " "), "categories": "010", "purity": "100", "atleast": "1080x1500"}),
    "danbooru": ("https://danbooru.donmai.us/posts.json", lambda t: {"tags": t, "limit": 100}),
}


def probe(name, tag):
    url, params = SOURCES[name]
    try:
        r = requests.get(url, params=params(tag), headers=UA, timeout=25)
        st = r.status_code
        if st != 200:
            return st, -1, ""
        js = r.json()
        if isinstance(js, dict):
            for k in ("post", "data", "results"):
                if k in js:
                    js = js[k]
                    break
        if not isinstance(js, list):
            return st, -2, str(js)[:80]
        sample = ""
        if js:
            p = js[0]
            sample = "|".join(sorted(p.keys()))[:120] if isinstance(p, dict) else type(p).__name__
        return st, len(js), sample
    except Exception as e:
        return type(e).__name__, -1, ""


for s in SOURCES:
    st, n, sample = probe(s, "gotoubun_no_hanayome")
    print("SRC %-18s %s n=%s %s" % (s, st, n, sample), flush=True)
    time.sleep(0.5)

print("---- per-series counts", flush=True)
for s in SOURCES:
    st, n, _ = probe(s, "gotoubun_no_hanayome")
    if st != 200 or n <= 0:
        continue
    line = []
    for app, tag in SERIES.items():
        st2, n2, _ = probe(s, tag)
        line.append("%s=%s%s" % (app, n2, "" if st2 == 200 else "(%s)" % st2))
        time.sleep(0.4)
    print("SERIES %s :: %s" % (s, "; ".join(line)), flush=True)
