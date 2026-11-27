"""Auto-repair dead (404/410/DNS) applyUrl entries in data/posts.json using verified officialUrl fallback."""
from __future__ import annotations
import concurrent.futures as cf
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTS_PATH = ROOT / "data" / "posts.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def probe_status(url: str, timeout: int = 10) -> int:
    if not url or not url.startswith(("http://", "https://")):
        return 0
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return int(getattr(resp, "status", 200))
        except urllib.error.HTTPError as exc:
            if exc.code == 405 and method == "HEAD":
                continue
            return int(exc.code)
        except Exception:
            if method == "HEAD":
                continue
            return 0
    return 0


def repair_posts() -> int:
    if not POSTS_PATH.exists():
        return 0
    raw = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    posts = raw if isinstance(raw, list) else raw.get("posts", [])
    candidates = [
        p for p in posts
        if isinstance(p, dict)
        and p.get("applyUrl")
        and p.get("officialUrl")
        and p.get("applyUrl") != p.get("officialUrl")
    ]
    if not candidates:
        print("Repair Agent: 0 distinct applyUrl records to check.")
        return 0

    urls = sorted({p["applyUrl"] for p in candidates})
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        statuses = dict(zip(urls, ex.map(probe_status, urls)))

    repaired = 0
    for p in candidates:
        st = statuses.get(p["applyUrl"], 200)
        if st in (404, 410):
            off_st = probe_status(p["officialUrl"])
            if off_st in (200, 301, 302, 303, 307, 308, 403):
                p["applyUrl"] = p["officialUrl"]
                p["applyLinkType"] = "GENERAL_RECRUITMENT_PORTAL"
                repaired += 1
                print(f"Repaired dead applyUrl ({st}) -> officialUrl for {p.get('id')}")

    if repaired:
        out = posts if isinstance(raw, list) else {**raw, "posts": posts}
        POSTS_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Repair Agent complete: checked={len(urls)}, repaired={repaired}")
    return repaired


if __name__ == "__main__":
    repair_posts()
