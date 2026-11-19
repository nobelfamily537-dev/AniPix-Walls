#!/usr/bin/env python3
import json, time, requests
UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation)"}
TAGS = """86_-_eighty_six-
86_(anime)
eighty_six
vladilena_milize
mashle
mashle:_magic_and_muscles
mash_burnedead
vinland_saga
thorfinn_(vinland_saga)
chiikawa
chiikawa_(anime)
kaze_tachinu
kokuriko-zaka_kara
neko_no_onggaeshi
kurenai_no_buta
gedo_senki
gake_no_ue_no_ponyo
yakusoku_no_neverland
hajime_no_ippo
god_eater
enen_no_shouboutai
horimiya
hori-san_to_miyamura-kun
kusuriya_no_hitorigoto
to_aru_kagaku_no_railgun
boku_dake_ga_inai_machi
sousou_no_frieren
blue_box
dandadan
kaiju_no._8
sakamoto_days
""".split()
res = {}
for t in TAGS:
    for site in ("https://konachan.net", "https://yande.re"):
        try:
            r = requests.get(site + "/tag.json", params={"name": t, "limit": 1}, headers=UA, timeout=30)
            js = r.json()
            res[t + " @" + site.split("//")[1]] = js[0]["count"] if js else 0
        except Exception as e:
            res[t + " @" + site.split("//")[1]] = "ERR " + type(e).__name__
        time.sleep(0.5)
print(json.dumps(res, indent=1))
