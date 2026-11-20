import json, time
import requests
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Referer":"https://konachan.net/"}
PAIRS=[("chiikawa","chiikawa"),("natsume yuujinchou","natsume_yuujinchou"),("initial d","initial_d"),
("chihayafuru","chihayafuru"),("my dress up darling","sono_bisque_doll_wa_koi_wo_suru"),
("ranma 1/2","ranma_1/2"),("gurren lagann","tengen_toppa_gurren_lagann"),("ponyo","gake_no_ue_no_ponyo"),
("bunny girl senpai","seishun_buta_yarou"),("oregairu","yahari_ore_no_seishun_love_comedy_wa_machigatteiru"),
("vinland saga","vinland_saga"),("seven deadly sins","nanatsu_no_taizai"),("fire force","enen_no_shouboutai"),
("hells paradise","jigokuraku"),("kuroko no basket","kuroko_no_basket"),("noragami","noragami"),
("rurouni kenshin","rurouni_kenshin"),("monster","monster_(manga)"),("mob psycho 100","mob_psycho_100"),
("gintama","gintama"),("gundam","gundam"),("re zero","re:zero_kara_hajimeru_isekai_seikatsu"),
("darling in the franxx","darling_in_the_franxx"),("dr stone","dr._stone"),("haikyuu","haikyuu!!"),
("horimiya","horimiya"),("laid back camp","yuru_camp"),("wind breaker","wind_breaker_(manga)"),
("cyberpunk edgerunners","cyberpunk:_edgerunners"),("solo leveling","solo_leveling"),
("made in abyss","made_in_abyss"),("rent a girlfriend","kanojo_okarishimasu"),("promised neverland","yakusoku_no_neverland"),
("blue exorcist","ao_no_exorcist"),("dungeon meshi","dungeon_meshi"),("konosuba","kono_subarashii_sekai_ni_shukufuku_wo!"),
("mashle","mashle"),("nisekoi","nisekoi"),("no game no life","no_game_no_life"),("steins gate","steins;gate"),
("code geass","code_geass"),("cowboy bebop","cowboy_bebop"),("fullmetal alchemist","fullmetal_alchemist"),
("psycho pass","psycho-pass"),("sword art online","sword_art_online"),("cardcaptor sakura","cardcaptor_sakura"),
("sailor moon","bishoujo_senshi_sailor_moon"),("toradora","toradora!"),("trigun","trigun"),
("bocchi the rock","bocchi_the_rock!"),("neon genesis evangelion","neon_genesis_evangelion"),
("oshi no ko","oshi_no_ko"),("berserk","berserk"),("bleach","bleach"),("overlord","overlord_(novel)"),
("puella magi madoka magica","mahou_shoujo_madoka_magica"),("apothecary diaries","kusuriya_no_hitorigoto"),
("fairy tail","fairy_tail"),("spy x family","spy_x_family"),("tensura","tenseishitara_slime_datta_ken"),
("serial experiments lain","serial_experiments_lain"),("hyouka","hyouka"),("akame ga kill","akame_ga_kill!"),
("touhou project","touhou"),("86 eighty six","86_-eightysix-"),("railgun","toaru_kagaku_no_railgun"),
("dandadan","dandadan"),("blue box","ao_no_hako"),("sakamoto days","sakamoto_days"),
("uzumaki","uzumaki_(junji_ito)"),("tales from earthsea","ged_senki_tan"),("the cat returns","neko_no_ongaeshi"),
("the wind rises","kaze_tachinu"),("love is war","kaguya-sama_wa_kokurasetai"),
("hells paradise2","hell's_paradise"),("look back","look_back_(manga)"),("wistoria","tsue_to_tsurugi_no_wistoria"),
("frieren","sousou_no_frieren"),("violet evergarden","violet_evergarden"),("dandadan2","dandadan!"),
("blue archive","blue_archive"),("girls frontline","girls'_frontline"),("persona 5","persona_5"),
("ranma","ranma_1/2"),("jujutsu kaisen","jujutsu_kaisen"),("chainsaw man","chainsaw_man"),
("one piece","one_piece"),("demon slayer","kimetsu_no_yaiba"),("naruto","naruto"),
("my hero academia","boku_no_hero_academia"),("hunter x hunter","hunter_x_hunter"),
("sakamoto days2","sakamoto_days_(manga)")]
res=[]
for our,tag in PAIRS:
    try:
        r=requests.get("https://konachan.net/tag.json",params={"name":tag,"limit":5},headers=UA,timeout=20)
        tj=r.json() if r.status_code==200 else []
    except Exception as e:
        tj=[]
    c=tj[0]["count"] if tj else 0
    ty=tj[0]["type"] if tj else 0
    # sample 100 top posts, count portrait-usable
    port=0
    try:
        r2=requests.get("https://konachan.net/post.json",params={"tags":tag+" rating:s","limit":100,"page":1},headers=UA,timeout=30)
        posts=r2.json() if r2.status_code==200 else []
        for p in posts:
            w=p.get("width") or 0; h=p.get("height") or 0
            if not w or not h: continue
            rr=h/w
            if rr>=1.2 and h>=1250 and w>=700: port+=1
            elif 0.9<=rr<1.2 and h>=1500: port+=1
            elif rr<0.9 and w>=2400 and h>=1300: port+=1
    except Exception:
        posts=[]
    print(f"{our} | kona={c} type={ty} sample={len(posts)} usable_portrait={port}", flush=True)
    time.sleep(0.7)
