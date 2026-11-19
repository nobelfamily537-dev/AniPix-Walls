#!/usr/bin/env python3
import json, time, requests
UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
TAGS = ["vinland_saga", "mashle", "eighty_six_(anime)", "enen_no_shouboutai", "kusuriya_no_hitorigoto",
        "yakusoku_no_neverland", "boku_dake_ga_inai_machi", "to_aru_kagaku_no_railgun", "god_eater",
        "kurenai_no_buta", "gake_no_ue_no_ponyo", "hajime_no_ippo", "chiikawa", "neko_no_onggaeshi",
        "kokuriko-zaka_kara", "kaze_tachinu", "gedo_senki", "86_(anime)", "horimiya"]
for t in TAGS:
    try:
        c = requests.get("https://danbooru.donmai.us/counts/posts.json",
                         params={"tags": t + " rating:g"}, headers=UA, timeout=30)
        cnt = c.json().get("counts", {}).get("posts") if c.status_code == 200 else c.status_code
        r = requests.get("https://danbooru.donmai.us/posts.json",
                         params={"tags": t + " rating:g", "limit": 3, "only": "id,image_width,image_height,file_url,large_file_url,score,tag_string_copyright,tag_string_character"},
                         headers=UA, timeout=30)
        js = r.json() if r.status_code == 200 else []
        s = ""
        if js:
            p = js[0]
            s = "%sx%s score=%s %s | %s" % (p.get("image_width"), p.get("image_height"), p.get("score"),
                                            (p.get("tag_string_copyright") or "")[:40],
                                            (p.get("large_file_url") or p.get("file_url") or "")[:60])
        print("%-28s count=%-6s posts=%s %s" % (t, cnt, len(js), s), flush=True)
    except Exception as e:
        print("%-28s ERR %s %s" % (t, type(e).__name__, e), flush=True)
    time.sleep(1.2)
