//正则表达式匹配：
var paths = [
    ["^/api/songs/chart/graphics/chart/([0-9]{1,3}).expert.json$", "https://raw.githubusercontent.com/smwlover36011/BandoriCustomMap/master/graphics/chart/$1.expert.json"],
    ["^/api/songs/chart/graphics/simulator/([0-9]{1,3}).expert.json$", "https://raw.githubusercontent.com/smwlover36011/BandoriCustomMap/master/graphics/simulator/$1.expert.json"],
    ["^/assets/(jp|en|cn|tw)/sound/bgm([0-9][0-9][0-9])_rip/bgm([0-9][0-9][0-9]).mp3$", "https://raw.githubusercontent.com/smwlover36011/BandoriCustomMap/master/music/bgm$2.mp3"],
    ["^/api/songs/all.5.json$", "https://raw.githubusercontent.com/smwlover36011/BandoriCustomMap/master/all/all.5.json"],
    ["^/api/bands/all.1.json$", "https://raw.githubusercontent.com/smwlover36011/BandoriCustomMap/master/all/all.1.json"],
    ["/assets/(jp|en|cn|tw)/musicjacket/([a-zA-Z0-9\_\-]*)_rip/jacket.png", "https://raw.githubusercontent.com/smwlover36011/BandoriCustomMap/master/musicjacket/$2.png"]
];


//主函数
addEventListener("fetch", async event => {
    event.respondWith(
        (async function () {
            var area_url = "https://bestdori.com/"
            var bestdori_url = new URL(area_url);
            var origin_url = new URL(event.request.url);
            var mypath = origin_url.pathname;
            
            for (var i = paths.length - 1; i >= 0; i--) {
                var patt = new RegExp(paths[i][0], "g");
                if (patt.test(mypath)) {
                    var newurl = mypath.replace(patt, paths[i][1]);
                    return new Response("", { "status": 302, "headers": { "Location": newurl } }); //生成302重定向请求
                }
            }

            //普通资源→反向代理
            var furl = origin_url;
            furl.host = bestdori_url.host;
            var request = new Request(event.request, { redirect: "follow" });
            request = new Request(furl, request);
            return await fetch(request);
        })()
    )
})