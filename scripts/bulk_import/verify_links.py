"""Concurrent internal + external link, PDF, and domain verification tool for Sarkari Alert."""
import argparse, concurrent.futures, json, posixpath, re, ssl, sys, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path
from discover import official

ROOT = Path(__file__).resolve().parents[2]
SITE_BASE = "https://anuragrathor92-crypto.github.io/sarkarialert/"


class _HrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.refs.append(d["href"].strip())
        elif tag in ("link", "script", "img"):
            u = (d.get("href") or d.get("src") or "").strip()
            if u:
                self.refs.append(u)


def check_internal_links(root=ROOT):
    """Verify every internal href/src and sitemap URL maps to an actual built file."""
    html_files = sorted(
        list(root.glob("*.html"))
        + list((root / "category").glob("*/index.html"))
        + list((root / "posts").glob("*/index.html"))
        + list((root / "tools").glob("index.html"))
        + list((root / "loans-and-cards").glob("index.html"))
        + list((root / "about").glob("index.html"))
        + list((root / "privacy").glob("index.html"))
        + list((root / "disclaimer").glob("index.html"))
    )
    checked = 0
    broken = []

    def resolve_local(page_rel, href):
        raw = href.split("#", 1)[0].split("?", 1)[0]
        if not raw or raw == "/":
            return root / "index.html" if raw == "/sarkarialert/" else None
        if raw.startswith("/sarkarialert/"):
            rel_path = raw[len("/sarkarialert/"):]
        elif raw.startswith("/"):
            return None  # Outside repo subpath
        else:
            page_dir = posixpath.dirname(page_rel)
            rel_path = posixpath.normpath(posixpath.join(page_dir, raw))
        if rel_path in ("", "."):
            return root / "index.html"
        if rel_path.startswith(".."):
            return None
        target = root / rel_path
        if target.is_dir() or raw.endswith("/"):
            target = target / "index.html"
        return target

    for fp in html_files:
        rel = fp.relative_to(root).as_posix()
        parser = _HrefParser()
        parser.feed(fp.read_text(encoding="utf-8", errors="ignore"))
        for href in parser.refs:
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "http://", "https://")):
                continue
            if href.startswith("/sarkarialert") or not href.startswith("/"):
                checked += 1
                target = resolve_local(rel, href)
                if target is None or not target.exists():
                    broken.append({"source": rel, "href": href, "reason": "missing_target"})
            elif href.startswith("/") and not href.startswith("//"):
                checked += 1
                broken.append({"source": rel, "href": href, "reason": "root_slash_outside_subpath"})

    sitemap = root / "sitemap.xml"
    if sitemap.exists():
        locs = re.findall(r"<loc>(.*?)</loc>", sitemap.read_text(encoding="utf-8", errors="ignore"))
        for loc in locs:
            checked += 1
            if not loc.startswith(SITE_BASE):
                broken.append({"source": "sitemap.xml", "href": loc, "reason": "invalid_base"})
                continue
            sub = loc[len(SITE_BASE):]
            target = (root / sub / "index.html") if (not sub or sub.endswith("/")) else (root / sub)
            if not target.exists():
                broken.append({"source": "sitemap.xml", "href": loc, "reason": "missing_target"})

    return {"pagesChecked": len(html_files), "linksChecked": checked, "broken": broken}


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
    referrals_path = ROOT / "data/referrals.json"
    if referrals_path.exists():
        ref = json.loads(referrals_path.read_text(encoding="utf-8"))
        for cat in ref.get("categories", []):
            for item in cat.get("items", []):
                if item.get("officialInfoUrl"):
                    urls.add(item["officialInfoUrl"])
    return sorted(urls)


def check_url(url):
    domain_ok = official(url)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SarkariAlertVerifier/1.2)"})
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
            ctype = r.headers.get("Content-Type", "")
            head = r.read(16000)
            note = ""
            if url.lower().endswith(".pdf") and "html" in ctype.lower() and not head.lstrip().startswith(b"%PDF"):
                return {"url": url, "domainApproved": domain_ok, "status": 422, "finalUrl": r.geturl(), "note": "PDF URL returned HTML fallback"}
            return {"url": url, "domainApproved": domain_ok, "status": r.status, "finalUrl": r.geturl(), "note": note}
    except urllib.error.HTTPError as e:
        return {"url": url, "domainApproved": domain_ok, "status": e.code, "finalUrl": e.geturl(), "note": str(e)}
    except Exception as e:
        return {"url": url, "domainApproved": domain_ok, "status": 0, "finalUrl": url, "note": str(e)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-internal", action="store_true", default=True)
    ap.add_argument("--skip-external", action="store_true")
    ap.add_argument("--strict-external", action="store_true")
    ap.add_argument("--output", default=str(ROOT / "import-output/link-verification.json"))
    args = ap.parse_args()

    internal = check_internal_links(ROOT)
    print(f"Internal link check: {internal['pagesChecked']} HTML pages, {internal['linksChecked']} links, broken={len(internal['broken'])}")
    for b in internal["broken"]:
        print("  BROKEN INTERNAL:", b)

    results = []
    bad_pdf = []
    pending_recheck = []
    if not args.skip_external:
        urls = collect_urls()
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            results = list(ex.map(check_url, urls))
        res_map = {r["url"]: r for r in results}
        posts = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))["posts"]
        for p in posts:
            if p.get("applyStatus") == "VERIFICATION_PENDING" or p.get("linkStatus") == "VERIFICATION_PENDING":
                target_u = p.get("applyUrl") or p.get("notificationUrl") or p.get("officialUrl")
                r = res_map.get(target_u, {})
                still_blocked = not (200 <= r.get("status", 0) < 400)
                pending_recheck.append({
                    "id": p["id"],
                    "url": target_u,
                    "httpStatus": r.get("status", 0),
                    "remainPending": still_blocked,
                    "note": r.get("note", ""),
                })
        ok = sum(1 for r in results if 200 <= r["status"] < 400)
        bad_pdf = [r for r in results if r["status"] == 422]
        hard_404 = [r for r in results if r["status"] in (404, 410)]
        print(f"External URL check: {len(results)} URLs, urllib2xx/3xx={ok}/{len(results)}, external404={len(hard_404)}, badPDF={len(bad_pdf)}, pendingRechecked={len(pending_recheck)}")
        for pr in pending_recheck:
            print("  PENDING RECHECK (2h):", pr["id"], pr["httpStatus"], pr["url"])
        for r in bad_pdf + hard_404:
            print("  EXTERNAL NOTICE:", r["status"], r["url"], r["note"])
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({"internal": internal, "external": results, "pendingRecheck": pending_recheck}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if bad_pdf or (args.strict_external and hard_404):
            sys.exit(1)

    if internal["broken"]:
        sys.exit(1)
