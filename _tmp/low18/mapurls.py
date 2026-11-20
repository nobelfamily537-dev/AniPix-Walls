import json, time
import requests
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Referer":"https://konachan.net/"}
TAGS=["sono_bisque_doll_wa_koi_wo_suru","tengen_toppa_gurren_lagann","yoko_littner","nia_teppelin",
"seishun_buta_yarou","sakurajima_mai","re:zero_kara_hajimeru_isekai_seikatsu","rem_(re:zero)",
"emilia_(re:zero)","gundam","darling_in_the_franxx","zero_two_(darling_in_the_franxx)",
"yuru_camp","shiraishi_rin","oomachi_nadeshiko","inuyama_aoi","cyberpunk:_edgerunners","lucy_(cyberpunk)",
"kanojo_okarishimasu","mizuhara_chizuru","megumin","aqua_(konosuba)","darkness_(konosuba)",
"kono_subarashii_sekai_ni_shukufuku_wo!","makise_kurisu","steins;gate","shiina_mayuri",
"fullmetal_alchemist","edward_elric","winry_rockbell","riza_hawkeye","code_geass","lamperouge_lelouch",
"c.c.","kouzuki_kallen","kirisaki_chitoge","onodera_kosaki","nisekoi","kitagawa_marin","gojou_wakana"]
want=set(int(p["pid"]) for p in json.load(open("_tmp/low18/picks.json")))
print("want", len(want), flush=True)
found={}
for tag in TAGS:
    for page in (1,2,3):
        try:
            r=requests.get("https://konachan.net/post.json",params={"tags":tag+" rating:s","limit":100,"page":page},headers=UA,timeout=30)
            js=r.json() if r.status_code==200 else []
        except Exception as e:
            print("ERR",tag,type(e).__name__,flush=True); js=[]
        for p in js:
            if p.get("id") in want:
                found[p["id"]]=dict(sample=p.get("sample_url") or p.get("jpeg_url"), file=p.get("file_url"),
                                    w=p.get("width"), h=p.get("height"))
        print(tag,"p%d"%page,"n=",len(js),"found_total=",len(found),flush=True)
        if len(js)<100: break
        time.sleep(0.6)
print("MISSING", sorted(want-set(found))[:20], len(want-set(found)), flush=True)
# probe download behaviour for a couple
for pid,info in list(found.items())[:2]:
    for label,url,hdr in [("file+ref",info["file"],UA),("file+noref",info["file"],{"User-Agent":UA["User-Agent"]}),
                          ("sample",info["sample"],UA)]:
        try:
            rr=requests.get(url,headers=hdr,timeout=30)
            print("PROBE",pid,label,rr.status_code,len(rr.content),flush=True)
        except Exception as e:
            print("PROBE",pid,label,"ERR",type(e).__name__,flush=True)
json.dump(found,open("_tmp/low18/urlmap.json","w"))
print("saved",len(found),flush=True)
