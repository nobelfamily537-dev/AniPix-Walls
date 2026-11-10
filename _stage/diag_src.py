import json, urllib.request, urllib.parse, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
WH = "https://wallhaven.cc/api/v1/search"
GB = "https://gelbooru.com/index.php"
KON = "https://konachan.net/post.json"

SERIES = [("sailor moon", "sailor moon", "sailor_moon"),
          ("howls moving castle", "howl's moving castle", "howl's_moving_castle"),
          ("my neighbor totoro", "totoro", "tonari_no_totoro"),
          ("nausicaa", "nausicaa", "kaze_no_tani_no_nausicaa"),
          ("clannad", "clannad", "clannad"),
          ("fullmetal alchemist", "fullmetal alchemist", "fullmetal_alchemist"),
          ("berserk", "berserk", "berserk"),
          ("fairy tail", "fairy tail", "fairy_tail"),
          ("bleach", "bleach", "bleach"),
          ("neon genesis evangelion", "evangelion", "neon_genesis_evangelion")]


def get(url, timeout=45):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


out = {}
for tag, whq, kontag in SERIES:
    row = {}
    # wallhaven loose
    try:
        qs = urllib.parse.urlencode({"q": whq, "ratios": "portrait", "categories": "100",
                                     "purity": "100", "sorting": "relevance", "page": 1})
        j = json.loads(get(WH + "?" + qs))
        data = j.get("data", [])
        port = [d for d in data if int(d["dimension_y"]) / max(int(d["dimension_x"]), 1) >= 1.5]
        row["wh"] = {"n": len(data), "portrait15": len(port),
                     "sample": data[0]["path"] if data else None}
    except Exception as e:
        row["wh"] = {"err": str(e)[:80]}
    # gelbooru
    try:
        qs = urllib.parse.urlencode({"page": "dapi", "s": "post", "q": "index", "json": "1",
                                     "tags": kontag, "limit": 20})
        j = json.loads(get(GB + "?" + qs))
        posts = j.get("post", []) if isinstance(j, dict) else []
        row["gb"] = {"n": len(posts), "sample": posts[0].get("file_url") if posts else None}
    except Exception as e:
        row["gb"] = {"err": str(e)[:80]}
    # konachan ordered by score
    try:
        qs = urllib.parse.urlencode({"tags": kontag + " order:score", "limit": 100, "page": 1})
        posts = json.loads(get(KON + "?" + qs))
        port = [p for p in posts if p.get("rating") == "s" and int(p["height"]) / max(int(p["width"]), 1) >= 1.4]
        row["kon"] = {"n": len(posts), "portrait": len(port)}
    except Exception as e:
        row["kon"] = {"err": str(e)[:80]}
    out[tag] = row

json.dump(out, open("_stage/diag_src.json", "w"), indent=1)
print(json.dumps(out)[:1200])
