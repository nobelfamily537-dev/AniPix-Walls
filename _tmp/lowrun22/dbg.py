import requests, json, time
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json"}
W="https://wallhaven.cc/api/v1/search"
qs=["akira","beastars","death parade","hajime no ippo","dorohedoro","kokuriko-zaka kara","from up on poppy hill","initial d","samurai champloo","gedo senki","tales from earthsea","chihayafuru","bungou stray dogs","the ancient magus bride","mahou tsukai no yome","86 eighty six","the cat returns","ranma","oregoru","oregairu","noragami","hyouka","spice and wolf","mushoku tensei","erased","fire force","a silent voice","girls band cry","horimiya","natsume yuujinchou"]
for q in qs:
    try:
        r=requests.get(W,params={"q":q,"categories":"010","purity":"100","ratios":"portrait","atleast":"1080x1920","sorting":"favorites","order":"desc"},headers=UA,timeout=25)
        j=r.json(); tot=j.get("meta",{}).get("total"); n=len(j.get("data",[]))
        print("%-28s total=%s n=%s"%(q,tot,n),flush=True)
    except Exception as e:
        print(q,"ERR",type(e).__name__,flush=True)
    time.sleep(0.7)
