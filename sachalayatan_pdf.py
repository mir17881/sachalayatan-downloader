"""
sachalayatan_pdf.py
===================
Download all articles from a Sachalayatan blog as individual PDFs.

Usage:
    python sachalayatan_pdf.py <username>        # one writer
    python sachalayatan_pdf.py all               # entire site

Each article is saved as:
    <username>/001_Article_Title.pdf
    <username>/002_Next_Article.pdf
    ...

Setup (one time):
    pip install requests beautifulsoup4 lxml playwright
    playwright install chromium
"""

import sys
import time
import re
import os
from pathlib import Path
from datetime import datetime

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
        # Specific user: /<username>/<digits or slug>
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
        # All mode: any /<user>/<slug>
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

    # Body: Drupal wraps in div#node-NNNNN-content
    body_el = soup.find("div", id=re.compile(r"^node-\d+-content$"))
    if not body_el:
        body_el = soup.select_one(".node-content, .field-items, article .content")

    body_html = ""
    if body_el:
        # Strip share widgets and scripts
        for tag in body_el.select(
            ".addthis_toolbox, .addthis_default_style, .social-share, "
            ".sharethis-wrapper, .links, script, noscript"
        ):
            tag.decompose()

        # Rewrite relative image src → absolute
        for img in body_el.select("img[src]"):
            src = img["src"]
            if not src.startswith("http"):
                img["src"] = BASE_URL + ("" if src.startswith("/") else "/") + src

        body_html = str(body_el)

    return {
        "title":    title,
        "date_str": date_str,
        "author":   author,
        "body_html": body_html,
        "url":      url,
    }


# ─────────────────────────────────────────────
#  PDF GENERATION
# ─────────────────────────────────────────────

PDF_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <link
    href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600&family=Inter:wght@400;500&display=swap"
    rel="stylesheet"
  />
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Hind Siliguri', 'Inter', sans-serif;
      font-size: 14px;
      line-height: 1.8;
      color: #1a1a2e;
      padding: 0;
    }}
    .header {{
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid #e0e0e0;
    }}
    h1 {{
      font-size: 22px;
      font-weight: 600;
      line-height: 1.4;
      margin-bottom: 8px;
      font-family: 'Hind Siliguri', 'Inter', sans-serif;
    }}
    .meta {{
      font-size: 12px;
      color: #666;
      font-family: 'Inter', sans-serif;
    }}
    .meta a {{ color: #2d6a9f; text-decoration: none; }}
    .body img {{
      max-width: 100%;
      height: auto;
    }}
    .body p  {{ margin-bottom: 1em; }}
    .body blockquote {{
      border-left: 3px solid #ccc;
      padding-left: 16px;
      margin: 1em 0;
      color: #555;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>{title}</h1>
    <div class="meta">
      {date_str}{author_line}
      <br>Source: <a href="{url}">{url}</a>
    </div>
  </div>
  <div class="body">
    {body_html}
  </div>
</body>
</html>"""


def render_pdf(playwright_page, article, output_path):
    """Render one article to PDF using the Playwright page object."""
    author_line = (
        f" &nbsp;·&nbsp; {article['author']}" if article["author"] else ""
    )
    html = PDF_TEMPLATE.format(
        title=article["title"].replace("<", "&lt;").replace(">", "&gt;"),
        date_str=article["date_str"],
        author_line=author_line,
        url=article["url"],
        body_html=article["body_html"],
    )
    playwright_page.set_content(html, wait_until="networkidle")
    playwright_page.pdf(
        path=str(output_path),
        format="A4",
        margin={"top": "20mm", "right": "20mm", "bottom": "20mm", "left": "20mm"},
        print_background=True,
    )


# ─────────────────────────────────────────────
#  FILENAME HELPER
# ─────────────────────────────────────────────

def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    name = re.sub(r"_+", "_", name)
    return name[:100] or "article"


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python sachalayatan_pdf.py <username|all>")
        sys.exit(1)

    username = sys.argv[1].strip().lower()
    all_mode = username == "all"
    listing_url = BASE_URL if all_mode else f"{BASE_URL}/blog/{username}"
    out_dir = Path("sachalayatan_all" if all_mode else username)
    out_dir.mkdir(exist_ok=True)

    print(f"\n=== Sachalayatan PDF Downloader ===")
    print(f"Mode     : {'all articles on site' if all_mode else username}")
    print(f"Output   : {out_dir.resolve()}\n")

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

    # ── Step 3: generate PDFs ──
    print("Step 3: Generating PDFs…")
    failed = []

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context()
        page    = context.new_page()

        for idx, url in enumerate(all_urls, 1):
            time.sleep(DELAY)
            print(f"  [{idx:3d}/{len(all_urls)}] {url}")
            try:
                article  = scrape_article(url)
                filename = f"{idx:03d}_{sanitize_filename(article['title'])}.pdf"
                out_path = out_dir / filename
                render_pdf(page, article, out_path)
                print(f"          ✓ {article['title']}")
            except Exception as e:
                print(f"          ✗ FAILED — {e}")
                failed.append((url, str(e)))

        context.close()
        browser.close()

    # ── Done ──
    success = len(all_urls) - len(failed)
    print(f"\n{'='*40}")
    print(f"Done.  {success} succeeded,  {len(failed)} failed.")
    print(f"PDFs saved to: {out_dir.resolve()}")

    if failed:
        print(f"\nFailed articles:")
        for url, err in failed:
            print(f"  {url}  —  {err}")


if __name__ == "__main__":
    main()
