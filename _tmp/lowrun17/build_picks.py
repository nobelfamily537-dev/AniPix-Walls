import json, os
from PIL import Image

# filled in after reviewing the contact sheets
PICKS = {
 "inuyasha": [0,1,3,4,5,6,8,9,11,12,13,17,18,19,21,23],
 "pokemon": [4,5,7,8,10,11,12,19,23,24,26,28,35,37,38,39,42,46],
 "suzume no tojimari": [0,4,12,13,15,16,17,18,19,22,23,25,27,28],
 "blue box": [2,4,6,8,10,11,12,14,16,17,18,20,22],
 "black clover": [1,2,4,9,11,13,17,26,28,32,34,37,41,42,44],
 "princess mononoke": [2,4,6,11,12,13,16,17,19,20,21,23],
 "touhou project": [0,1,3,4,5,7,8,11,12,13,14,18],
 "one-punch man": [1,2,4,5,8,9,24,26,28,32,34,39],
 "kakegurui": [0,1,2,3,7,8,9,10,17,19,22],
 "soul eater": [3,6,11,12,13,14,15,18,19,22],
}


SERIES_SRC = {
 "princess mononoke": ["mononoke_hime"],
 "black clover": ["black_clover"],
 "pokemon": ["pokemon"],
 "suzume no tojimari": ["suzume_no_tojimari", "iwakura_suzume"],
 "touhou project": ["touhou"],
 "one-punch man": ["one-punch_man"],
 "inuyasha": ["inuyasha"],
 "kakegurui": ["kakegurui"],
 "soul eater": ["soul eater"],
 "blue box": ["ao no hako"],
}

CHARS = {
 "princess mononoke": ["san","ashitaka","moro","kodama","yakul","eboshi","jigo","okkoto","san (mononoke hime)"],
 "black clover": ["asta","yuno","noelle silva","yami sukehiro","mimosa vermillion","luck voltia",
   "charmy pappitson","mereoleona vermillion","julius novachrono","fuegoleon vermillion","nacht faust",
   "nozel silva","asta (black clover)","yuno (black clover)"],
 "pokemon": ["pikachu","eevee","gardevoir","mewtwo","mew","lucario","sylveon","charizard","greninja",
   "gengar","umbreon","espeon","dragonair","milotic","garchomp","zeraora","raichu","lillie","cynthia",
   "misty","serena","dawn"],
 "suzume no tojimari": ["iwakura suzume","munakata souta","daijin","suzume","souta","tamaki"],
 "touhou project": ["hakurei reimu","kirisame marisa","izayoi sakuya","remilia scarlet","flandre scarlet",
   "konpaku youmu","saigyouji yuyuko","komeiji satori","komeiji koishi","cirno","reisen udongein",
   "patchouli knowledge","aya shameimaru","kochiya sanae","fujiwara no mokou","reimu","marisa","sakuya",
   "youmu","yuyuko","koishi","satori","flandre","remilia"],
 "one-punch man": ["saitama","genos","tatsumaki","fubuki","garou","speed-o'-sound sonic","sonic","king",
   "bang","atomic samurai","mumen rider","saitama (one-punch man)","fubuki (one-punch man)"],
 "inuyasha": ["inuyasha","higurashi kagome","kagome","sesshomaru","kikyou","sango","miroku","shippo",
   "naraku","rin","kouga","kirara"],
 "kakegurui": ["jabami yumeko","yumeko jabami","momobami kirari","kirari momobami","saotome mary",
   "mary saotome","momobami ririka","ririka momobami","itsuki sumeragi","sumeragi itsuki",
   "igarashi sayaka","sayaka igarashi","yumeko","kirari","mary","ririka"],
 "soul eater": ["maka albarn","soul evans","evans","black star","tsubaki nakatsukasa","nakatsukasa tsubaki",
   "death the kid","crona","spirit albarn","medusa gorgon","franken stein","blair","elizabeth thompson",
   "patricia thompson","excalibur","maka","soul","crona"],
 "blue box": ["inoue chinatsu","chinatsu inoue","kano chinatsu","kano taiki","taiki kano","chono hina",
   "hina chono","kashiwagi ayame","kasahara kyou","chinatsu","taiki","hina","ayame"],
}

VOCAB = ["hair","eyes","twintails","ponytail","braid","bangs","ahoge","ribbon","bow","dress","uniform",
 "skirt","shirt","jacket","coat","hoodie","scarf","gloves","boots","shoes","socks","thighhighs","hat",
 "cap","tie","necklace","earrings","kimono","yukata","hood","cape","armor","glasses","sword","gun",
 "weapon","umbrella","book","flower","flowers","petal","microphone","guitar","bag","staff","wand",
 "bicycle","car","train","sky","cloud","clouds","night","star","stars","moon","sun","sunset","sunrise",
 "rain","snow","water","sea","ocean","river","lake","mountain","forest","tree","trees","city","building",
 "street","room","window","school","beach","field","grass","garden","bridge","road","light","lights",
 "smile","smiling","crying","tears","sleeping","lying","hugging","holding","reaching","dancing",
 "singing","flying","jumping","silhouette","shadow","reflection","bokeh","glow","lens flare","portrait",
 "close-up","cinematic","dramatic","dreamy","melancholy","cozy","warm","cool","fantasy","magic",
 "magical","pastel","bright","dark","seaside","snowfall","cherry blossoms","sakura","autumn","summer",
 "winter","spring","night sky","fireworks","lantern","stars","constellation","moonlight","sunlight",
 "sparkle","sparkles","petals","confetti","wings","angel","cat","animal","plushie","food","drink"]

