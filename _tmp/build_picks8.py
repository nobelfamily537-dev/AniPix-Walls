#!/usr/bin/env python3
"""Build _tmp/pickslow8.json from curated picks (batch given as argv[1])."""
import json, os, sys

C10 = json.load(open("_tmp/candlow10.json"))
C11 = json.load(open("_tmp/candlow11.json"))
URL = {c["file"]: c["url"] for c in C10 + C11}

P = {
    # ---------------- pokemon (game) ----------------
    "pokemon_02": ("game", "pokemon", "latios,latias,pokemon,legendary pokemon,clouds,sky,flying,teal,blue,dragon,soaring,soft light,aerial"),
    "pokemon_03": ("game", "pokemon", "corviknight,pokemon,torii gate,autumn leaves,red,black,forest,dusk,bird,japanese shrine,moody,cinematic"),
    "pokemon_07": ("game", "pokemon", "pokemon,dragon creature,autumn,forest,red,white,mist,towering,dark fantasy,moody"),
    "pokemon_08": ("game", "pokemon", "sylveon,pokemon,pastel,pink,cosy room,girl,computer,night,soft light,cute,indoor"),
    "pokemon_10": ("game", "pokemon", "bulbasaur,pokemon,green,portrait,cute,grass type,nature,soft light,starter pokemon"),
    "pokemon_11": ("game", "pokemon", "chandelure,pokemon,purple,flames,ghost type,dark,vibrant,candles,moody"),
    "pokemon_12": ("game", "pokemon", "rayquaza,pokemon,space,dragon,green,stars,cosmic,legendary pokemon,nebula"),
    "pokemon_15": ("game", "pokemon", "vaporeon,pokemon,water,river,blue,forest,peaceful,nature,eeveelution"),
    "pokemon_17": ("game", "pokemon", "pikachu,pichu,raichu,pokemon,forest,green,cute,sunlight,nature,electric type"),
    "pokemon_19": ("game", "pokemon", "leafeon,pokemon,forest,green,nature,sunlight,eeveelution,peaceful"),
    "pokemon_20": ("game", "pokemon", "pikachu,pokemon,meadow,blue sky,clouds,grass,summer,bright,cute"),
    "pokemon_21": ("game", "pokemon", "ho-oh,pokemon,rain,legendary pokemon,fire,red,golden,dramatic,sky,mythic"),

    # ---------------- clannad (anime) ----------------
    "clannad_06": ("anime", "clannad", "clannad,clannad after story,girl,scooter,summer,street,sunlight,warm,nostalgic,slice of life"),
    "clannad_08": ("anime", "clannad", "clannad,tomoya okazaki,nagisa furukawa,couple,white background,minimal,romance,soft,school uniform"),
    "clannad_10": ("anime", "clannad", "clannad,nagisa furukawa,ushio okazaki,mother and daughter,flower field,warm,sunset,emotional,field"),
    "clannad_11": ("anime", "clannad", "clannad,family,indoor,warm light,slice of life,cosy,living room,gentle"),
    "clannad_13": ("anime", "clannad", "clannad,nagisa furukawa,blue dress,sea,beach,summer,sky,wind,nostalgic"),
    "clannad_14": ("anime", "clannad", "clannad,girl,stairs,bamboo,green,sunlight,summer,serene"),
    "clannad_16": ("anime", "clannad", "clannad,family,tree,sunset,warm,silhouette,emotional,gentle"),
    "clannad_20": ("anime", "clannad", "clannad,fujibayashi ryou,fujibayashi kyou,twins,cards,bright,cheerful,school uniform"),
    "clannad_21": ("anime", "clannad", "clannad,family,picnic,park,spring,cheerful,slice of life,warm"),
    "clannad_23": ("anime", "clannad", "clannad,girl,garden,flowers,green,sunlight,gentle,soft"),

    # ---------------- neon genesis evangelion (anime2) ----------------
    "neon-genesis-evangelion_03": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,rei ayanami,plugsuit,cockpit,red,dramatic,sci-fi,mecha"),
    "neon-genesis-evangelion_05": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,rei ayanami,plugsuit,pale,ethereal,minimal,white,blue hair"),
    "neon-genesis-evangelion_08": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,eva unit 01,berserk,purple,green,dramatic,apocalypse,mecha"),
    "neon-genesis-evangelion_09": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,plugsuit,sky,clouds,red,wind,confident"),
    "neon-genesis-evangelion_10": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,sunset,street,red hair,casual,warm"),
    "neon-genesis-evangelion_15": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,portrait,red,intense,close-up,dramatic"),
    "neon-genesis-evangelion_16": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,rei ayanami,sunset,sky,clouds,orange,serene"),
    "neon-genesis-evangelion_17": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,red,water,flowers,reflection,dreamlike"),
    "neon-genesis-evangelion_20": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,sleeping,red,soft,peaceful"),
    "neon-genesis-evangelion_21": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,rei ayanami,shinji ikari,red background,trio,minimal"),
    "neon-genesis-evangelion_23": ("anime2", "neon genesis evangelion", "neon genesis evangelion,evangelion,asuka langley,rei ayanami,black background,red,plugsuit,contrast"),

    # ---------------- konosuba (anime) ----------------
    "konosuba_01": ("anime", "konosuba", "konosuba,megumin,crimson demon,staff,sunset,orange,sky,silhouette,wizard"),
    "konosuba_05": ("anime", "konosuba", "konosuba,megumin,explosion,magic,fire,orange,dramatic,sky,wizard"),
    "konosuba_06": ("anime", "konosuba", "konosuba,megumin,kazuma satou,wedding,dress,romance,cheerful,bright"),
    "konosuba_07": ("anime", "konosuba", "konosuba,megumin,yunyun,reading,indoor,cosy,warm light,books"),
    "konosuba_08": ("anime", "konosuba", "konosuba,megumin,portrait,red eyes,wizard hat,cape,confident,warm"),
    "konosuba_10": ("anime", "konosuba", "konosuba,darkness,maid outfit,white background,minimal,cute"),
    "konosuba_11": ("anime", "konosuba", "konosuba,megumin,kazuma satou,couple,cheerful,bright,adventure"),
    "konosuba_12": ("anime", "konosuba", "konosuba,megumin,fire,explosion,magic circle,red,dramatic"),
    "konosuba_14": ("anime", "konosuba", "konosuba,megumin,yukata,fireworks,night,summer festival,red,warm"),
    "konosuba_16": ("anime", "konosuba", "konosuba,megumin,kazuma satou,close-up,playful,warm"),
    "konosuba_17": ("anime", "konosuba", "konosuba,megumin,rainbow,magic,colourful,sky,vibrant"),
    "konosuba_19": ("anime", "konosuba", "konosuba,megumin,aqua,darkness,kazuma satou,group,white background,cheerful"),

    # ---------------- tokyo ghoul (anime2) ----------------
    "tokyo-ghoul_01": ("anime2", "tokyo ghoul", "tokyo ghoul,touka kirishima,kagune,red,ruined building,dark,dramatic"),
    "tokyo-ghoul_02": ("anime2", "tokyo ghoul", "tokyo ghoul,touka kirishima,kagune,sunset,city,rooftop,orange,dramatic"),
    "tokyo-ghoul_03": ("anime2", "tokyo ghoul", "tokyo ghoul,touka kirishima,kagune,black dress,white background,red,elegant"),
    "tokyo-ghoul_06": ("anime2", "tokyo ghoul", "tokyo ghoul,ken kaneki,rooftop,night,city,rain,dark,lonely"),
    "tokyo-ghoul_11": ("anime2", "tokyo ghoul", "tokyo ghoul,ken kaneki,touka kirishima,sofa,indoor,moody,stylish"),
    "tokyo-ghoul_12": ("anime2", "tokyo ghoul", "tokyo ghoul,ken kaneki,portrait,dark,white hair,red eye,intense"),
    "tokyo-ghoul_14": ("anime2", "tokyo ghoul", "tokyo ghoul,ken kaneki,kagune,white background,red,black,dramatic"),
    "tokyo-ghoul_17": ("anime2", "tokyo ghoul", "tokyo ghoul,touka kirishima,kagune,leaping,action,red,dynamic"),
    "tokyo-ghoul_18": ("anime2", "tokyo ghoul", "tokyo ghoul,ken kaneki,rain,city,crowd,umbrella,melancholy,dark"),
    "tokyo-ghoul_19": ("anime2", "tokyo ghoul", "tokyo ghoul,ken kaneki,butterfly,dark,gothic,red,mysterious"),

    # ---------------- your name (anime) ----------------
    "your-name_00": ("anime", "your name", "your name,kimi no na wa,comet,sky,clouds,twilight,romantic,blue,stars"),
    "your-name_01": ("anime", "your name", "your name,kimi no na wa,comet,sky,silhouette,twilight,romantic,purple"),
    "your-name_02": ("anime", "your name", "your name,kimi no na wa,mitsuha miyamizu,shrine maiden,red ribbon,traditional,japanese,portrait"),
    "your-name_03": ("anime", "your name", "your name,kimi no na wa,taki tachibana,mitsuha miyamizu,stairs,sunset,romantic,city"),
    "your-name_06": ("anime", "your name", "your name,kimi no na wa,comet,night sky,stars,blue,dreamy,landscape"),
    "your-name_07": ("anime", "your name", "your name,kimi no na wa,hands,red ribbon,white background,minimal,tender,romance"),
    "your-name_09": ("anime", "your name", "your name,kimi no na wa,taki tachibana,mitsuha miyamizu,sunset,sky,romantic,warm"),
    "your-name_10": ("anime", "your name", "your name,kimi no na wa,comet,sky,clouds,twilight,blue,serene"),
    "your-name_11": ("anime", "your name", "your name,kimi no na wa,taki tachibana,mitsuha miyamizu,stairs,golden hour,romantic"),
    "your-name_13": ("anime", "your name", "your name,kimi no na wa,couple,sky,clouds,romantic,soft light,blue"),
    "your-name_14": ("anime", "your name", "your name,kimi no na wa,couple,clouds,sky,dreamy,romantic,pastel"),

    # ---------------- attack on titan (anime2) ----------------
    "attack-on-titan_01": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,mikasa ackerman,blades,red scarf,dynamic,action,white background"),
    "attack-on-titan_02": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,mikasa ackerman,rooftop,sunset,city,odm gear,silhouette,epic"),
    "attack-on-titan_03": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,mikasa ackerman,titans,battlefield,epic,red scarf,dramatic"),
    "attack-on-titan_06": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,mikasa ackerman,horse,sunset,scout regiment,cloak,motion"),
    "attack-on-titan_07": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,scout regiment,sea,grass,clouds,freedom,emotional"),
    "attack-on-titan_09": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,scout regiment,group,butterflies,sky,memorial,emotional"),
    "attack-on-titan_10": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,levi ackerman,hange zoe,forest,odm gear,action,green"),
    "attack-on-titan_11": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,colossal titan,wall,fire,epic,dramatic,red sky"),
    "attack-on-titan_12": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,scout regiment,red scarf,black background,action,group"),
    "attack-on-titan_15": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,eren yeager,levi ackerman,shattered glass,dynamic,action"),
    "attack-on-titan_16": ("anime2", "attack on titan", "attack on titan,shingeki no kyojin,mikasa ackerman,titan,battle,odm gear,dynamic"),

    # ---------------- suzume (anime) ----------------
    "suzume_00": ("anime", "suzume", "suzume,suzume no tojimari,door,field,sky,water reflection,magical,blue,girl"),
    "suzume_02": ("anime", "suzume", "suzume,suzume no tojimari,daijin,cat,white background,cute,minimal,soft"),
    "suzume_03": ("anime", "suzume", "suzume,suzume no tojimari,suzume iwato,doors,night,stars,magical,purple,dreamlike"),
    "suzume_04": ("anime", "suzume", "suzume,suzume no tojimari,suzume iwato,daijin,chair,blue sky,portrait,summer,cute"),
}

