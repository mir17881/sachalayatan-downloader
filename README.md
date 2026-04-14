# Sachalayatan Article Downloader

Two tools in one repo — use whichever fits your situation:

| | Web tool | Python script |
|---|---|---|
| **Who it's for** | Any writer, no setup | Admin / power user |
| **Speed** | Slow (proxy rate limits) | Fast (direct connection) |
| **Setup** | None — open a URL | `pip install` + one command |
| **Bengali text** | ✓ | ✓ (headless Chromium) |
| **"all" mode** | ✓ | ✓ |

**Live web tool:** https://mir17881.github.io/sachalayatan-downloader/

**GitHub repo:** https://github.com/mir17881/sachalayatan-downloader

---

## Python script (fast, for power users)

### Setup — one time only

```powershell
pip install requests beautifulsoup4 lxml playwright
playwright install chromium
```

### Usage

```powershell
# Download one writer's articles
python sachalayatan_pdf.py mir178

# Download every article on the entire site
python sachalayatan_pdf.py all
```

PDFs are saved to a folder named after the username (e.g. `mir178\001_Title.pdf`).  
For `all` mode the folder is named `sachalayatan_all\`.

### How to get the script

Clone the repo:

```powershell
git clone https://github.com/mir17881/sachalayatan-downloader.git
cd sachalayatan-downloader
```

Or just download `sachalayatan_pdf.py` directly from the repo.

---

## Web tool (no setup, for writers)

### How it works (no server required)

Everything runs in the visitor's browser:

1. The page fetches the blog listing via a public CORS proxy (`api.allorigins.win`)
2. It walks through all pagination pages and collects every article URL
3. Each article is fetched, parsed, and converted to a PDF using `html2pdf.js`
4. All PDFs are bundled into a ZIP file using `JSZip`
5. The visitor clicks **⬇ Download ZIP** — extracting it gives a folder of individual PDFs

No data ever touches a server you control. The only external services used are:
- `api.allorigins.win` — free CORS proxy
- Google Fonts (Bengali: Hind Siliguri)
- CDN libraries (JSZip, html2pdf.js)

---

## Using the tool

1. Open the live URL in any modern browser (Chrome or Edge recommended)
2. Type a username or `all` in the input box (see modes below)
3. Click **Download All** (or press Enter)
4. Watch the progress log — each article is fetched and converted in real time
5. When done, click **⬇ Download ZIP**
6. Extract the ZIP to get the folder of PDFs

### Download modes

| Input | What it downloads | ZIP file | Folder inside ZIP |
|---|---|---|---|
| `mir178` (any username) | All articles by that writer | `mir178_articles.zip` | `mir178/` |
| `all` | Every article on sachalayatan.com | `sachalayatan_all_articles.zip` | `sachalayatan_all/` |

> **Warning:** `all` mode crawls the entire site and may take many hours depending on total article count. A confirmation dialog will appear before it starts. Keep your browser open throughout.

PDFs are numbered and named: `001_Article_Title.pdf`, `002_Next_Article.pdf`, etc.

---

## What the PDFs contain

Each PDF includes:
- Article title
- Publication date
- Source URL (links back to the original post)
- Full article body (text, inline images if they load)

Bengali text renders correctly because the page loads the **Hind Siliguri** font from Google Fonts.

---

## Known limitations

| Issue | Why | Workaround |
|---|---|---|
| Slow for large archives | 1.6 s delay between requests (polite crawling) | Let it run; 50 articles ≈ 5–7 minutes |
| CORS proxy may be slow | `allorigins.win` is a free shared service | Retry if it times out |
| Images may be missing | Cross-origin image loading is browser-restricted | Text and layout are always preserved |
| PDFs are image-based | html2pdf renders via canvas | Text is not searchable; trade-off for Bengali script support |
| `all` mode is very slow | Thousands of articles, 1.6 s each | Run overnight; browser must stay open |

---

## Deploying an updated version

The site is already live. To push changes:

1. Edit `index.html` locally
2. Commit and push:

```powershell
cd "C:\Users\mir17\OneDrive\Documents\Claude Code\sachalayatan-downloader"
git add index.html README.md
git commit -m "describe your change"
git push
```

GitHub Pages redeploys automatically within ~1 minute.

### If Claude is helping you update the code

Share this README and the current `index.html`. The key selectors (may need updating if Sachalayatan changes its HTML) are in `scrapeArticle()`:

```javascript
// Title:
doc.querySelector('h1.title, h2.title, h1.page-header')

// Date:
doc.querySelector('span.date-display-single, span.submitted')

// Body:
doc.querySelector('div[id^="node-"][id$="-content"]')

// Pagination:
doc.querySelector('li.pager-last a')
```

The "all" mode article link pattern is in `parseArticleLinks()` — it matches any `/<username>/<numeric-id>` path while skipping reserved Drupal segments (node, admin, user, blog, sites, etc.) defined in `SKIP_SEGMENTS`.

---

## Deploying a fresh copy (for co-authors or forks)

If someone else wants their own hosted copy:

1. Fork https://github.com/mir17881/sachalayatan-downloader on GitHub
2. Go to the forked repo → **Settings → Pages**
3. Set source to **Deploy from branch → main → / (root)**
4. The site goes live at `https://<their-username>.github.io/sachalayatan-downloader/`

No code changes needed — the tool works for any Sachalayatan username.

---

## File structure

```
sachalayatan-downloader/
├── index.html   ← the entire tool (single file, no build step)
└── README.md    ← this file
```

---

## Credits

Built for Sachalayatan writers by mir178.  
Uses [JSZip](https://stuk.github.io/jszip/), [html2pdf.js](https://ekoopmans.github.io/html2pdf.js/), and [allorigins.win](https://allorigins.win/).
