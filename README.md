# Sachalayatan Downloader

Downloads all articles from Sachalayatan writers as HTML files, with comments and images.

---

## Every day use (after setup is done)

**Windows** — double-click `start.bat`
**Mac** — double-click `start.command`

That's it. Your browser opens automatically. When finished, close the black terminal window to stop the app.

---

## Using the app

Once the browser opens at `http://localhost:5000`:

### Download a single user
1. Select **Single User**
2. Type the username
3. Click **Start Download**

### Download by letter
1. Select **By Letter**
2. Click the letters you want (e.g. A, B, C) — they turn blue when selected
3. Click **Choose File** and select your CSV file
4. Click **Start Download**
   This downloads all users from the CSV whose username starts with those letters.

### Download all users
1. Select **All Users**
2. Click **Choose File** and select your CSV file
3. Click **Start Download**
   This downloads every username in the CSV.

### While downloading
- **Top bar** — shows overall progress across all users
- **Second bar** — shows progress for the current user's articles
- **Live log** — shows each article as it is saved (green = success, red = failed)

### When done
A report appears showing how many articles were saved and a list of anything that failed.
The report is also saved to the `reports/` folder inside the project.

---

## Where are the downloaded files?

Inside the project folder:

```
sachalayatan-downloader/
  downloads/
    tanvir_alamgir/
      001_Article_Title/
        index.html        ← open this in any browser to read the article
        images/           ← images are here (only if the article had images)
      002_Next_Article/
        index.html
    another_user/
      ...
  reports/
    report_2026-04-14_15-30.html
```

---

## One-time setup (do this once, never again)

### Step 1 — Install Python (if not already installed)

**Windows:**
1. Go to https://www.python.org/downloads/
2. Click the big **Download Python** button
3. Run the installer
4. **On the first screen: tick the box that says "Add Python to PATH"** before clicking Install

**Mac:**
1. Go to https://www.python.org/downloads/
2. Click **Download Python** and run the installer
3. Follow the steps — no special options needed

---

### Step 2 — Download this project

Go to the GitHub page, click the green **Code** button → **Download ZIP**.
Unzip it anywhere you like (e.g. your Desktop).

---

### Step 3 — Open a terminal inside the project folder

**Windows:**
1. Open the `sachalayatan-downloader` folder in File Explorer
2. Click the address bar at the top of the window
3. Type `powershell` and press Enter

**Mac:**
1. Open the `sachalayatan-downloader` folder in Finder
2. Right-click the folder → **New Terminal at Folder**

---

### Step 4 — Run the setup file

**Windows** — double-click `setup.bat`

**Mac** — double-click `setup.command`
(First time on Mac: right-click → Open → Open to bypass the security warning)

The setup file will install all required packages automatically and tell you when it's done. You only need to run it once.

---

### Step 5 — Prepare your CSV file

Create a CSV file with any name (e.g. `writers.csv`) anywhere on your computer.

Open it in any text editor (Notepad on Windows, TextEdit on Mac). It must have `username` as the first column header, with one username per line:

```
username
tanvir_alamgir
odin
mir178
another_user
```

Save it wherever you like. When using the app, you will be asked to choose this file — it does not need to be inside the project folder.

---

### Step 6 — First launch on Mac (one-time security step)

macOS will block `start.command` the first time because it was downloaded from the internet.

1. Right-click `start.command`
2. Click **Open**
3. Click **Open** again on the warning dialog

After this, double-clicking will work normally.

---

### Done

From now on, just double-click `start.bat` (Windows) or `start.command` (Mac) to start.

---

## Stopping the app

Close the black terminal window that opened when you double-clicked the start file.

---

## Troubleshooting

**"python is not recognized" (Windows)**
Python was not added to PATH. Reinstall Python and tick **"Add Python to PATH"** on the first screen.

**"pip is not recognized" (Windows)**
Open PowerShell in the project folder and run: `python -m pip install requests beautifulsoup4 lxml flask`

**"Permission denied" on start.command (Mac)**
Open Terminal, go to the project folder, and run: `chmod +x start.command` — then try again.

**"Address already in use"**
Something is already using port 5000. Open `app.py` in a text editor, find `port=5000` near the bottom, change it to `port=5001`, then go to `http://localhost:5001`.

**Browser opens but page is blank**
The terminal window was closed. Double-click the start file again.

---

## For developers

Key selectors in `scrape_article()` — update if the site's HTML changes:

```python
# Title
soup.find("h1", class_="title") or soup.find("h2", class_="title")

# Date
soup.find("span", class_="date-display-single") or soup.find("span", class_="submitted")

# Body
soup.find("div", id=re.compile(r"^node-\d+-content$"))

# Comments
soup.find("div", id="comments")

# Pagination
soup.find("li", class_="pager-last")
```
