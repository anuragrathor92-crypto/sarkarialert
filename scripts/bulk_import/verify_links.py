"""Concurrent external link & domain verification tool for Sarkari Alert."""
import concurrent.futures, json, ssl, urllib.error, urllib.request
from pathlib import Path
from discover import official

ROOT = Path(__file__).resolve().parents[2]


def collect_urls():
    posts = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))["posts"]
    schemes = json.loads((ROOT / "data/schemes_directory.json").read_text(encoding="utf-8"))["records"]
    urls = set()
    for p in posts:
        for k in ("officialUrl", "notificationUrl", "applyUrl", "actionUrl", "otrUrl"):
            if p.get(k):
                urls.add(p[k])
        for _, u in p.get("extraLinks") or []:
            urls.add(u)
    for s in schemes:
        for k in ("officialUrl", "sourceUrl"):
            if s.get(k):
                urls.add(s[k])
    return sorted(urls)


def check_url(url):
    domain_ok = official(url)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SarkariAlertVerifier/1.1)"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return {"url": url, "domainApproved": domain_ok, "status": r.status, "finalUrl": r.geturl(), "note": ""}
    except urllib.error.HTTPError as e:
        return {"url": url, "domainApproved": domain_ok, "status": e.code, "finalUrl": e.geturl(), "note": str(e)}
    except Exception as e:
        return {"url": url, "domainApproved": domain_ok, "status": 0, "finalUrl": url, "note": str(e)}


if __name__ == "__main__":
    urls = collect_urls()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(check_url, urls))
    out = ROOT / "import-output/link-verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = sum(1 for r in results if 200 <= r["status"] < 400)
    approved = sum(1 for r in results if r["domainApproved"])
    print(f"Verified {len(results)} unique official URLs: domainApproved={approved}/{len(results)}, directHTTPS2xx/3xx={ok}/{len(results)}")
    for r in results:
        if not (200 <= r["status"] < 400):
            print("  NOTE:", r["status"], r["url"], "->", r["note"][:100])
