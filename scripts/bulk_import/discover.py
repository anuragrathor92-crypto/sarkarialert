"""Discover notice URLs, monitor UP RTE 2027-28, and verify official links; never copy third-party prose."""
import argparse, datetime as dt, json, re, ssl, time, urllib.request, urllib.parse, urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://sarkariresult.com.cm/"
UA = "SarkariAlertDiscovery/1.1"
HOST = "sarkariresult.com.cm"
PAGES = {
    "latest-jobs": "latest-jobs/",
    "results": "result/",
    "admit-card": "admit-card/",
    "answer-key": "answer-key/",
    "admission": "admission/",
    "documents": "document-verification/",
    "10th-iti": "10th-iti-job/",
    "outsourcing": "outsoursing-sewa-yojana-job/",
    "syllabus": "syllabus/",
}
EXCLUDED = set(PAGES.values()) | {
    "", "contact/", "contact-us/", "privacy-policy/", "disclaimer/",
    "about-us/", "about/", "more/", "feed/", "sarkari-result/", "wp-login.php"
}
ALLOWED = {
    # Official recruitment portals verified against the corresponding notices, 26 Nov 2026.
    "recruitment.csir.res.in", "www.csir.res.in", "goashipyard.ibtexamination.com", "ibpsreg.ibps.in",
    "www.ibps.in", "ibps.in", "www.rrbapply.gov.in", "rrbapply.gov.in",
    "www.joinindiannavy.gov.in", "www.joinindianarmy.nic.in", "joinindianarmy.nic.in",
    "www.aees.gov.in", "aees.gov.in", "aees.onlineregistrationforms.com",
    "www.sidbi.in", "sidbi.in", "sbi.co.in", "www.sbi.co.in", "bank.sbi", "www.bank.sbi",
    "sbi.bank.in", "www.sbi.bank.in", "www.joinindiancoastguard.gov.in",
    "www.clat2027.consortiumofnlus.ac.in", "clat2027.consortiumofnlus.ac.in",
    "exams.nta.ac.in", "www.nielit.gov.in", "www.nielit.in", "student.nielit.gov.in",
    "eshram.gov.in", "pmuy.gov.in", "pmsuryaghar.gov.in", "www.pmuy.gov.in",
    "apps.cbexams.com", "afcat.edcil.co.in", "apply.upessc.org",
    "www.nlcindia.in", "nlcindia.in", "pmvidyalaxmi.co.in", "www.pmvidyalaxmi.co.in",
    "www.standupmitra.in", "standupmitra.in", "pmegp.msme.gov.in",
    "pmsvanidhi.mohua.gov.in", "www.uok.ac.in", "uok.ac.in",
    "iimcat.ac.in", "www.iimcat.ac.in", "gate2027.iitm.ac.in",
    "www.bbmb.gov.in", "bbmb.gov.in", "www.apprenticeshipindia.gov.in", "apprenticeshipindia.gov.in",
    "careers.bhel.in", "www.ecil.co.in", "ecil.co.in", "nats.education.gov.in",
    "aiimsgorakhpur.edu.in", "www.aiimsbilaspur.edu.in", "aiimsbilaspur.edu.in",
    "www.bel-india.in", "bel-india.in", "hal-india.co.in", "www.hal-india.co.in",
    "www.assamrifles.gov.in", "assamrifles.gov.in", "assamrifles.mha.gov.in",
    "www.mponline.gov.in", "mponline.gov.in", "www.rrccr.com", "rrccr.com",
    "www.rrcnr.org", "rrcnr.org", "bseh.org.in", "www.bseh.org.in",
    "www.eximbankindia.in", "eximbankindia.in", "recruitment.sjvn.co.in",
    "nsap.dord.gov.in", "blasrecruit.in", "www.blasrecruit.in",
    "ukpsc.net.in", "www.ukpsc.net.in", "iforms.mponline.gov.in",
    "www.hpsbys.in", "hpsbys.in", "www.kudumbashree.org", "kudumbashree.org",
    "nationalinsurance.nic.co.in",
    "powergrid.in", "www.powergrid.in", "careers.powergrid.in",
    "gailonline.com", "www.gailonline.com", "gailebank.gail.co.in",
    "cpcle26.onlineregistrationform.org", "upanganwadibharti.in",
    "sbi.bank.in", "recruitment.sbi.bank.in",
    "becil.com", "www.becil.com", "becilregistration.in",
    "manitnt.samarth.edu.in", "niperahmnt.samarth.edu.in",
    "nsic.co.in", "www.nsic.co.in", "career.nsic.co.in",
    "nplindia.in", "www.nplindia.in",
    "ukssscrecruitment.in", "cdn.digialm.com",
    "goashipyard.in", "www.goashipyard.in",
    "recruitment.icmr.org.in", "apply.upessc.org",
}
UP_RTE_URL = "https://rte25.upsdc.gov.in/"
UP_RTE_FALLBACK_URL = "https://basiceducation.up.gov.in/hi"


def get_ist():
    try:
        return ZoneInfo("Asia/Kolkata")
    except ZoneInfoNotFoundError:
        return dt.timezone(dt.timedelta(hours=5, minutes=30), name="IST")