BATCH1 = ["pokemon", "clannad", "neon genesis evangelion", "konosuba"]
BATCH2 = ["tokyo ghoul", "your name", "attack on titan", "suzume"]

batch = sys.argv[1] if len(sys.argv) > 1 else "1"
wanted = BATCH1 if batch == "1" else BATCH2

picks = []
missing = []
for f, (cat, series, tags) in P.items():
    if series not in wanted:
        continue
    f = f if f.endswith(".jpg") else f + ".jpg"
    if f not in URL:
        missing.append(f)
        continue
    picks.append({"file": f, "url": URL[f], "cat": cat, "series": series, "tags": tags})

json.dump(picks, open("_tmp/pickslow8.json", "w"), indent=1)
print("batch", batch, "picks", len(picks), "missing", missing)
from collections import Counter
print(Counter(p["series"] for p in picks))
print(Counter(p["cat"] for p in picks))

# ---------------- batch 3 ----------------
P3 = {
    "my-neighbor-totoro_01": ("anime", "my neighbor totoro", "my neighbor totoro,totoro,tonari no totoro,studio ghibli,girl,doorway,meadow,green hills,summer,blue sky,peaceful"),
    "my-neighbor-totoro_03": ("anime", "my neighbor totoro", "my neighbor totoro,totoro,tonari no totoro,studio ghibli,full moon,night,grass,whimsical,cute,magical"),
    "my-neighbor-totoro_04": ("anime", "my neighbor totoro", "my neighbor totoro,totoro,tonari no totoro,studio ghibli,house,red roof,blue sky,countryside,summer,scenery"),
    "my-neighbor-totoro_05": ("anime", "my neighbor totoro", "my neighbor totoro,totoro,tonari no totoro,studio ghibli,rain,umbrella,night,forest,cute,moody"),
    "my-neighbor-totoro_08": ("anime", "my neighbor totoro", "my neighbor totoro,totoro,tonari no totoro,studio ghibli,watercolour,rain,umbrella,girl,soft,muted"),
    "madoka-magica_00": ("anime2", "madoka magica", "madoka magica,puella magi madoka magica,homura akemi,madoka kaname,cliff,magic circle,pink,dramatic,epic"),
    "madoka-magica_01": ("anime2", "madoka magica", "madoka magica,puella magi madoka magica,kyoko sakura,homura akemi,madoka kaname,magical girls,action,checkered floor,vibrant"),
    "madoka-magica_03": ("anime2", "madoka magica", "madoka magica,puella magi madoka magica,madoka kaname,cherry blossoms,pink,spring,magical girl,soft light"),
    "madoka-magica_04": ("anime2", "madoka magica", "madoka magica,puella magi madoka magica,madoka kaname,homura akemi,pink,white,contrast,tender,dramatic"),
    "madoka-magica_05": ("anime2", "madoka magica", "madoka magica,puella magi madoka magica,madoka kaname,space,cosmic,stars,pink,planets,ethereal"),
    "madoka-magica_07": ("anime2", "madoka magica", "madoka magica,puella magi madoka magica,madoka kaname,ultimate madoka,wings,pink,divine,dramatic"),
    "madoka-magica_08": ("anime2", "madoka magica", "madoka magica,puella magi madoka magica,madoka kaname,homura akemi,dark,warm light,elegant,gothic"),
    "madoka-magica_10": ("anime2", "madoka magica", "madoka magica,puella magi madoka magica,madoka kaname,white dress,flowers,garden,angel,serene,soft"),
}
if batch == "3":
    C12 = json.load(open("_tmp/candlow12.json"))
    U12 = {c["file"]: c["url"] for c in C12}
    picks = []
    miss = []
    for f, (cat, series, tags) in P3.items():
        fn = f if f.endswith(".jpg") else f + ".jpg"
        if fn not in U12:
            miss.append(fn)
            continue
        picks.append({"file": fn, "url": U12[fn], "cat": cat, "series": series, "tags": tags})
    json.dump(picks, open("_tmp/pickslow8.json", "w"), indent=1)
    print("batch 3 picks", len(picks), "missing", miss)
    print(Counter(p["series"] for p in picks), Counter(p["cat"] for p in picks))
