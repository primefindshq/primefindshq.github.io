"""
Tells IndexNow search engines (Bing, Yandex, Seznam, Naver; Bing's index also feeds
DuckDuckGo, Yahoo and ChatGPT search) which URLs exist or changed, so they crawl them
without waiting to discover them.

Run after a deploy is live:  py scripts/indexnow.py            (every URL in the sitemap)
                             py scripts/indexnow.py /guides/   (only URLs containing a path)

The key is data/site-config.json "indexNowKey"; build.py publishes it as /<key>.txt,
which is how the engines verify the submission comes from the site owner.
"""
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    with open(os.path.join(ROOT, "data", "site-config.json"), encoding="utf-8") as f:
        site = json.load(f)
    key = site["indexNowKey"]
    host = site["url"].split("//", 1)[-1].strip("/")
    with open(os.path.join(ROOT, "public", "sitemap.xml"), encoding="utf-8") as f:
        urls = re.findall(r"<loc>([^<]+)</loc>", f.read())
    if len(sys.argv) > 1:
        urls = [u for u in urls if any(part in u for part in sys.argv[1:])]
    # The API accepts up to 10,000 URLs per request.
    for i in range(0, len(urls), 10000):
        body = json.dumps({"host": host, "key": key, "keyLocation": f"https://{host}/{key}.txt",
                           "urlList": urls[i:i + 10000]}).encode()
        req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                print(f"Submitted {len(urls[i:i + 10000])} URLs: HTTP {r.status}")
        except urllib.error.HTTPError as e:
            print(f"IndexNow refused the batch: HTTP {e.code} {e.read()[:200]!r}")


if __name__ == "__main__":
    main()
