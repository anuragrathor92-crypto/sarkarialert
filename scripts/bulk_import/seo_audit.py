"""Automated technical SEO, JobPosting schema & Core Web Vitals health audit."""
import argparse
import datetime as dt
import html
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from build_site import BASE, ROOT, is_jobposting_eligible, load_site_config
from discover import get_ist


def audit_site(now=None):
    now = now or dt.datetime.now(get_ist())
    posts_data = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))
    active_by_id = {p["id"]: p for p in posts_data["posts"]}

    html_files = [
        ROOT / "index.html",
        ROOT / "404.html",
        ROOT / "sitemap/index.html",
        ROOT / "loans-and-cards/index.html",
        ROOT / "about/index.html",
        ROOT / "privacy/index.html",
        ROOT / "disclaimer/index.html",
    ]
    html_files.extend(sorted((ROOT / "category").glob("*/index.html")))
    html_files.extend(sorted((ROOT / "posts").glob("*/index.html")))

    errors = []
    warnings = []
    titles = []
    descs = []
    canonicals = set()
    indexable_canonicals = set()
    jobposting_urls = []
    expired_or_ineligible_jp = []
    cwv_issues = []
    related_missing = []

    for f in html_files:
        if not f.exists():
            errors.append(f"Missing generated file: {f.relative_to(ROOT).as_posix()}")
            continue
        rel = f.relative_to(ROOT).as_posix()
        txt = f.read_text(encoding="utf-8")

        robots_m = re.search(r'<meta name="robots" content="([^"]*)"', txt)
        robots = robots_m.group(1) if robots_m else ""
        is_noindex = "noindex" in robots.lower()

        t_m = re.search(r"<title>(.*?)</title>", txt, re.S)
        d_m = re.search(r'<meta name="description" content="([^"]*)"', txt)
        c_m = re.search(r'<link rel="canonical" href="([^"]*)"', txt)
        h1_cnt = len(re.findall(r"<h1\b", txt))

        title = html.unescape(t_m.group(1)) if t_m else ""
        desc = html.unescape(d_m.group(1)) if d_m else ""
        canonical = c_m.group(1) if c_m else ""

        if not title:
            errors.append(f"{rel}: missing <title>")
        elif len(title) > 70:
            errors.append(f"{rel}: <title> exceeds 70 chars ({len(title)}): {title}")
        if not desc:
            errors.append(f"{rel}: missing meta description")
        elif len(desc) < 70:
            errors.append(f"{rel}: short meta description ({len(desc)} chars)")
        elif len(desc) > 165:
            errors.append(f"{rel}: long meta description ({len(desc)} chars)")
        if not canonical.startswith(BASE):
            errors.append(f"{rel}: invalid canonical {canonical}")
        else:
            canonicals.add(canonical)
            if not is_noindex:
                indexable_canonicals.add(canonical)

        if h1_cnt != 1:
            errors.append(f"{rel}: expected 1 <h1>, found {h1_cnt}")
        if 'property="og:image"' not in txt or 'property="og:title"' not in txt:
            errors.append(f"{rel}: missing Open Graph tags")
        if 'name="viewport"' not in txt:
            cwv_issues.append(f"{rel}: missing viewport meta")
        if '<script defer src="' not in txt:
            cwv_issues.append(f"{rel}: missing deferred site.js")

        if not is_noindex:
            titles.append((rel, title))
            descs.append((rel, desc))

        # Related links check on active posts & schemes
        if rel.startswith("posts/") and not is_noindex and 'class="related-box"' not in txt:
            related_missing.append(rel)

        # Structured data audit
        for raw_ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', txt, re.S):
            try:
                parsed = json.loads(raw_ld)
            except json.JSONDecodeError as ex:
                errors.append(f"{rel}: invalid JSON-LD: {ex}")
                continue
            for item in (parsed if isinstance(parsed, list) else [parsed]):
                if item.get("@type") == "JobPosting":
                    pid = rel.split("/")[1] if rel.startswith("posts/") else ""
                    post_obj = active_by_id.get(pid)
                    if is_noindex or not post_obj or not is_jobposting_eligible(post_obj, now):
                        expired_or_ineligible_jp.append(rel)
                    else:
                        for req_k in ("title", "description", "datePosted", "validThrough", "employmentType", "hiringOrganization", "jobLocation", "url"):
                            if not item.get(req_k):
                                errors.append(f"{rel}: JobPosting missing {req_k}")
                        vt = item.get("validThrough", "")
                        try:
                            dt_v = dt.datetime.fromisoformat(vt)
                            if dt_v.tzinfo is None:
                                dt_v = dt_v.replace(tzinfo=now.tzinfo)
                            if dt_v <= now:
                                expired_or_ineligible_jp.append(rel)
                        except ValueError:
                            errors.append(f"{rel}: JobPosting invalid validThrough {vt}")
                        jobposting_urls.append(canonical)

    dup_titles = [k for k, c in Counter(t for _, t in titles).items() if c > 1]
    dup_descs = [k for k, c in Counter(d for _, d in descs).items() if c > 1]
    if dup_titles:
        errors.append(f"Duplicate titles ({len(dup_titles)}): {dup_titles[:5]}")
    if dup_descs:
        errors.append(f"Duplicate descriptions ({len(dup_descs)}): {dup_descs[:5]}")
    if expired_or_ineligible_jp:
        errors.append(f"Expired or ineligible JobPosting markup found: {expired_or_ineligible_jp}")
    if related_missing:
        errors.append(f"Posts missing related internal links block: {related_missing[:5]}")
    if cwv_issues:
        errors.extend(cwv_issues[:10])

    # Sitemap audit
    sm_path = ROOT / "sitemap.xml"
    sm_urls = []
    sm_lastmods = []
    if not sm_path.exists():
        errors.append("Missing sitemap.xml")
    else:
        tree = ET.fromstring(sm_path.read_text(encoding="utf-8"))
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for url_el in tree.findall("s:url", ns):
            loc = url_el.findtext("s:loc", default="", namespaces=ns)
            lm = url_el.findtext("s:lastmod", default="", namespaces=ns)
            if loc:
                sm_urls.append(loc)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lm):
                errors.append(f"Invalid sitemap lastmod for {loc}: {lm}")
            else:
                sm_lastmods.append(lm)
        missing_in_sm = sorted(indexable_canonicals - set(sm_urls))
        extra_in_sm = sorted(set(sm_urls) - indexable_canonicals)
        if missing_in_sm:
            errors.append(f"Indexable URLs missing from sitemap.xml: {missing_in_sm[:5]}")
        if extra_in_sm:
            errors.append(f"Non-indexable/orphan URLs in sitemap.xml: {extra_in_sm[:5]}")
        if len(set(sm_lastmods)) < 2:
            warnings.append("sitemap.xml has uniform single lastmod across all URLs")

    # RSS Feed audit
    feed_path = ROOT / "feed.xml"
    feed_items = 0
    if not feed_path.exists():
        errors.append("Missing feed.xml")
    else:
        ftree = ET.fromstring(feed_path.read_text(encoding="utf-8"))
        feed_items = len(ftree.findall("./channel/item"))
        if feed_items == 0:
            errors.append("feed.xml has 0 items")

    # Core Web Vitals & Asset budget check
    css_txt = (ROOT / "assets/style.css").read_text(encoding="utf-8") if (ROOT / "assets/style.css").exists() else ""
    if "content-visibility" not in css_txt:
        errors.append("assets/style.css missing content-visibility optimization")
    for asset_rel in ("assets/favicon.svg", "assets/og-card.png"):
        if not (ROOT / asset_rel).exists():
            errors.append(f"Missing SEO brand asset: {asset_rel}")

    cfg = load_site_config()
    integrations = {
        "googleSearchConsole": (cfg.get("googleSearchConsole") or {}).get("status"),
        "googleIndexingApi": (cfg.get("googleIndexingApi") or {}).get("status"),
        "googleAnalytics4": "CONFIGURED" if (cfg.get("googleAnalytics4") or {}).get("measurementId") else "AWAITING_ID",
        "bingWebmaster": "CONFIGURED" if (cfg.get("bingWebmaster") or {}).get("verificationMetaContent") else "AWAITING_TOKEN",
        "googleAdSense": "CONFIGURED" if (cfg.get("googleAdSense") or {}).get("publisherId") else "AWAITING_PUBLISHER_ID",
    }

    report = {
        "checkedAt": now.isoformat(),
        "passed": len(errors) == 0,
        "pagesAudited": len(html_files),
        "indexablePages": len(indexable_canonicals),
        "uniqueTitles": len({t for _, t in titles}),
        "duplicateTitlesCount": len(dup_titles),
        "uniqueDescriptions": len({d for _, d in descs}),
        "duplicateDescriptionsCount": len(dup_descs),
        "eligibleJobPostingPages": len(jobposting_urls),
        "expiredOrIneligibleJobPostings": len(expired_or_ineligible_jp),
        "sitemapUrls": len(sm_urls),
        "sitemapDistinctLastmods": sorted(set(sm_lastmods)),
        "rssFeedItems": feed_items,
        "cssBytes": (ROOT / "assets/style.css").stat().st_size if (ROOT / "assets/style.css").exists() else 0,
        "ogImageBytes": (ROOT / "assets/og-card.png").stat().st_size if (ROOT / "assets/og-card.png").exists() else 0,
        "integrations": integrations,
        "errors": errors,
        "warnings": warnings,
    }
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--output", default="import-output/seo-report.json")
    args = ap.parse_args()

    rep = audit_site()
    out_p = Path(args.output)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"SEO Audit: pages={rep['pagesAudited']}, indexable={rep['indexablePages']}, "
        f"JobPostings={rep['eligibleJobPostingPages']}, badJP={rep['expiredOrIneligibleJobPostings']}, "
        f"dupTitles={rep['duplicateTitlesCount']}, dupDescs={rep['duplicateDescriptionsCount']}, "
        f"sitemap={rep['sitemapUrls']} ({len(rep['sitemapDistinctLastmods'])} lastmod dates), "
        f"rss={rep['rssFeedItems']}, errors={len(rep['errors'])}"
    )
    if rep["errors"]:
        for err in rep["errors"][:15]:
            print("  SEO ERROR:", err)
        if args.strict:
            raise SystemExit(1)
