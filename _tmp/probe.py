import requests, json
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
urls=[
 ("safebooru","https://safebooru.donmai.us/posts.json?tags=nisekoi&limit=2"),
 ("danbooru-main","https://danbooru.donmai.us/posts.json?tags=nisekoi&limit=2"),
 ("konachan","https://konachan.net/post.json?tags=nisekoi&limit=2"),
 ("yande","https://yande.re/post.json?tags=nisekoi&limit=2"),
 ("gelbooru","https://gelbooru.com/index.php?page=dapi&s=post&q=index&tags=nisekoi&json=1&limit=2"),
 ("wallhaven","https://wallhaven.cc/api/v1/search?q=nisekoi"),
 ("zerochan","https://www.zerochan.net/nisekoi"),
 ("pinterest-pin","https://www.pinterest.com/pin/1136459287615194/"),
 ("pinimg","https://i.pinimg.com/736x/00/00/00/00000000000000000000000000000000.jpg"),
 ("waifu.pics","https://api.waifu.pics/sfw/waifu"),
 ("nekos.best","https://nekos.best/api/v2/neko"),
 ("anime-api","https://api.jikan.moe/v4/anime?q=nisekoi&limit=1"),
 ("safebooru-html","https://safebooru.org/index.php?page=post&s=list&tags=nisekoi"),
 ("pixiv","https://www.pixiv.net/ajax/search/artworks/nisekoi"),
]
for n,u in urls:
    try:
        r=requests.get(u,headers=UA,timeout=30)
        print(n, r.status_code, len(r.content), r.headers.get("content-type","")[:40], flush=True)
        if n in ("konachan","yande","gelbooru","safebooru","danbooru-main"):
            print("   head:", r.text[:160].replace("\n"," "), flush=True)
    except Exception as e:
        print(n,"ERR",e, flush=True)
