#!/usr/bin/env python3
"""Low20 stage A: fetch candidate metadata only (no image downloads)."""
import json, os, re, time
import requests

UA = {"User-Agent": "AniPixBot/1.0 (wallpaper curation; contact nobelfamily537@gmail.com)",
      "Accept": "application/json"}

SERIES = [
    ("ranma", "ranma", "ranma 1/2", "anime", ["ranma_1/2"], ["saotome ranma", "tendou akane"]),
    ("god eater", "god eater", None, "game", ["god_eater"], ["alisa illinichina amiella", "soma schicksal"]),
    ("ponyo", "ponyo", None, "anime", ["gake_no_ue_no_ponyo"], ["ponyo", "sousuke"]),
    ("porco rosso", "porco rosso", None, "anime", ["kurenai_no_buta"], ["porco rosso", "fio piccolo"]),
    ("bunny girl senpai", "bunny girl senpai", "rascal does not dream", "anime", ["seishun_buta_yarou"],
     ["sakurajima mai", "azusagawa sakuta"]),
    ("the wind rises", "the wind rises", "kaze tachinu", "anime", ["kaze_tachinu"], ["horikoshi jirou"]),
    ("vinland saga", "vinland saga", None, "anime", ["vinland_saga"], ["thorfinn", "askeladd"]),
    ("digimon", "digimon", "digimon adventure", "anime", ["digimon"], ["agumon", "yagami taichi"]),
    ("girls band cry", "girls band cry", None, "anime", ["girls_band_cry"], ["iseri nina", "kawaragi momoka"]),
    ("fire force", "fire force", "enen no shouboutai", "anime", ["enen_no_shouboutai"],
     ["shinra kusakabe", "tamaki kotatsu"]),
    ("noragami", "noragami", None, "anime", ["noragami"], ["yato", "iki hiyori"]),
    ("rurouni kenshin", "rurouni kenshin", None, "anime", ["rurouni_kenshin"], ["himura kenshin", "kamiya kaoru"]),
    ("kuroko no basket", "kuroko no basket", "kuroko's basketball", "anime", ["kuroko_no_basket"],
     ["kuroko tetsuya", "kagami taiga"]),
    ("jigokuraku", "jigokuraku", "hell's paradise", "anime", ["jigokuraku"], ["gabimaru", "yamada asaemon sagiri"]),
    ("made in abyss", "made in abyss", None, "anime", ["made_in_abyss"], ["riko", "reg", "nanachi"]),
    ("yu-gi-oh", "yu-gi-oh", "yugioh", "anime", ["yu-gi-oh!"], ["muto yugi", "kaiba seto"]),
    ("akame ga kill", "akame ga kill", "akame ga kiru", "anime", ["akame_ga_kill"], ["akame", "tatsumi"]),
    ("mob psycho 100", "mob psycho 100", "mob psycho", "anime", ["mob_psycho_100"],
     ["kageyama shigeo", "reigen arataka"]),
    ("gundam", "gundam", "mobile suit gundam", "anime", ["mobile_suit_gundam"], ["amuro ray", "char aznable"]),
    ("mushoku tensei", "mushoku tensei", "jobless reincarnation", "anime", ["mushoku_tensei"],
     ["rudeus greyrat", "eris boreas greyrat", "roxy migurdia"]),
    # extended fallback list, still all below 70 in the index
    ("hyouka", "hyouka", None, "anime", ["hyouka"], ["chitanda eru", "oreki houtarou"]),
    ("toradora", "toradora", None, "anime", ["toradora!"], ["aisaka taiga", "takasu ryuji"]),
    ("kakegurui", "kakegurui", None, "anime", ["kakegurui"], ["jabami yumeko"]),
    ("nisekoi", "nisekoi", None, "anime", ["nisekoi"], ["kirisaki chitoge", "onodera kosaki"]),
    ("blue box", "blue box", None, "anime", ["ao_no_hako"], ["chiba yumeka"]),
    ("wind breaker", "wind breaker", None, "anime", ["wind_breaker"], ["sakura haruka", "suo hayato"]),
    ("sakamoto days", "sakamoto days", None, "anime", ["sakamoto_days"], ["sakamoto taro"]),
    ("mashle", "mashle", "mashle magic and muscles", "anime", ["mashle"], ["mash burnedead"]),
    ("kaiju no 8", "kaiju no 8", "kaiju no. 8", "anime", ["kaijuu_8gou"], ["kafka hibino"]),
    ("delicious in dungeon", "delicious in dungeon", "dungeon meshi", "anime", ["dungeon_meshi"],
     ["marcille donato", "laios touden"]),
    ("heavenly delusion", "heavenly delusion", "tengoku daimakyou", "anime", ["tengoku_daimakyou"],
     ["kiruko", "maru"]),
    ("soul eater", "soul eater", None, "anime", ["soul_eater"], ["maka albarn", "soul evans"]),
    ("serial experiments lain", "serial experiments lain", "lain", "anime", ["serial_experiments_lain"],
     ["iwakura lain"]),
    ("psycho pass", "psycho pass", "psycho-pass", "anime", ["psycho-pass"], ["tsunemori akane", "kogami shinya"]),
    ("trigun", "trigun", None, "anime", ["trigun"], ["vash the stampede", "meryl stryfe"]),
    ("cowboy bebop", "cowboy bebop", None, "anime", ["cowboy_bebop"], ["spike spiegel", "faye valentine"]),
    ("steins gate", "steins gate", "steins;gate", "anime", ["steins;gate"], ["makise kurisu", "okabe rintarou"]),
    ("code geass", "code geass", None, "anime", ["code_geass"], ["lelouch vi britannia", "c.c."]),
    ("overlord", "overlord", None, "anime", ["overlord_(maruyama)"], ["ainz ooal gown", "albedo"]),
    ("konosuba", "konosuba", None, "anime", ["kono_subarashii_sekai_ni_shukufuku_wo!"],
     ["megumin", "aqua", "darkness"]),
    ("no game no life", "no game no life", None, "anime", ["no_game_no_life"], ["sora", "shiro"]),
    ("blue archive", "blue archive", None, "game", ["blue_archive"], ["shiroko", "hoshino"]),
    ("arknights", "arknights", None, "game", ["arknights"], ["amiya", "kal'tsit"]),
    ("elden ring", "elden ring", None, "game", ["elden_ring"], ["ranni the witch", "malenia"]),
    ("dark souls", "dark souls", None, "game", ["dark_souls"], ["artorias"]),
    ("persona 5", "persona 5", None, "game", ["persona_5"], ["sakura futaba", "takamaki anne"]),
    ("zenless zone zero", "zenless zone zero", None, "game", ["zenless_zone_zero"], ["ellen joe", "miyabi"]),
    ("honkai impact", "honkai impact", "honkai impact 3rd", "game", ["honkai_impact"], ["kiana kaslana"]),
]

