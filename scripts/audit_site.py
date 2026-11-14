"""Static audit of the built site in public/: broken internal links, missing
images, pages without a title/description/h1, duplicate titles, products
without an affiliate link. Prints a summary and exits 1 if anything breaks.

    py scripts/audit_site.py
"""
import json, os, re, sys
from collections import Counter
from urllib.parse import unquote, urlparse

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
sys.stdout.reconfigure(encoding="utf-8")


def target_exists(path):
    p = os.path.join(ROOT, unquote(path).lstrip("/"))
    return os.path.isfile(p) or os.path.isfile(os.path.join(p, "index.html")) or os.path.isfile(p + ".html")


pages, broken, missing_img, meta_issues, titles = 0, Counter(), Counter(), [], Counter()
for dirpath, _, files in os.walk(ROOT):
    if "/bot" in dirpath.replace("\\", "/"):
        continue
    for f in files:
        if not f.endswith(".html") or re.match(r"google[0-9a-f]+\.html$", f):
            continue
        pages += 1
        rel = os.path.relpath(os.path.join(dirpath, f), ROOT).replace("\\", "/")
        html = open(os.path.join(dirpath, f), encoding="utf-8").read()
        if "noindex" not in html:
            t = re.search(r"<title>(.*?)</title>", html, re.S)
            titles[t.group(1).strip() if t else ""] += 1
            if not t or not re.search(r'<meta name="description" content="[^"]+', html) or "<h1" not in html:
                meta_issues.append(rel)
        for attr, url in re.findall(r'(href|src)="([^"#?]+)', html):
            u = urlparse(url)
            if u.scheme or u.netloc or url.startswith(("mailto:", "tel:", "data:", "javascript:")):
                continue
            if not url.startswith("/"):
                url = "/" + os.path.normpath(os.path.join(os.path.dirname(rel), url)).replace("\\", "/")
            if not target_exists(url):
                (missing_img if attr == "src" else broken)[url] += 1

data = json.load(open(os.path.join(os.path.dirname(ROOT), "data", "products.json"), encoding="utf-8"))
live = [p for p in data if p.get("published", True)]
no_link = [p["slug"] for p in live if not re.match(r"https://(link\.amazon|amzn\.to|www\.amazon\.com)/", p.get("affiliateUrl", ""))]
dup_titles = {t: n for t, n in titles.items() if n > 1}

print(f"pages {pages}, live products {len(live)}")
print(f"broken links {sum(broken.values())}: {list(broken.items())[:10]}")
print(f"missing images/scripts {sum(missing_img.values())}: {list(missing_img.items())[:10]}")
print(f"pages missing title/description/h1 {len(meta_issues)}: {meta_issues[:10]}")
print(f"duplicate titles {len(dup_titles)}: {list(dup_titles.items())[:5]}")
print(f"products without affiliate link {len(no_link)}: {no_link[:10]}")
sys.exit(1 if broken or missing_img or no_link else 0)
