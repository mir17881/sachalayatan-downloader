"""
app.py
======
Sachalayatan Downloader — Web UI

Run:
    python app.py
Then open: http://localhost:5000
"""

import csv
import hashlib
import json
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from flask import Flask, Response, jsonify, render_template, request, send_from_directory

from sachalayatan_downloader import (
    BASE_URL,
    DELAY,
    get_article_urls_from_page,
    get_total_pages,
    save_html,
    scrape_article,
    session,
)

app = Flask(__name__)

DOWNLOADS_DIR      = Path("downloads")
REPORTS_DIR        = Path("reports")
BATCH_PROGRESS_FILE = Path("batch_progress.json")

DOWNLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


# ── Batch progress ─────────────────────────────────────────────────────────────

def _load_batch_progress():
    if BATCH_PROGRESS_FILE.exists():
        try:
            return json.loads(BATCH_PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_batch_progress(data):
    BATCH_PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _csv_key(filename, usernames):
    """Stable key: filename + hash of first 20 usernames (identifies the file without hashing all)."""
    sample = ",".join(usernames[:20])
    h = hashlib.md5(sample.encode()).hexdigest()[:8]
    return f"{Path(filename).stem}_{h}"


# ── Job state ──────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_pause_event = threading.Event()
_stop_event  = threading.Event()
_pause_event.set()   # not paused by default

_job = {
    "running":     False,
    "history":     [],   # SSE messages for replay on reconnect
    "subscribers": [],   # one queue per connected SSE client
}


def _broadcast(event_type, data):
    msg = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    with _lock:
        _job["history"].append(msg)
        for q in _job["subscribers"]:
            q.put(msg)


def _subscribe():
    q = queue.Queue()
    with _lock:
        history = list(_job["history"])
        _job["subscribers"].append(q)
    return q, history


def _unsubscribe(q):
    with _lock:
        if q in _job["subscribers"]:
            _job["subscribers"].remove(q)


# ── CSV ────────────────────────────────────────────────────────────────────────

def parse_csv_file(path_or_stream):
    """Load usernames from a file path or file-like object."""
    if isinstance(path_or_stream, Path):
        f = open(path_or_stream, encoding="utf-8-sig")
        close_after = True
    else:
        import io
        f = io.TextIOWrapper(path_or_stream, encoding="utf-8-sig")
        close_after = False
    try:
        reader = csv.DictReader(f)
        if "username" not in (reader.fieldnames or []):
            return None, "CSV must have a 'username' column header."
        return [
            row["username"].strip().lower()
            for row in reader
            if row.get("username", "").strip()
        ], None
    finally:
        if close_after:
            f.close()


# ── Report builder ─────────────────────────────────────────────────────────────

def build_report(usernames, total_done, total_failed, failed_list, timestamp, stopped=False):
    failed_rows = "".join(
        f"<tr>"
        f"<td>{f['username']}</td>"
        f"<td><a href=\"{f['url']}\" target=\"_blank\">{f['url']}</a></td>"
        f"<td>{f['error']}</td>"
        f"</tr>"
        for f in failed_list
    )
    failed_section = ""
    if failed_list:
        failed_section = f"""
        <h2>Failed Articles ({len(failed_list)})</h2>
        <table>
          <thead>
            <tr><th>User</th><th>URL</th><th>Error</th></tr>
          </thead>
          <tbody>{failed_rows}</tbody>
        </table>"""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Download Report — {timestamp}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           max-width: 960px; margin: 40px auto; padding: 0 24px 60px; color: #222; }}
    h1   {{ font-size: 22px; margin-bottom: 4px; }}
    h2   {{ font-size: 16px; margin: 32px 0 12px; }}
    .meta  {{ color: #666; font-size: 13px; margin-bottom: 32px; }}
    .stats {{ display: flex; gap: 20px; margin-bottom: 32px; flex-wrap: wrap; }}
    .stat  {{ background: #f5f5f5; border-radius: 8px; padding: 16px 24px; min-width: 120px; }}
    .stat .num   {{ font-size: 32px; font-weight: 700; }}
    .stat .num.ok   {{ color: #2d6a3f; }}
    .stat .num.bad  {{ color: #c0392b; }}
    .stat .label {{ font-size: 13px; color: #666; margin-top: 2px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th  {{ text-align: left; border-bottom: 2px solid #ddd; padding: 8px 10px; background: #f9f9f9; }}
    td  {{ border-bottom: 1px solid #eee; padding: 8px 10px; vertical-align: top; word-break: break-all; }}
    a   {{ color: #1a73e8; }}
    code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>Download Report{'— Stopped Early' if stopped else ''}</h1>
  <div class="meta">
    {'Stopped' if stopped else 'Completed'} {timestamp} &nbsp;·&nbsp;
    Output folder: <code>downloads/</code>
  </div>
  <div class="stats">
    <div class="stat">
      <div class="num">{len(usernames)}</div>
      <div class="label">Users</div>
    </div>
    <div class="stat">
      <div class="num ok">{total_done}</div>
      <div class="label">Articles saved</div>
    </div>
    <div class="stat">
      <div class="num {'bad' if total_failed else ''}">{total_failed}</div>
      <div class="label">Failed</div>
    </div>
  </div>
  {failed_section}
</body>
</html>"""


# ── Download thread ────────────────────────────────────────────────────────────

def _check_stop():
    """Wait while paused. Return True if stop was requested."""
    _pause_event.wait()
    return _stop_event.is_set()


def run_download(usernames):
    total_users         = len(usernames)
    total_articles_done = 0
    total_articles_fail = 0
    failed_list         = []
    failed_usernames    = set()
    stopped             = False

    with _lock:
        batch_meta = _job.pop("_batch", None)

    _broadcast("start", {"total_users": total_users})

    for user_idx, username in enumerate(usernames, 1):
        if _check_stop():
            stopped = True
            break

        _broadcast("user_start", {
            "username":    username,
            "user_idx":    user_idx,
            "total_users": total_users,
        })

        out_dir     = DOWNLOADS_DIR / username
        out_dir.mkdir(exist_ok=True)
        listing_url = f"{BASE_URL}/blog/{username}"

        try:
            resp = session.get(listing_url, timeout=15)
            resp.raise_for_status()
            soup        = BeautifulSoup(resp.text, "lxml")
            total_pages = get_total_pages(soup)

            seen     = set()
            all_urls = []

            first_links, _ = get_article_urls_from_page(listing_url, username, seen)
            all_urls.extend(first_links)

            for p in range(1, total_pages):
                if _check_stop():
                    stopped = True
                    break
                time.sleep(DELAY)
                try:
                    links, _ = get_article_urls_from_page(
                        f"{listing_url}?page={p}", username, seen
                    )
                    all_urls.extend(links)
                except Exception:
                    pass

            if stopped:
                break

            _broadcast("user_articles_found", {
                "username":       username,
                "total_articles": len(all_urls),
            })

            user_success = 0
            user_failed  = 0

            for art_idx, url in enumerate(all_urls, 1):
                if _check_stop():
                    stopped = True
                    break
                time.sleep(DELAY)
                try:
                    article = scrape_article(url)
                    save_html(article, out_dir, art_idx)
                    user_success        += 1
                    total_articles_done += 1
                    _broadcast("article_done", {
                        "username":       username,
                        "art_idx":        art_idx,
                        "total_articles": len(all_urls),
                        "title":          article["title"],
                        "url":            url,
                    })
                except Exception as e:
                    user_failed         += 1
                    total_articles_fail += 1
                    failed_list.append({"username": username, "url": url, "error": str(e)})
                    failed_usernames.add(username)
                    _broadcast("article_fail", {
                        "username":       username,
                        "art_idx":        art_idx,
                        "total_articles": len(all_urls),
                        "url":            url,
                        "error":          str(e),
                    })

            if stopped:
                break

            if user_failed:
                failed_usernames.add(username)

            _broadcast("user_done", {
                "username":    username,
                "user_idx":    user_idx,
                "total_users": total_users,
                "success":     user_success,
                "failed":      user_failed,
            })

        except Exception as e:
            failed_usernames.add(username)
            _broadcast("user_error", {
                "username":    username,
                "user_idx":    user_idx,
                "total_users": total_users,
                "error":       str(e),
            })

    # Save report
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_html = build_report(
        usernames, total_articles_done, total_articles_fail, failed_list, timestamp, stopped
    )
    filename = f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.html"
    (REPORTS_DIR / filename).write_text(report_html, encoding="utf-8")

    # Save batch progress if this was a batch download
    batch_next = None
    if batch_meta and not stopped:
        progress = _load_batch_progress()
        new_position = batch_meta["position"] + len(usernames)
        progress[batch_meta["key"]] = {
            "position":     new_position,
            "total":        batch_meta["total"],
            "last_updated": timestamp,
        }
        _save_batch_progress(progress)
        remaining = batch_meta["total"] - new_position
        batch_next = {
            "position":   new_position,
            "total":      batch_meta["total"],
            "remaining":  remaining,
            "batch_size": batch_meta["batch_size"],
        }

    _broadcast("complete", {
        "total_users":      total_users,
        "articles_done":    total_articles_done,
        "articles_failed":  total_articles_fail,
        "failed_list":      failed_list,
        "failed_usernames": sorted(failed_usernames),
        "report_file":      filename,
        "timestamp":        timestamp,
        "stopped":          stopped,
        "batch_next":       batch_next,
    })

    with _lock:
        _job["running"] = False


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    with _lock:
        return jsonify({"running": _job["running"]})


@app.route("/batch-info", methods=["POST"])
def batch_info():
    """Return current batch position for an uploaded CSV (no download started)."""
    csv_file = request.files.get("csv")
    if not csv_file:
        return jsonify({"error": "No file"}), 400
    all_users, err = parse_csv_file(csv_file.stream)
    if err:
        return jsonify({"error": err}), 400
    key      = _csv_key(csv_file.filename, all_users)
    progress = _load_batch_progress()
    entry    = progress.get(key, {})
    position = entry.get("position", 0)
    return jsonify({
        "key":      key,
        "total":    len(all_users),
        "position": position,
        "remaining": len(all_users) - position,
    })




@app.route("/start", methods=["POST"])
def start():
    with _lock:
        if _job["running"]:
            return jsonify({"error": "A download is already running."}), 400
        _job["running"] = True
        _job["history"] = []

    def abort(msg):
        with _lock:
            _job["running"] = False
        return jsonify({"error": msg}), 400

    mode = request.form.get("mode")

    if mode == "single":
        username = request.form.get("username", "").strip().lower()
        if not username:
            return abort("No username provided.")
        usernames = [username]

    elif mode in ("letters", "all"):
        csv_file = request.files.get("csv")
        if not csv_file or not csv_file.filename:
            return abort("Please choose a CSV file.")
        all_users, err = parse_csv_file(csv_file.stream)
        if err:
            return abort(err)
        if not all_users:
            return abort("The CSV file contains no usernames.")

        if mode == "letters":
            letters   = {l.lower() for l in request.form.getlist("letters")}
            usernames = [u for u in all_users if u and u[0] in letters]
            if not usernames:
                return abort("No users found for the selected letters.")
        else:
            usernames = all_users

    elif mode == "batch":
        csv_file = request.files.get("csv")
        if not csv_file or not csv_file.filename:
            return abort("Please choose a CSV file.")
        try:
            batch_size = int(request.form.get("batch_size", 100))
        except ValueError:
            return abort("Invalid batch size.")
        if batch_size not in (50, 100, 200):
            return abort("Batch size must be 50, 100, or 200.")

        all_users, err = parse_csv_file(csv_file.stream)
        if err:
            return abort(err)
        if not all_users:
            return abort("The CSV file contains no usernames.")

        key      = _csv_key(csv_file.filename, all_users)
        progress = _load_batch_progress()
        position = progress.get(key, {}).get("position", 0)

        if position >= len(all_users):
            return abort("All users in this CSV have already been downloaded. Reset to start over.")

        usernames = all_users[position : position + batch_size]

        # Store batch metadata so run_download can save progress on completion
        _job["_batch"] = {
            "key":       key,
            "position":  position,
            "batch_size": batch_size,
            "total":     len(all_users),
        }

    else:
        return abort("Invalid mode.")

    _pause_event.set()
    _stop_event.clear()
    thread = threading.Thread(target=run_download, args=(usernames,), daemon=True)
    thread.start()
    return jsonify({"ok": True, "count": len(usernames)})


@app.route("/pause", methods=["POST"])
def pause():
    _pause_event.clear()
    _broadcast("paused", {})
    return jsonify({"ok": True})


@app.route("/resume", methods=["POST"])
def resume():
    _pause_event.set()
    _broadcast("resumed", {})
    return jsonify({"ok": True})


@app.route("/stop", methods=["POST"])
def stop():
    _stop_event.set()
    _pause_event.set()   # unblock if currently paused
    return jsonify({"ok": True})


@app.route("/batch-reset", methods=["POST"])
def batch_reset():
    """Reset the saved position for a specific CSV key."""
    key = (request.json or {}).get("key")
    if not key:
        return jsonify({"error": "No key"}), 400
    progress = _load_batch_progress()
    if key in progress:
        del progress[key]
        _save_batch_progress(progress)
    return jsonify({"ok": True})


@app.route("/retry", methods=["POST"])
def retry():
    with _lock:
        if _job["running"]:
            return jsonify({"error": "A download is already running."}), 400
        _job["running"] = True
        _job["history"] = []

    data      = request.json or {}
    usernames = [u.strip().lower() for u in data.get("usernames", []) if u.strip()]
    if not usernames:
        with _lock:
            _job["running"] = False
        return jsonify({"error": "No usernames provided."}), 400

    _pause_event.set()
    _stop_event.clear()
    thread = threading.Thread(target=run_download, args=(usernames,), daemon=True)
    thread.start()
    return jsonify({"ok": True, "count": len(usernames)})


@app.route("/stream")
def stream():
    q, history = _subscribe()

    def generate():
        yield ": connected\n\n"
        for msg in history:
            yield msg
        try:
            while True:
                try:
                    msg = q.get(timeout=20)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            _unsubscribe(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORTS_DIR, filename)


if __name__ == "__main__":
    import webbrowser
    # Open browser automatically after server is ready
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5000")).start()
    print("\n  Sachalayatan Downloader")
    print("  Opening browser at: http://localhost:5000")
    print("  Keep this window open while using the app.\n")
    app.run(debug=False, threaded=True, port=5000)