BAD = {"text", "english_text", "watermark", "signature", "artist_name", "speech_bubble", "comic", "4koma",
       "multiple_views", "character_sheet", "translated", "logo", "border", "frame", "letterboxed",
       "twitter_username", "web_address", "dated", "artist_logo", "english_commentary", "bad_id",
       "sketch", "monochrome", "greyscale", "partially_colored", "censored", "manga", "scan", "sample",
       "chibi", "comic_panel", "bikini", "swimsuit", "underwear", "lingerie", "panties", "bra",
       "cleavage", "no_bra", "see_through", "spread_legs", "large_breasts", "huge_breasts", "ass",
       "nude", "naked", "topless", "wet", "bed", "bottomless", "sideboob", "underboob", "photo",
       "photograph", "cosplay", "screencap", "screenshot", "reference_sheet", "upscaled",
       "jpeg_artifacts", "lowres", "real_world_location", "photo_background", "collage", "crossover",
       "vector", "lineart", "line_art", "blood", "gore", "guro", "game_cg", "cgi",
       "anime_screencap", "screen_capture", "redraw", "official_art", "promotional_art",
       "key_visual", "poster", "banner", "album", "cover", "movie_poster", "bad_pixiv_id",
       "commentary", "commentary_request", "translation_request", "character_request", "artist_request",
       "wide_image", "phone_wallpaper", "variant_set", "resolution_mismatch", "partially_translated",
       "chinese_text", "korean_text", "japanese_text", "loli", "child", "aged_down", "muscular",
       "abs", "sweat", "tongue", "pov", "faceless_male", "male_focus", "greeting_card", "calendar",
       "sticker", "meme", "logo_parody", "fake_screenshot", "6+boys", "3boys", "smoking", "cigarette",
       "holding_gun", "gun", "food", "weapon_focus", "mecha_focus", "vehicle_focus"}

