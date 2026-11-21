#!/usr/bin/env python3
"""Probe source availability per series (no downloads)."""
import json, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SERIES = [
    ("god eater", ["god_eater"], ["god eater", "alisa illinchina"]),
    ("initial d", ["initial_d", "fujiwara_takumi"], ["initial d", "ae86"]),
    ("soul eater", ["soul_eater", "maka_albarn"], ["soul eater", "maka albarn"]),
    ("seven deadly sins", ["nanatsu_no_taizai", "meliodas"], ["seven deadly sins", "nanatsu no taizai"]),
    ("clannad", ["clannad", "furukawa_nagisa"], ["clannad", "nagisa furukawa"]),
    ("kaiju no. 8", ["kaijuu_8-gou", "hibino_kafka"], ["kaiju no 8", "kaiju no. 8"]),
    ("princess mononoke", ["mononoke_hime", "san_(mononoke_hime)"], ["princess mononoke", "mononoke hime"]),
    ("black clover", ["black_clover", "asta_(black_clover)"], ["black clover", "asta black clover"]),
    ("dungeon meshi", ["dungeon_meshi", "marcille_donato"], ["dungeon meshi", "delicious in dungeon"]),
    ("nausicaa", ["kaze_no_tani_no_nausicaa"], ["nausicaa", "valley of the wind"]),
    ("touhou project", ["touhou", "hakurei_reimu"], ["touhou", "reimu hakurei"]),
    ("cyberpunk edgerunners", ["cyberpunk:_edgerunners", "lucy_(cyberpunk)"], ["cyberpunk edgerunners", "lucy cyberpunk"]),
]


def get(url, params, timeout=20):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        time.sleep(1.0)
        return r
    except Exception as e:
        print("  ERR", type(e).__name__, flush=True)
        return None


def wh(q, extra):
    p = {"q": q, "categories": "010", "purity": "100", "sorting": "favorites"}
    p.update(extra)
    r = get("https://wallhaven.cc/api/v1/search", p)
    if not r or r.status_code != 200:
        return -1, 0
    try:
        js = r.json()
    except Exception:
        return -1, 0
    data = js.get("data", [])
    tall = sum(1 for d in data if d["dimension_y"] / d["dimension_x"] >= 1.25)
    return len(data), tall


def yande(tag):
    r = get("https://yande.re/post.json", {"tags": "%s rating:safe score:>10" % tag, "limit": 100})
    if not r or r.status_code != 200:
        return -1, 0, 0
    try:
        arr = r.json()
    except Exception:
        return -1, 0, 0
    tall = [p for p in arr if p.get("height") and p.get("width") and p["height"] / p["width"] >= 1.25
            and p["height"] >= 1400]
    good = [p for p in tall if (p.get("score") or 0) > 40]
    return len(arr), len(tall), len(good)


for name, ytags, wqs in SERIES:
    out = {"series": name}
    for q in wqs:
        n1, t1 = wh(q, {"atleast": "1080x1500", "ratios": "9x16,10x16,2x3,3x4"})
        n2, t2 = wh(q, {"atleast": "1080x1500"})
        out[q] = {"wh_portrait": n1, "wh_portrait_tall": t1, "wh_any": n2, "wh_any_tall": t2}
    for t in ytags:
        a, b, c = yande(t)
        out[t] = {"yande": a, "yande_tall": b, "yande_tall_score40": c}
    print(json.dumps(out), flush=True)
print("PROBE DONE", flush=True)
