"""
sachalayatan_downloader.py
==========================
Download all articles from a Sachalayatan blog as HTML files.

Usage:
    python sachalayatan_downloader.py <username>   # one writer
    python sachalayatan_downloader.py all          # entire site

Each article is saved as:
    <username>/001_Article_Title/index.html
    <username>/001_Article_Title/images/...

Setup (one time):
    pip install requests beautifulsoup4 lxml
"""

import sys
import time
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "http://www.sachalayatan.com"
DELAY    = 1.5   # seconds between requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Drupal sub-paths that are never article slugs
SKIP_ARTICLE_PATHS = {"track", "feed", "contact", "edit", "delete", "revisions"}

# Path segments that are never usernames (used in "all" mode)
SKIP_SEGMENTS = {
    "node", "admin", "user", "blog", "sites", "modules", "themes",
    "misc", "files", "system", "logout", "search", "taxonomy",
    "comment", "aggregator", "tracker", "contact",
}

session = requests.Session()
session.headers.update(HEADERS)


# ─────────────────────────────────────────────
#  SCRAPING HELPERS
# ─────────────────────────────────────────────

def get_total_pages(soup):
    """Return total number of listing pages (1-indexed)."""
    pager = soup.find("li", class_="pager-last")
    if pager:
        a = pager.find("a")
        if a and "page=" in a.get("href", ""):
            return int(a["href"].split("page=")[-1]) + 1
    pages = set()
    for a in soup.select("a[href*='page=']"):
        try:
            pages.add(int(a["href"].split("page=")[-1]))
        except ValueError:
            pass
    return max(pages) + 1 if pages else 1