OUT = "_tmp/low20"
os.makedirs(OUT, exist_ok=True)
PER_SERIES = 26


def dget(url, params, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=25)
            if r.status_code == 200:
                time.sleep(0.6)
                return r.json()
            print("  HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("  ERR", type(e).__name__, flush=True)
        time.sleep(3)
    return None


def danbooru(tag):
    js = dget("https://danbooru.donmai.us/posts.json",
              {"tags": tag + " rating:g", "limit": 200})
    out = []
    for p in js or []:
        out.append(dict(site="danbooru", id=p.get("id"), score=p.get("score") or 0,
                        w=p.get("image_width") or 0, h=p.get("image_height") or 0,
                        url=p.get("file_url") or p.get("large_file_url"),
                        prev=p.get("large_file_url") or p.get("preview_file_url"),
                        tags=(p.get("tag_string") or ""),
                        rating=p.get("rating")))
    return out


def konachan(tag):
    js = dget("https://konachan.net/post.json", {"tags": tag + " rating:s", "limit": 100})
    out = []
    for p in js or []:
        out.append(dict(site="konachan", id=p.get("id"), score=p.get("score") or 0,
                        w=p.get("width") or 0, h=p.get("height") or 0,
                        url=p.get("file_url"), prev=p.get("sample_url") or p.get("file_url"),
                        tags=(p.get("tags") or ""), rating=p.get("rating")))
    return out


meta = {}
for name, itag, alt, cat, tags, chars in SERIES:
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    pool = []
    for t in tags:
        got = danbooru(t)
        print("  %-22s danbooru %-32s -> %d" % (name, t, len(got)), flush=True)
        pool += got
        if len(pool) >= 150:
            break
    if len(pool) < 30:
        for t in tags:
            got = konachan(t)
            print("  %-22s konachan %-32s -> %d" % (name, t, len(got)), flush=True)
            pool += got
    seen, kept = set(), []
    pool.sort(key=lambda p: -(p["score"] or 0))
    for p in pool:
        key = (p["site"], str(p["id"]))
        if key in seen:
            continue
        seen.add(key)
        w, h = p["w"], p["h"]
        if not w or not h or not p.get("url") or not p.get("prev"):
            continue
        r = h / w
        if r >= 1.15:
            if h < 1250 or w < 680:
                continue
        else:
            if h < 1100 or w < 1700:
                continue
        if set(p["tags"].split()) & BAD:
            continue
        if p.get("rating") not in ("g", "s", None):
            continue
        kept.append(p)
    meta[slug] = dict(name=name, itag=itag, alt=alt, cat=cat, chars=chars,
                      pool=len(pool), valid=len(kept), cands=kept[:PER_SERIES])
    print("== %-22s pool=%d valid=%d kept=%d" % (name, len(pool), len(kept), len(meta[slug]["cands"])), flush=True)

json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
print("SUMMARY")
for k, v in sorted(meta.items(), key=lambda kv: -kv[1]["valid"]):
    print("  %-24s %d" % (v["name"], v["valid"]))