def official(url):
    try:
        u = urllib.parse.urlsplit(url)
        h = (u.hostname or "").lower()
        return (
            u.scheme == "https"
            and u.username is None
            and u.password is None
            and u.port in (None, 443)
            and (h in ALLOWED or h.endswith((".gov.in", ".nic.in", ".ac.in")))
            and h not in {"gov.in", "nic.in", "ac.in"}
        )
    except ValueError:
        return False


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.depth += 1
        if tag == "a":
            self.current = (dict(attrs).get("href", ""), self.depth > 0)

    def handle_endtag(self, tag):
        if tag == "li":
            self.depth = max(0, self.depth - 1)
        if tag == "a" and self.current:
            self.links.append(self.current)
            self.current = None


class SameHost(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).hostname != HOST or urllib.parse.urlsplit(newurl).scheme != "https":
            raise ValueError("External or non-HTTPS redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain"})
    with urllib.request.build_opener(SameHost()).open(request, timeout=20) as r:
        raw = r.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Page too large")
        return raw.decode(r.headers.get_content_charset() or "utf-8", errors="replace")


def article_url(href, base=BASE):
    u = urllib.parse.urlsplit(urllib.parse.urljoin(base, href))
    path = u.path.strip("/") + "/"
    if u.hostname != HOST or u.scheme != "https" or path in EXCLUDED or not re.fullmatch(r"[a-z0-9][a-z0-9-]{5,}/", path):
        return None
    if not re.search(r"20(?:2[0-9]|3[0-9])|recruitment|result|admit|answer|yojana|scholarship|apprentice|online-form", path):
        return None
    return BASE + path


def _fetch_strict_ipv4(url, timeout=25):
    """Fetch HTTPS URL using strict certificate validation, preferring IPv4 to avoid IPv6 blackholes."""
    import socket
    orig_getaddrinfo = socket.getaddrinfo

    def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        res = orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        return res or orig_getaddrinfo(host, port, family, type, proto, flags)

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Connection": "close",
        },
    )
    socket.getaddrinfo = ipv4_only
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(350_000).decode(r.headers.get_content_charset() or "utf-8", errors="replace")
    finally:
        socket.getaddrinfo = orig_getaddrinfo


def check_up_rte_monitor():
    """Check official UP RTE portal (and official parent ministry portal fallback) with strict SSL."""
    now_iso = dt.datetime.now(get_ist()).isoformat(timespec="seconds")
    status = {
        "id": "up-rte-2027-28",
        "name": "UP RTE 25% Private School Admission 2027-28",
        "url": UP_RTE_URL,
        "fallbackUrl": UP_RTE_FALLBACK_URL,
        "checkedAt": now_iso,
        "httpStatus": 0,
        "session2027Detected": False,
        "status": "CHECK_ERROR",
        "summary": "Monitor check pending.",
        "summaryHi": "आधिकारिक पोर्टल की जाँच जारी है।",
    }
    errors = []
    for target_u, is_fallback in ((UP_RTE_URL, False), (UP_RTE_URL, False), (UP_RTE_FALLBACK_URL, True)):
        try:
            st, body = _fetch_strict_ipv4(target_u, timeout=25)
            status["httpStatus"] = st
            detected = bool(re.search(r"2027\s*[-–]\s*(?:20)?28", body))
            status["session2027Detected"] = detected
            if is_fallback:
                status["fallbackUsed"] = True
            if detected:
                status["status"] = "POSSIBLE_2027_28_UPDATE"
                status["summary"] = f"2027-28 session text detected on {target_u} (HTTP {st}); review notification details."
                status["summaryHi"] = "आधिकारिक पोर्टल पर 2027–28 सत्र का उल्लेख मिला है; समय-सारणी की समीक्षा करें।"
            else:
                status["status"] = "NOTIFICATION_AWAITED"
                note = "via official parent portal basiceducation.up.gov.in" if is_fallback else "direct portal online"
                status["summary"] = f"Official UP RTE check OK (HTTP {st}, {note}). Session 2027-28 notification still awaited."
                status["summaryHi"] = "आधिकारिक यूपी आरटीई / बेसिक शिक्षा पोर्टल सक्रिय है। सत्र 2027–28 की समय-सारणी अभी प्रतीक्षित है; हर 2 घंटे में स्वचालित जाँच जारी है।"
            return status
        except Exception as ex:
            errors.append(f"{target_u}: {ex}")
    status["summary"] = "Monitor fetch error: " + " | ".join(errors[-2:])
    return status