def get_article_urls_from_page(listing_url, username, seen):
    """Fetch one listing page and return new article URLs."""
    resp = session.get(listing_url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    urls = []
    if username and username != "all":
        pattern = re.compile(
            rf"^(?:https?://(?:www\.)?sachalayatan\.com)?/{re.escape(username)}/([\w-]+)$"
        )
        for a in soup.select("a[href]"):
            href = a["href"].split("?")[0].split("#")[0]
            m = pattern.match(href)
            if not m:
                continue
            if m.group(1) in SKIP_ARTICLE_PATHS:
                continue
            full = href if href.startswith("http") else BASE_URL + href
            if full not in seen:
                seen.add(full)
                urls.append(full)
    else:
        pattern = re.compile(
            r"^(?:https?://(?:www\.)?sachalayatan\.com)?/([a-zA-Z0-9_-]+)/([\w-]+)$"
        )
        for a in soup.select("a[href]"):
            href = a["href"].split("?")[0].split("#")[0]
            m = pattern.match(href)
            if not m:
                continue
            if m.group(1) in SKIP_SEGMENTS:
                continue
            if m.group(2) in SKIP_ARTICLE_PATHS:
                continue
            full = href if href.startswith("http") else BASE_URL + href
            if full not in seen:
                seen.add(full)
                urls.append(full)

    return urls, soup


def scrape_article(url):
    """Fetch and parse a single article. Returns a dict."""
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # Title
    title_el = soup.find("h1", class_="title") or soup.find("h2", class_="title")
    title = title_el.get_text(strip=True) if title_el else url.split("/")[-1]

    # Date
    date_el = (
        soup.find("span", class_="date-display-single") or
        soup.find("span", class_="submitted")
    )
    date_str = date_el.get_text(strip=True) if date_el else ""

    # Author
    author_el = soup.find("a", href=re.compile(r"^/[a-zA-Z0-9_-]+$"))
    author = author_el.get_text(strip=True) if author_el else ""

    # Body
    body_el = soup.find("div", id=re.compile(r"^node-\d+-content$"))
    if not body_el:
        body_el = soup.select_one(".node-content, .field-items, article .content")

    body_html = ""
    if body_el:
        for tag in body_el.select(
            ".addthis_toolbox, .addthis_default_style, .social-share, "
            ".sharethis-wrapper, .links, script, noscript"
        ):
            tag.decompose()
        for img in body_el.select("img[src]"):
            src = img["src"]
            if not src.startswith("http"):
                img["src"] = BASE_URL + ("" if src.startswith("/") else "/") + src
        body_html = str(body_el)

    # Comments (Drupal standard markup)
    comments_html = ""
    comments_section = (
        soup.find("div", id="comments") or
        soup.find("section", id="comments") or
        soup.find("div", class_=re.compile(r"\bcomments\b"))
    )
    if not comments_section:
        comment_nodes = soup.select(
            "div.comment, div.comment-wrapper, "
            "div[class*='comment-'], li.comment"
        )
        if comment_nodes:
            wrapper = soup.new_tag("div", id="comments")
            header = soup.new_tag("h2")
            header.string = f"মন্তব্য ({len(comment_nodes)})"
            wrapper.append(header)
            for c in comment_nodes:
                wrapper.append(c)
            comments_section = wrapper

    if comments_section:
        for tag in comments_section.select(
            ".links, .comment-links, script, noscript, "
            "a[href*='/edit'], a[href*='/delete'], a[href*='/reply']"
        ):
            tag.decompose()
        for img in comments_section.select("img[src]"):
            src = img["src"]
            if not src.startswith("http"):
                img["src"] = BASE_URL + ("" if src.startswith("/") else "/") + src
        comments_html = str(comments_section)

    return {
        "title":         title,
        "date_str":      date_str,
        "author":        author,
        "body_html":     body_html,
        "comments_html": comments_html,
        "url":           url,
    }


# ─────────────────────────────────────────────
#  FILENAME HELPER
# ─────────────────────────────────────────────

def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    name = re.sub(r"_+", "_", name)
    return name[:100] or "article"


# ─────────────────────────────────────────────
#  HTML OUTPUT
# ─────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link
    href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600&family=Inter:wght@400;500&display=swap"
    rel="stylesheet"
  />
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Hind Siliguri', 'Inter', sans-serif;
      font-size: 15px;
      line-height: 1.8;
      color: #1a1a2e;
      max-width: 780px;
      margin: 40px auto;
      padding: 0 24px 60px;
    }}
    .header {{
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid #e0e0e0;
    }}
    h1 {{
      font-size: 24px;
      font-weight: 600;
      line-height: 1.4;
      margin-bottom: 8px;
    }}
    .meta {{
      font-size: 12px;
      color: #666;
    }}
    .meta a {{ color: #2d6a9f; text-decoration: none; }}
    .body img {{
      max-width: 100%;
      height: auto;
      display: block;
      margin: 1em 0;
    }}
    .body p  {{ margin-bottom: 1em; }}
    .body blockquote {{
      border-left: 3px solid #ccc;
      padding-left: 16px;
      margin: 1em 0;
      color: #555;
    }}
    .body iframe {{ max-width: 100%; }}
    .comments {{
      margin-top: 48px;
      border-top: 2px solid #e0e0e0;
      padding-top: 24px;
    }}
    .comments h2 {{
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 20px;
      color: #333;
    }}
    .comment {{
      border-bottom: 1px solid #eee;
      padding: 16px 0;
    }}
    .comment:last-child {{ border-bottom: none; }}
    .comment .submitted {{
      font-size: 12px;
      color: #888;
      margin-bottom: 6px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>{title}</h1>
    <div class="meta">
      {date_str}{author_line}
      &nbsp;·&nbsp; <a href="{url}" target="_blank">Original</a>
    </div>
  </div>
  <div class="body">
    {body_html}
  </div>
  {comments_section}
</body>
</html>"""


def _download_images(soup_fragment, images_dir, img_names_used):
    """Download all img[src] in a BeautifulSoup fragment to images_dir, rewrite srcs. Returns count."""
    count = 0
    for img in soup_fragment.select("img[src]"):
        src = img["src"]
        if not src.startswith("http"):
            continue
        try:
            resp = session.get(src, timeout=10)
            resp.raise_for_status()

            raw_name = src.split("/")[-1].split("?")[0]
            img_name = sanitize_filename(raw_name) if raw_name else ""
            if not img_name:
                img_name = f"img_{count}"
            if "." not in img_name:
                ct = resp.headers.get("content-type", "image/jpeg")
                ext = ct.split("/")[-1].split(";")[0].strip()
                img_name = f"{img_name}.{ext}"
            base, _, ext = img_name.rpartition(".")
            candidate = img_name
            n = 1
            while candidate in img_names_used:
                candidate = f"{base}_{n}.{ext}"
                n += 1
            img_name = candidate
            img_names_used.add(img_name)

            images_dir.mkdir(exist_ok=True)
            (images_dir / img_name).write_bytes(resp.content)
            img["src"] = f"images/{img_name}"
            count += 1
        except Exception:
            pass  # leave original absolute src on failure
    return count


def save_html(article, out_dir, idx):
    """Save article as index.html with images downloaded to images/ subfolder."""
    folder_name = f"{idx:03d}_{sanitize_filename(article['title'])}"
    article_dir = out_dir / folder_name
    article_dir.mkdir(exist_ok=True)

    images_dir = article_dir / "images"
    img_names_used = set()

    # Process article body
    body_soup = BeautifulSoup(article["body_html"], "lxml")
    img_count = _download_images(body_soup, images_dir, img_names_used)
    body_html = "".join(str(t) for t in body_soup.body.children) if body_soup.body else article["body_html"]

    # Process comments
    comments_section = ""
    if article.get("comments_html"):
        c_soup = BeautifulSoup(article["comments_html"], "lxml")
        img_count += _download_images(c_soup, images_dir, img_names_used)
        comments_html = "".join(str(t) for t in c_soup.body.children) if c_soup.body else article["comments_html"]
        comments_section = f'<div class="comments">{comments_html}</div>'

    author_line = f" &nbsp;·&nbsp; {article['author']}" if article["author"] else ""
    html = HTML_TEMPLATE.format(
        title=article["title"].replace("<", "&lt;").replace(">", "&gt;"),
        date_str=article["date_str"],
        author_line=author_line,
        url=article["url"],
        body_html=body_html,
        comments_section=comments_section,
    )
    (article_dir / "index.html").write_text(html, encoding="utf-8")
    return article_dir, img_count


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python sachalayatan_downloader.py <username|all>")
        sys.exit(1)

    username = sys.argv[1].strip().lower()
    all_mode = username == "all"
    listing_url = BASE_URL if all_mode else f"{BASE_URL}/blog/{username}"
    out_dir = Path("sachalayatan_all" if all_mode else username)
    out_dir.mkdir(exist_ok=True)

    print(f"\n=== Sachalayatan Downloader ===")
    print(f"Mode   : {'all articles on site' if all_mode else username}")
    print(f"Output : {out_dir.resolve()}\n")

    # ── Step 1: discover total pages ──
    print("Step 1: Discovering listing pages…")
    resp = session.get(listing_url, timeout=15)
    resp.raise_for_status()
    first_soup = BeautifulSoup(resp.text, "lxml")
    total_pages = get_total_pages(first_soup)
    print(f"  Found {total_pages} page(s)\n")

    # ── Step 2: collect all article URLs ──
    print("Step 2: Collecting article URLs…")
    seen = set()
    all_urls = []

    first_links, _ = get_article_urls_from_page(listing_url, username, seen)
    all_urls.extend(first_links)
    print(f"  Page 1 / {total_pages}: {len(first_links)} article(s)")

    for p in range(1, total_pages):
        page_url = f"{listing_url}?page={p}"
        time.sleep(DELAY)
        try:
            links, _ = get_article_urls_from_page(page_url, username, seen)
            all_urls.extend(links)
            print(f"  Page {p + 1} / {total_pages}: {len(links)} article(s)")
        except Exception as e:
            print(f"  Page {p + 1}: FAILED — {e}")

    print(f"\n  Total unique articles: {len(all_urls)}\n")

    if not all_urls:
        print("No articles found. Check the username and try again.")
        sys.exit(1)

    # ── Step 3: save HTML ──
    print("Step 3: Saving articles…")
    failed = []

    for idx, url in enumerate(all_urls, 1):
        time.sleep(DELAY)
        print(f"  [{idx:3d}/{len(all_urls)}] {url}")
        try:
            article = scrape_article(url)
            _, img_count = save_html(article, out_dir, idx)
            img_note = f"  ({img_count} image{'s' if img_count != 1 else ''})" if img_count else ""
            print(f"          ✓ {article['title']}{img_note}")
        except Exception as e:
            print(f"          ✗ FAILED — {e}")
            failed.append((url, str(e)))

    # ── Done ──
    success = len(all_urls) - len(failed)
    print(f"\n{'='*40}")
    print(f"Done.  {success} succeeded,  {len(failed)} failed.")
    print(f"Output saved to: {out_dir.resolve()}")

    if failed:
        print(f"\nFailed articles:")
        for url, err in failed:
            print(f"  {url}  —  {err}")


if __name__ == "__main__":
    main()
