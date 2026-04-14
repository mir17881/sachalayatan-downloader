# Sachalayatan Article Downloader

A one-page web tool that lets any Sachalayatan writer enter their username and download all their articles as individual PDFs, packaged in a single ZIP file.

**Live site (once deployed):** `https://<your-github-username>.github.io/sachalayatan-downloader/`

---

## How it works (no server required)

Everything runs in the visitor's browser:

1. The page fetches the writer's blog listing via a public CORS proxy (`api.allorigins.win`)
2. It walks through all pagination pages and collects every article URL
3. Each article is fetched, parsed, and converted to a PDF using `html2pdf.js`
4. All PDFs are bundled into a ZIP file named `<username>_articles.zip` using `JSZip`
5. The visitor clicks "Download ZIP" — extracting it gives a folder named after the username

No data ever touches a server you control. The only external services used are:
- `api.allorigins.win` — free CORS proxy
- Google Fonts (Bengali: Hind Siliguri)
- CDN libraries (JSZip, html2pdf.js)

---

## Deploying to GitHub Pages

### Prerequisites
- A GitHub account (free tier is fine)
- Git installed, or use the GitHub web interface

### Step 1 — Create a GitHub repository

1. Go to [github.com](https://github.com) and click **New repository**
2. Name it `sachalayatan-downloader` (or anything you like)
3. Set it to **Public** (required for free GitHub Pages)
4. Click **Create repository**

### Step 2 — Upload the files

**Option A — via GitHub web interface (no Git needed):**

1. Open your new repository on GitHub
2. Click **Add file → Upload files**
3. Drag and drop `index.html` into the upload area
4. Click **Commit changes**

**Option B — via Git (command line):**

```powershell
cd "C:\Users\mir17\OneDrive\Documents\Claude Code\sachalayatan-downloader"
git init
git add index.html README.md
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<YOUR-GITHUB-USERNAME>/sachalayatan-downloader.git
git push -u origin main
```

### Step 3 — Enable GitHub Pages

1. In your repository, click **Settings** (top navigation)
2. Scroll down to the **Pages** section in the left sidebar
3. Under **Source**, select **Deploy from a branch**
4. Choose **main** branch, folder **/ (root)**
5. Click **Save**

GitHub will show a message like:
> "Your site is live at `https://<your-username>.github.io/sachalayatan-downloader/`"

It usually goes live within **1–2 minutes**.

---

## Using the tool

1. Open the live URL in any modern browser (Chrome or Edge recommended)
2. Type your Sachalayatan username (e.g. `mir178`) in the input box
3. Click **Download All** (or press Enter)
4. Watch the progress log — each article is fetched and converted in real time
5. When done, click **⬇ Download ZIP**
6. Extract the ZIP — you'll get a folder named after your username containing one PDF per article
   - Files are numbered and named: `001_Article_Title.pdf`, `002_Next_Article.pdf`, etc.

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
| PDFs are image-based | html2pdf renders via canvas | Text is not searchable; this is a known trade-off for Bengali script support |

---

## Updating the tool

If you need to make changes (e.g., the site's HTML structure changes):

1. Edit `index.html` locally
2. Commit and push to the same repository
3. GitHub Pages redeploys automatically within ~1 minute

If Claude is helping you update it, share this README and the current `index.html` — the selectors that matter are in the `scrapeArticle()` function:

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

If Sachalayatan updates its layout, these selectors may need to change.

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
