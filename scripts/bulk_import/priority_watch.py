"""Read-only priority post/source watcher. Signals require verification; no auto-publishing."""
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

from discover import official, ROOT

UA = "SarkariAlertPriorityWatch/1.0"
MAX_BYTES = 2_000_000
INTERVALS = {"results": 15, "admit-card": 15, "answer-key": 30,
             "latest-jobs": 30, "exam-date": 30, "admission": 30,
             "upcoming-jobs": 120, "scholarship": 120}
STATE = ROOT / ".watch-state/state.json"
REPORT = ROOT / "import-output/priority-watch.json"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def get(url, limit=MAX_BYTES, headers=None):
    if not official(url):
        raise ValueError("unapproved_domain")
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=8) as res:
        return res.status, dict(res.headers.items()), res.read(limit + 1)

def allowed_by_robots(url):
    u = urllib.parse.urlsplit(url)
    robots = urllib.parse.urlunsplit((u.scheme, u.netloc, "/robots.txt", "", ""))
    try:
        _, _, body = get(robots, 100000)
        if len(body) > 100000:
            return False
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(body.decode("utf-8", "replace").splitlines())
        return parser.can_fetch(UA, url)
    except urllib.error.HTTPError as e:
        return e.code in (404, 410)
    except Exception:
        return False

def probe(url, previous):
    if not official(url):
        return {"status": "UNAPPROVED_DOMAIN"}
    if not allowed_by_robots(url):
        return {"status": "ROBOTS_UNAVAILABLE_OR_DISALLOWED"}
    headers = {}
    if previous.get("etag"):
        headers["If-None-Match"] = previous["etag"]
    if previous.get("lastModified"):
        headers["If-Modified-Since"] = previous["lastModified"]
    try:
        status, h, body = get(url, headers=headers)
        if len(body) > MAX_BYTES:
            return {"status": "SIZE_LIMIT", "http": status}
        if url.split("?")[0].lower().endswith(".pdf") and not body.lstrip().startswith(b"%PDF"):
            return {"status": "PDF_MISMATCH", "http": status}
        if not body.lstrip().startswith(b"%PDF"):
            title = re.search(rb"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            if title and re.search(rb"(404|page not found|access denied|application closed|service unavailable)", title.group(1), re.I):
                return {"status": "POSSIBLE_SOFT_ERROR", "http": status}
        digest = hashlib.sha256(body).hexdigest()
        old = previous.get("hash")
        return {"status": "POSSIBLE_SOURCE_CHANGE" if old and digest != old else
                ("UNCHANGED" if old else "BASELINE"),
                "http": status, "hash": digest,
                "etag": next((v for k,v in h.items() if k.lower()=="etag"), ""),
                "lastModified": next((v for k,v in h.items() if k.lower()=="last-modified"), "")}
    except urllib.error.HTTPError as e:
        if e.code == 304 and previous.get("hash"):
            return {"status": "UNCHANGED", "http": 304}
        if e.code in (301,302,303,307,308):
            target = urllib.parse.urljoin(url, e.headers.get("Location", ""))
            return {"status": "REDIRECT_REVIEW", "http": e.code,
                    "redirectOfficial": official(target)}
        return {"status": "BROKEN_HTTP" if e.code in (404,410) else "HTTP_RECHECK", "http": e.code}
    except Exception:
        return {"status": "CONNECTION_RECHECK"}

def targets(posts):
    out = {}
    for p in posts:
        interval = INTERVALS.get(p.get("category"), 1440)
        for field in ("notificationUrl", "officialUrl", "actionUrl", "applyUrl"):
            url = p.get(field)
            if not isinstance(url, str) or not url or not official(url):
                continue
            minutes = max(30, min(interval, 60)) if field == "applyUrl" else interval
            item = out.setdefault(url, {"interval": minutes, "posts": []})
            item["interval"] = min(minutes, item["interval"])
            item["posts"].append({"id": p["id"], "role": field, "category": p.get("category"),
                                  "applyType": p.get("applyLinkType") if field == "applyUrl" else None})
    return out

def due(target_map, state, now, limit=80):
    ranked = []
    for url, item in target_map.items():
        previous = state.get(url, {})
        try:
            elapsed = (now - dt.datetime.fromisoformat(previous["checkedAt"])).total_seconds()/60
        except (KeyError, ValueError, TypeError):
            elapsed = 1_000_000
        if elapsed >= item["interval"]:
            ranked.append((-(elapsed-item["interval"]), item["interval"], url))
    # Avoid concentrating requests on a single official host.
    chosen = []
    hosts = {}
    for _, _, url in sorted(ranked):
        host = urllib.parse.urlsplit(url).hostname
        if hosts.get(host, 0) >= 2:
            continue
        hosts[host] = hosts.get(host, 0)+1
        chosen.append(url)
        if len(chosen) >= limit:
            break
    return chosen, len(ranked)

def watch(posts, state, now, probe_fn=probe, limit=80):
    items = targets(posts)
    state = {k:v for k,v in state.items() if k in items}
    selected, due_count = due(items, state, now, limit)
    stamp = now.isoformat()
    checks = []
    # Run at most one request chain per host concurrently.
    groups = {}
    for url in selected:
        groups.setdefault(urllib.parse.urlsplit(url).hostname, []).append(url)
    def check_group(urls):
        return [(url, probe_fn(url, state.get(url, {}))) for url in urls]
    with cf.ThreadPoolExecutor(max_workers=10) as executor:
        for group in executor.map(check_group, groups.values()):
            for url, result in group:
                previous = state.get(url, {})
                state[url] = {**previous, **result, "checkedAt": stamp}
                checks.append({"url": url, **result, "checkedAt": stamp,
                               "affectedPosts": items[url]["posts"]})
    counts = {}
    for check in checks:
        status = check["status"]
        counts[status] = counts.get(status, 0)+1
    report = {"checkedAt": stamp, "registeredSources": len(items),
              "dueBeforeRun": due_count, "checked": len(checks),
              "dueNotChecked": max(0, due_count-len(checks)), "counts": counts,
              "checks": checks, "publishedPosts": 0,
              "note": "Change signals and HTTP checks are not fact or application-form verification."}
    return state, report

def main():
    posts = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))["posts"]
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    new_state, report = watch(posts, state, dt.datetime.now(dt.timezone.utc))
    STATE.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(new_state, ensure_ascii=False), encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="checks"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
