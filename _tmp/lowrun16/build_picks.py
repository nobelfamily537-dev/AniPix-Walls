import json, os
from PIL import Image

PICKS = {
 "mahou shoujo madoka magica": [0,1,3,7,8,10,11,12,13,14,16,17,18,20,22,23,24,25,27,28],
 "anohana": [0,1,2,4,6,7,8,9,10,12,13,14,15,17,18,19,20,21,22,24],
 "yuru camp": [3,4,5,6,7,9,10,11,12,13,14,15,17,18,19,22],
 "lycoris recoil": [0,1,3,4,5,6,7,10,12,13,15],
 "psycho pass": [0,1,3,5,6,9,10,11,13,14],
 "overlord": [3,6,7,8,9,11,12],
 "detective conan": [2,3,4,5,6,7,10],
 "weathering with you": [0,2,6,7,8,9],
 "oshi no ko": [0,1,2,3],
}

SERIES_SRC = {
 "mahou shoujo madoka magica": ["mahou_shoujo_madoka_magica"],
 "anohana": ["ano_hi_mita_hana_no_namae_wo_bokutachi_wa_mada_shiranai"],
 "yuru camp": ["yuru_camp"],
 "lycoris recoil": ["lycoris_recoil"],
 "psycho pass": ["psycho-pass", "psycho_pass"],
 "overlord": ["overlord"],
 "detective conan": ["detective_conan"],
 "weathering with you": ["tenki_no_ko"],
 "oshi no ko": ["oshi_no_ko"],
}

CHARS = {
 "mahou shoujo madoka magica": ["kaname madoka","madoka kaname","akemi homura","homura akemi","miki sayaka",
   "sayaka miki","sakura kyoko","kyoko sakura","tomoe mami","mami tomoe","ultimate madoka","nagisa momoe",
   "kyuubee","kyubey","charlotte (madoka magica)","walpurgisnacht","devil homura","homura"],
 "anohana": ["menma","honma meiko","meiko honma","anaru","anjo naruko","naruko anjo","yadomi jinta",
   "jinta yadomi","hisakawa tetsudo","tsuruko","chiriko tsurumi","yukiatsu","atsumu matsuyuki"],
 "yuru camp": ["kagami rin","rin kagami","shima rin","nadeshiko kagamihara","kagamihara nadeshiko",
   "inuyama aoi","aoi inuyama","saitou ena","ena saitou","ogaki chiaki","chiaki ogaki","inuyama sakura","rin shima"],
 "lycoris recoil": ["nishikigi chisato","chisato nishikigi","inoue takina","takina inoue","chisato","takina",
   "kurumi","mika"],
 "psycho pass": ["tsunemori akane","akane tsunemori","kougami shinya","shinya kougami","makishima shougo",
   "shougo makishima","ginoza nobuchika","kagari shion","shion kagari","sibyl","mika shimotsuki"],
 "overlord": ["ainz ooal gown","albedo","shalltear bloodfallen","shalltear","demiurge","cocytus",
   "aura bella fiora","mare bello fiore","evileye","solution epsilon","pandora's actor","nabe"],
 "detective conan": ["edogawa conan","conan edogawa","conan","mouri ran","ran mouri","haibara ai","ai haibara",
   "kudou shinichi","shinichi kudou","akai shuichi","shuichi akai","amuro tooru","tooru amuro","furuya rei",
   "kid the phantom thief","phantom thief kid","mouri kogorou","sonoko suzuki","suzuki sonoko","sherry"],
 "weathering with you": ["amano hina","hina amano","morishima hodaka","hodaka morishima","hina","hodaka",
   "nagisa amano","amano nagisa"],
 "oshi no ko": ["hoshino ai","ai hoshino","hoshino aqua","hoshino aquamarine","hoshino ruby","arima kana",
   "kana arima","kurokawa akane","akane kurokawa","ai","aqua","ruby"],
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
 "mahou shoujo madoka magica": ["magical girl","dark fantasy","emotional","dreamy","tragic"],
 "anohana": ["slice of life","emotional","summer","nostalgic","tearjerker"],
 "yuru camp": ["slice of life","cozy","winter","camping","relaxing"],
 "lycoris recoil": ["action","guns","cafe","spy","cute girls"],
 "psycho pass": ["cyberpunk","sci-fi","dark","dystopian","futuristic"],
 "overlord": ["dark fantasy","isekai","villain","overpowered","guild"],
 "detective conan": ["mystery","detective","crime","thriller"],
 "weathering with you": ["romance","rain","sky","makoto shinkai","melancholy"],
 "oshi no ko": ["idol","music","showbiz","drama"],
}
NOISE = {"hatsune miku","skirt lift","navel","midriff","bare shoulders","thighs","breasts","cleavage","pillow","bed","panties","underwear","bikini","swimsuit","wet","sweat","tongue","pov","armored core","allmind"}
STYLE = ["detailed art","soft shading","cinematic lighting","anime wallpaper","elegant"]

ALT = {
 "mahou shoujo madoka magica": ["madoka magica"],
 "anohana": ["anohana the flower we saw that day"],
 "yuru camp": ["laid-back camp"],
 "psycho pass": ["psycho-pass"],
 "detective conan": ["case closed"],
 "weathering with you": ["tenki no ko"],
}


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


cands = json.load(open("_tmp/lowrun16/cands.json"))
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
        for t in colour_theme(os.path.join("_tmp/lowrun16/prev", c["file"])):
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

json.dump(out, open("_tmp/lowrun16/picks.json", "w"), indent=1)
from collections import Counter
print("picks", len(out), Counter(p["series"] for p in out), Counter(p["cat"] for p in out))
print("dropped", dropped)
print("short tags:", [(p["series"], p["idx"], len(p["tags"])) for p in out if len(p["tags"]) < 10])
for p in out[:6]:
    print(p["series"], p["idx"], p["tags"])
