#!/usr/bin/env python3
"""Probe konachan tag availability + aspect ratio distribution for gap series."""
import json, re, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

TAGS = ["jojo_no_kimyou_na_bouken", "kujo_jotaro", "dio_brando", "giorno_giovanna", "jolyne_cujoh",
        "stone_ocean", "golden_wind", "vento_aureo", "higashikata_josuke",
        "tengen_toppa_gurren_lagann", "yoko_littner", "kamina", "nia_teppelin",
        "fruits_basket", "honda_tohru", "sohma_kyo", "sohma_yuki",
        "seishun_buta_yarou", "sakurajima_mai", "azusagawa_sakuta",
        "yahari_ore_no_seishun_love_comedy_wa_machigatteiru", "yukinoshita_yukino", "yuigahama_yui",
        "chihayafuru", "ayase_chihaya", "vivy_fluorite_eye_s_song", "shiguang_dailiren",
        "higurashi_no_naku_koro_ni", "ryuuguu_rena", "akatsuki_no_yona", "yona_(akatsuki_no_yona)",
        "kiseijuu", "parasyte", "mushishi", "dororo", "another_(anime)", "devilman_crybaby",
        "sakamichi_no_apollon", "ping_pong_the_animation", "haibane_renmei", "monster_(manga)",
        "kanon", "air_(visual_novel)", "clannad", "ef_(visual_novel)", "white_album",
        "nagi_no_asukara", "sakurasou_no_pet_na_kanojo", "shinmai_fukei_no_testament",
        "grand_blue", "kaguya-sama_wa_kokurasetai", "isekai_ojisan", "sousou_no_frieren"]


def get(url, params, timeout=25):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        print("  HTTP", r.status_code, params.get("tags"), flush=True)
    except Exception as e:
        print("  ERR", type(e).__name__, params.get("tags"), flush=True)
    return None


for t in TAGS:
    js = get("https://konachan.net/post.json", {"tags": t + " rating:s", "limit": 100})
    if not js:
        continue
    port = land = 0
    for p in js:
        w, h = p.get("width") or 0, p.get("height") or 0
        if not w or not h:
            continue
        r = h / w
        if r >= 1.2:
            port += 1
        elif r <= 0.8:
            land += 1
    print("%-55s n=%3d portrait=%3d landscape=%3d" % (t, len(js), port, land), flush=True)
    time.sleep(0.4)
