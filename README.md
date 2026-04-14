# Sachalayatan PDF Downloader

Downloads all articles from a Sachalayatan writer's blog as individual PDFs.

**Repo:** https://github.com/mir17881/sachalayatan-downloader

---

## Setup (one time)

```
git clone https://github.com/mir17881/sachalayatan-downloader.git
cd sachalayatan-downloader
pip install requests beautifulsoup4 lxml playwright
playwright install chromium
```

---

## Usage

```
python sachalayatan_pdf.py <username>
```

Examples:

```
python sachalayatan_pdf.py odin
python sachalayatan_pdf.py mir178
python sachalayatan_pdf.py all
```

`all` downloads every article on the entire site.

PDFs are saved to a folder named after the username:

```
odin/
  001_Article_Title.pdf
  002_Next_Article.pdf
  ...
```

---

## Notes

- Works on Windows and Mac — steps are identical
- Open terminal (PowerShell on Windows, Terminal on Mac) and run from inside the `sachalayatan-downloader` folder
- 1.5 s delay between requests to avoid overloading the site
- If an article fails it is logged and skipped; the rest continue

---

## Updating

```
git pull
```

---

## If Claude is helping you update the code

Key selectors in `scrapeArticle()` — update these if the site's HTML changes:

```python
# Title
soup.find("h1", class_="title") or soup.find("h2", class_="title")

# Date
soup.find("span", class_="date-display-single") or soup.find("span", class_="submitted")

# Body
soup.find("div", id=re.compile(r"^node-\d+-content$"))

# Pagination
soup.find("li", class_="pager-last")
```
