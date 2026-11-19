import json
import requests
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/html,*/*"}
T = [
 ("konachan.net json","https://konachan.net/post.json",{"tags":"cowboy_bebop","limit":3}),
 ("konachan.com json","https://konachan.com/post.json",{"tags":"cowboy_bebop","limit":3}),
 ("yande.re json","https://yande.re/post.json",{"tags":"cowboy_bebop","limit":3}),
 ("safebooru.donmai","https://safebooru.donmai.us/posts.json",{"tags":"cowboy_bebop","limit":3}),
 ("danbooru","https://danbooru.donmai.us/posts.json",{"tags":"cowboy_bebop","limit":3}),
 ("safebooru.org","https://safebooru.org/index.php",{"page":"dapi","s":"post","q":"index","tags":"cowboy_bebop","limit":3}),
 ("gelbooru","https://gelbooru.com/index.php",{"page":"dapi","s":"post","q":"index","tags":"cowboy_bebop","limit":3}),
 ("alphacoders search","https://wall.alphacoders.com/search.php",{"search":"cowboy+bebop"}),
 ("anime-pictures","https://anime-pictures.net/posts",{"search_tag":"cowboy_bebop"}),
 ("zerochan","https://www.zerochan.net/Cowboy+Bebop",{}),
 ("e-shuushuu","https://e-shuushuu.net/search/results/",{"tags":"cowboy+bebop"}),
 ("waifu.im","https://api.waifu.im/search",{"included_tags":"waifu"}),
 ("nekosapi","https://api.nekosapi.com/v4/images/random",{}),
 ("reddit json","https://www.reddit.com/r/AnimeWallpaper/search.json",{"q":"cowboy bebop","restrict_sr":1,"limit":3}),
 ("i.redd.it test","https://i.redd.it/",{}),
 ("images.alphacoders","https://images.alphacoders.com/",{}),
 ("anilist","https://graphql.anilist.co",{}),
]
for name,url,params in T:
    try:
        r = requests.get(url, params=params, headers=UA, timeout=25)
        body = r.text[:120].replace("\n"," ")
        print("%-22s %s len=%d %s" % (name, r.status_code, len(r.content), body), flush=True)
    except Exception as e:
        print("%-22s ERR %s %s" % (name, type(e).__name__, str(e)[:80]), flush=True)