def discover_official_icmr():
    """Parse structured open recruitment advertisements directly from https://www.icmr.gov.in/employment-opportunities."""
    url = "https://www.icmr.gov.in/employment-opportunities"
    items = []
    try:
        _, html_txt = _fetch_strict_ipv4(url, timeout=20)
    except Exception:
        return items

    for m in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", html_txt, re.S | re.I):
        row_html = m.group(1)
        cols = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
            for c in re.findall(r"<td\b[^>]*>(.*?)</td>", row_html, re.S | re.I)
        ]
        if len(cols) < 6:
            continue
        raw_title, institute, adv_status, post_nature, last_date_raw = cols[1], cols[2], cols[3], cols[4], cols[5]
        if adv_status.lower() != "open":
            continue
        pdfs = re.findall(r'href=["\']([^"\']+\.pdf)["\']', row_html, re.I)
        if not pdfs:
            continue
        en_pdf = next((u for u in pdfs if "hindi" not in u.lower()), pdfs[0])
        hi_pdf = next((u for u in pdfs if "hindi" in u.lower()), "")
        portal_match = re.search(r"https://recruitment\.icmr\.org\.in", row_html)
        apply_url = portal_match.group(0) + "/" if portal_match else url
        nid_m = re.search(r"Advertisement\s+No\.?\s*:?\s*([^\s(]+)|Advt\.?\s*No\.?\s*:?\s*([^\s)]+)", raw_title, re.I)
        notice_id = (nid_m.group(1) or nid_m.group(2)).rstrip(".,:;") if nid_m else re.sub(r"\W+", "-", raw_title[:24]).strip("-")
        clean_t = re.sub(r"\(The online application portal.*?$", "", raw_title).strip()
        clean_t = re.sub(r"Last Date:.*$", "", clean_t).strip()
        items.append({
            "source": "icmr.gov.in",
            "title": f"{clean_t} ({institute})",
            "department": f"ICMR ({institute})" if institute and "ICMR" not in institute else (institute or "ICMR"),
            "locationHint": f"{clean_t} {institute}",
            "noticeId": notice_id,
            "postNature": post_nature,
            "lastDateRaw": last_date_raw,
            "notificationUrl": en_pdf,
            "hindiNotificationUrl": hi_pdf,
            "applyUrl": apply_url,
            "applyLinkType": "GENERAL_RECRUITMENT_PORTAL",
            "officialUrl": url,
            "category": "latest-jobs",
        })
    return items


def check_expired_posts():
    """Identify any posts in data/posts.json whose deadline has passed."""
    now = dt.datetime.now(get_ist())
    posts = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))["posts"]
    expired = []
    for p in posts:
        dl = p.get("deadline")
        if dl:
            try:
                parsed = dt.datetime.fromisoformat(dl)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=get_ist())
                if parsed <= now:
                    expired.append({"id": p["id"], "title": p["title"], "deadline": dl})
            except ValueError:
                pass
    return expired


def discover(limit):
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(BASE + "robots.txt")
    rp.parse(fetch(BASE + "robots.txt").splitlines())
    found = {}
    errors = []
    for cat, path in PAGES.items():
        url = BASE + path
        if not rp.can_fetch(UA, url):
            errors.append({"url": url, "error": "robots disallowed"})
            continue
        try:
            a = Anchors()
            a.feed(fetch(url))
            for href, in_list in a.links:
                if not in_list:
                    continue
                link = article_url(href, url)
                if link:
                    row = found.setdefault(
                        link,
                        {
                            "sourceUrl": link,
                            "sourceSlug": link.rstrip("/").split("/")[-1],
                            "categories": [],
                            "officialLinkCandidates": [],
                            "status": "pending_review",
                        },
                    )
                    if cat not in row["categories"]:
                        row["categories"].append(cat)
        except Exception as e:
            errors.append({"url": url, "error": str(e)})
        time.sleep(0.8)

    for row in list(found.values())[:limit]:
        url = row["sourceUrl"]
        if not rp.can_fetch(UA, url):
            continue
        try:
            a = Anchors()
            a.feed(fetch(url))
            row["officialLinkCandidates"] = sorted(
                {urllib.parse.urljoin(url, h) for h, _ in a.links if official(urllib.parse.urljoin(url, h))}
            )[:30]
        except Exception as e:
            row["inspectionError"] = str(e)
        time.sleep(0.8)

    existing = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))["posts"]
    imported = {p.get("discoveryUrl") for p in existing if p.get("discoveryUrl")}
    rte_status = check_up_rte_monitor()
    expired = check_expired_posts()
    official_discoveries = discover_official_icmr()
    return {
        "checkedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": BASE,
        "candidates": [r for u, r in found.items() if u not in imported],
        "officialDiscoveries": official_discoveries,
        "errors": errors,
        "sourcePages": PAGES,
        "publishedCount": len(existing),
        "expiredActivePosts": expired,
        "upRteMonitor": rte_status,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="import-output/discovery.json")
    ap.add_argument("--inspect", type=int, default=20)
    ap.add_argument("--write-monitor", action="store_true")
    args = ap.parse_args()
    result = discover(max(0, min(40, args.inspect)))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write_monitor:
        mon_path = ROOT / "data/monitor_status.json"
        mon_path.write_text(
            json.dumps(
                {"lastCheckedAt": result["upRteMonitor"]["checkedAt"], "monitors": [result["upRteMonitor"]]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        "Discovered", len(result["candidates"]), "candidate URLs;",
        len(result["errors"]), "source errors;",
        len(result["expiredActivePosts"]), "expired posts;",
        "UP RTE:", result["upRteMonitor"]["status"],
    )
    if not result["candidates"]:
        raise SystemExit("No candidates: check source access or parser; do not assume no updates.")