META_BAD = {"close","group","aqua","green","red","blue","pink","white","black","orange","purple","brown",
 "yellow","grey","silver","gold"}

MOOD = {
 "princess mononoke": ["studio ghibli","fantasy","nature","forest","adventure"],
 "black clover": ["shounen","magic","fantasy","action","knights"],
 "pokemon": ["creature","cute","adventure","colorful","fantasy"],
 "suzume no tojimari": ["makoto shinkai","romance","journey","sky","emotional"],
 "touhou project": ["magical","fantasy","shrine maiden","gothic","cute girls"],
 "one-punch man": ["superhero","action","comedy","powerful"],
 "inuyasha": ["feudal japan","fantasy","romance","adventure","youkai"],
 "kakegurui": ["gambling","psychological","school","thriller","dramatic"],
 "soul eater": ["dark fantasy","shinigami","weapon","gothic","action"],
 "blue box": ["romance","sports","school","slice of life","wholesome"],
}

NOISE = {"hatsune miku","skirt lift","navel","midriff","bare shoulders","thighs","breasts","cleavage",
 "pillow","bed","panties","underwear","bikini","swimsuit","wet","sweat","tongue","pov","armored core",
 "allmind","male focus","faceless male","abs","muscular"}

STYLE = ["detailed art","soft shading","cinematic lighting","anime wallpaper","elegant"]

ALT = {
 "princess mononoke": ["mononoke hime", "studio ghibli"],
 "black clover": ["clover kingdom"],
 "pokemon": ["pokemon anime"],
 "suzume no tojimari": ["suzume", "makoto shinkai"],
 "touhou project": ["touhou"],
 "one-punch man": ["opm", "one punch man"],
 "inuyasha": ["inuyasha anime", "feudal japan"],
 "kakegurui": ["compulsive gambler", "kakegurui xx"],
 "soul eater": ["shinigami", "death weapon"],
 "blue box": ["ao no hako"],
}

OUTDIR = "_tmp/lowrun17"


def colour_theme(path):
    im = Image.open(path).convert("RGB").resize((40, 70))
    px = list(im.getdata())
    n = len(px)
    r = sum(p[0] for p in px) / n
    g = sum(p[1] for p in px) / n
    b = sum(p[2] for p in px) / n
    lum = (r + g + b) / 3
    mx, mn = max(r, g, b), min(r, g, b)
    if lum > 205 and mx - mn < 30:
        return ["white theme", "minimal", "bright", "clean"]
    if lum < 55:
        return ["dark theme", "night", "moody", "shadow"]
    if mx - mn < 22:
        return ["muted tones", "soft light", "calm"]
    if r >= g and r >= b:
        return ["warm tones", "red theme", "amber"] if lum < 150 else ["warm tones", "pink theme", "soft light"]
    if b >= r and b >= g:
        return ["blue theme", "cool tones", "twilight"] if lum < 150 else ["blue theme", "sky", "pastel"]
    return ["green theme", "nature", "calm", "foliage"]


cands = json.load(open(os.path.join(OUTDIR, "cands.json")))
by = {}
for c in cands:
    by.setdefault(c["series"], {})[c["idx"]] = c

out, dropped = [], []
flip = 0
for series, idxs in PICKS.items():
    for i in idxs:
        c = by[series][i]
        srctags = c["tags"].split()
        if not any(s in srctags for s in SERIES_SRC[series]):
            dropped.append((series, i, "not-series"))
            continue
        conv = [t.replace("_", " ").lower() for t in srctags]
        tags = [series] + ALT.get(series, [])
        chars = []
        for t in conv:
            for name in CHARS[series]:
                if name in t and name not in chars:
                    chars.append(name)
        for ch in chars[:3]:
            if any(ch in t or t in ch for t in tags):
                continue
            tags.append(ch)
        details = []
        for t in conv:
            if t in tags or t in META_BAD or t in NOISE or len(t) < 4 or t.isdigit():
                continue
            if "(" in t or ":" in t or ")" in t:
                continue
            if any(v in t for v in VOCAB) and t not in details:
                details.append(t)
        for d in details:
            if len(tags) < 11 and d not in tags:
                tags.append(d)
        for m in MOOD.get(series, []):
            if len(tags) < 12 and m not in tags:
                tags.append(m)
        for t in colour_theme(os.path.join(OUTDIR, "prev", c["file"])):
            if len(tags) < 15 and t not in tags:
                tags.append(t)
        for st in STYLE:
            if len(tags) >= 12:
                break
            if st not in tags:
                tags.append(st)
        tags = tags[:15]
        cat = "anime" if flip % 2 == 0 else "anime2"
        flip += 1
        out.append({"series": series, "idx": i, "pid": c["pid"], "url": c["url"], "cat": cat,
                    "w": c["w"], "h": c["h"], "tags": tags})

json.dump(out, open(os.path.join(OUTDIR, "picks.json"), "w"), indent=1)
from collections import Counter
print("picks", len(out), Counter(p["series"] for p in out), Counter(p["cat"] for p in out))
print("dropped", dropped)
print("short tags:", [(p["series"], p["idx"], len(p["tags"])) for p in out if len(p["tags"]) < 10])
for p in out[:4]:
    print(p["series"], p["idx"], p["tags"])
