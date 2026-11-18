import json, requests
UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
TAGS = ["dandadan", "horimiya", "vinland_saga", "sen_to_chihiro_no_kamikakushi", "gintama",
        "mob_psycho_100", "hajime_no_ippo", "trigun", "cowboy_bebop", "code_geass",
        "k-on!", "natsume_yuujinchou", "sakamoto_days", "gedo_senki", "neko_no_onggaeshi",
        "gake_no_ue_no_ponyo", "tenkuu_no_shiro_laputa", "cardcaptor_sakura"]
SITES = ["https://safebooru.donmai.us", "https://danbooru.donmai.us"]
for base in SITES:
    for t in TAGS:
        row = []
        for q in (t, t + " rating:g", t + " rating:g score:>5"):
            try:
                r = requests.get(base + "/counts/posts.json", params={"tags": q}, headers=UA, timeout=30)
                row.append("%s=%s" % (q.replace(t, "*"), r.json().get("counts", {}).get("posts", "?")))
            except Exception as e:
                row.append("%s=ERR:%s" % (q.replace(t, "*"), type(e).__name__))
        print("%-30s %-38s %s" % (base.split("//")[1], t, "  ".join(row)), flush=True)
r = requests.get("https://danbooru.donmai.us/posts.json", params={"tags": "dandadan rating:g", "limit": 2}, headers=UA, timeout=30)
js = r.json()
print("danbooru sample status", r.status_code, "n", len(js))
if js:
    print("keys:", sorted(js[0].keys()))
    print("sample:", {k: js[0].get(k) for k in ("id", "file_url", "sample_url", "image_width", "image_height", "score", "rating")})
r = requests.get("https://safebooru.donmai.us/posts.json", params={"tags": "dandadan", "limit": 2}, headers=UA, timeout=30)
js = r.json()
print("safebooru sample status", r.status_code, "n", len(js))
if js:
    print("sample:", {k: js[0].get(k) for k in ("id", "file_url", "sample_url", "image_width", "image_height", "score", "rating")})
