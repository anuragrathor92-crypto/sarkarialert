"""Official-source verification, structured extraction & authorized auto-approval gate."""
import argparse
import datetime as dt
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from build_site import JOB_CATS, ROOT
from discover import get_ist, official
from seo_keywords import resolve_verified_location

DEFAULT_DISCOVERY = ROOT / "import-output/discovery.json"
DEFAULT_REVIEW_QUEUE = ROOT / "import-output/review-queue.json"
DEFAULT_APPROVED = ROOT / "data/import_approved.json"

DATE_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def norm(txt):
    return re.sub(r"[\W_]+", "", str(txt or "").casefold())


def parse_date_str(raw):
    s = re.sub(r"\s+", " ", str(raw or "")).strip()
    m = re.search(r"([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(20\d{2})", s)
    if m and m.group(1).lower() in DATE_MONTHS:
        return f"{int(m.group(3)):04d}-{DATE_MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](20\d{2})", s)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    return ""


def probe_official(url):
    if not url or not official(url):
        return {"ok": False, "status": 0, "isPdf": False, "finalUrl": url, "reason": "unapproved_domain"}
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; SarkariAlertVerifier/1.3)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            ctype = resp.headers.get("Content-Type", "").lower()
            head = resp.read(2048)
            is_pdf = head.lstrip().startswith(b"%PDF")
            if url.lower().endswith(".pdf") and not is_pdf and "html" in ctype:
                return {"ok": False, "status": 422, "isPdf": False, "finalUrl": resp.geturl(), "reason": "pdf_html_fallback"}
            return {"ok": 200 <= resp.status < 400, "status": resp.status, "isPdf": is_pdf, "finalUrl": resp.geturl(), "reason": ""}
    except urllib.error.HTTPError as ex:
        return {"ok": False, "status": ex.code, "isPdf": False, "finalUrl": ex.geturl(), "reason": f"http_{ex.code}"}
    except Exception as ex:
        return {"ok": False, "status": 0, "isPdf": False, "finalUrl": url, "reason": str(ex)[:100]}


def slugify(text, max_len=64):
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:max_len].strip("-")


def build_existing_index():
    posts = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))["posts"]
    schemes = json.loads((ROOT / "data/schemes_directory.json").read_text(encoding="utf-8"))["records"]
    approved = json.loads(DEFAULT_APPROVED.read_text(encoding="utf-8")).get("posts", []) if DEFAULT_APPROVED.exists() else []
    combined = posts + schemes + approved
    return {
        "ids": {p["id"] for p in combined},
        "titles": {norm(p["title"]) for p in combined if p.get("title")},
        "notices": {(p.get("department", "").casefold(), p.get("noticeId")) for p in combined if p.get("noticeId")},
        "sources": {p.get("discoveryUrl") for p in combined if p.get("discoveryUrl")},
        "notifs": {p.get("notificationUrl") for p in combined if p.get("notificationUrl")},
    }


def is_duplicate(rec, idx):
    if rec["id"] in idx["ids"]:
        return True, "duplicate_id"
    if norm(rec["title"]) in idx["titles"]:
        return True, "duplicate_title"
    if rec.get("noticeId") and (rec["department"].casefold(), rec["noticeId"]) in idx["notices"]:
        return True, "duplicate_notice"
    if rec.get("discoveryUrl") and rec["discoveryUrl"] in idx["sources"]:
        return True, "duplicate_discovery_url"
    if rec.get("notificationUrl") and rec["notificationUrl"] in idx["notifs"]:
        return True, "duplicate_notification_url"
    return False, ""


def register_seen(rec, idx):
    idx["ids"].add(rec["id"])
    idx["titles"].add(norm(rec["title"]))
    if rec.get("noticeId"):
        idx["notices"].add((rec["department"].casefold(), rec["noticeId"]))
    if rec.get("discoveryUrl"):
        idx["sources"].add(rec["discoveryUrl"])
    if rec.get("notificationUrl"):
        idx["notifs"].add(rec["notificationUrl"])


def verify_official_discovery(item, now, idx):
    """Verify structured official-source notice against strict authorized rules."""
    reasons = []
    title = re.sub(r"\s+", " ", item.get("title", "")).strip()
    dept = re.sub(r"\s+", " ", item.get("department", "")).strip()
    notice_id = re.sub(r"\s+", " ", item.get("noticeId", "")).strip()
    last_date = parse_date_str(item.get("lastDateRaw") or item.get("lastDate"))
    apply_url = item.get("applyUrl", "").strip()
    notif_url = item.get("notificationUrl", "").strip()
    official_url = item.get("officialUrl", "").strip()

    if not title or not dept or not notice_id:
        reasons.append("missing_core_metadata")
    low_t = title.lower()
    if any(k in low_t for k in ("expression of interest", "deployment of regular", "corrigendum", "cancellation")):
        reasons.append("internal_eoi_or_amendment_requires_manual_review")
    if not last_date:
        reasons.append("missing_parseable_last_date")
    else:
        dl = dt.datetime.fromisoformat(f"{last_date}T23:59:00+05:30")
        if dl <= now + dt.timedelta(days=1):
            reasons.append("expired_or_closing_within_24h")

    if item.get("postNature", "").lower() == "temporary posts" and not item.get("autoApproveTemporary"):
        reasons.append("temporary_project_post_requires_manual_review")

    clean_title = re.sub(rf"^Advertisement\s*(?:No\.?)?\s*{re.escape(notice_id)}\s*[-:–]\s*", "", title, flags=re.I).strip()
    if len(clean_title) >= 15:
        title = clean_title
    pid = item.get("id") or f"{slugify(dept, 16)}-{slugify(notice_id, 28)}-{last_date[:4]}" if last_date else ""
    if pid and not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,90}", pid):
        pid = slugify(f"{dept}-{title}-{last_date[:4]}", 72)

    pre_rec = {
        "id": pid,
        "title": title,
        "department": dept,
        "noticeId": notice_id,
        "discoveryUrl": item.get("discoveryUrl") or notif_url,
        "notificationUrl": notif_url,
    }
    pre_dup, pre_dup_reason = is_duplicate(pre_rec, idx)
    if pre_dup:
        return None, [pre_dup_reason]

    p_notif = probe_official(notif_url)
    p_apply = probe_official(apply_url)
    p_off = probe_official(official_url)
    if not p_notif["ok"]:
        reasons.append(f"notification_probe_failed:{p_notif['reason']}")
    if notif_url.lower().endswith(".pdf") and not p_notif["isPdf"]:
        reasons.append("notification_not_verified_pdf")
    if not p_apply["ok"]:
        reasons.append(f"apply_probe_failed:{p_apply['reason']}")
    if not p_off["ok"]:
        reasons.append(f"official_probe_failed:{p_off['reason']}")

    if reasons:
        return None, reasons

    apply_link_type = item.get("applyLinkType") or "GENERAL_RECRUITMENT_PORTAL"
    loc_city, loc_state = resolve_verified_location({"id": pid, "department": dept, "title": f"{title} {item.get('locationHint', '')}"})
    apply_label = item.get("applyLabel") or (
        "Direct Apply Online Form" if apply_link_type == "DIRECT_APPLICATION_FORM" else f"Official {dept} Recruitment Portal"
    )
    extra_links = []
    if item.get("hindiNotificationUrl") and probe_official(item["hindiNotificationUrl"])["ok"]:
        extra_links.append(["Official Notification (Hindi PDF)", item["hindiNotificationUrl"]])

    start_date = parse_date_str(item.get("startDateRaw")) or now.date().isoformat()
    rec = {
        "id": pid,
        "title": title,
        "category": item.get("category") or "latest-jobs",
        "department": dept,
        "qualification": item.get("qualification") or "Post-wise per Official Notification",
        "noticeId": notice_id,
        "vacancies": item.get("vacancies"),
        "noticeDate": item.get("noticeDate") or start_date,
        "startDate": start_date,
        "lastDate": last_date,
        "deadline": f"{last_date}T23:59:00+05:30",
        "locationLocality": item.get("locationLocality") or loc_city,
        "locationRegion": item.get("locationRegion") or loc_state,
        "notificationUrl": notif_url,
        "applyUrl": apply_url,
        "applyLabel": apply_label,
        "applyLinkType": apply_link_type,
        "officialUrl": official_url,
        "summary": item.get("summaryHi") or f"{dept} ने विज्ञापन संख्या {notice_id} के तहत {title} के लिए आधिकारिक भर्ती अधिसूचना जारी की है। अंतिम तिथि {last_date} है।",
        "eligibilityHi": item.get("eligibilityHi") or f"शैक्षिक योग्यता, आयु सीमा एवं चयन शर्तें {dept} के आधिकारिक विज्ञापन ({notice_id}) PDF में देखें।",
        "applyInstructions": item.get("applyInstructions") or (
            f"आधिकारिक भर्ती पोर्टल ({apply_url}) पर जाकर विज्ञापन {notice_id} के अंतर्गत ऑनलाइन पंजीकरण व आवेदन {last_date} से पहले पूरा करें।"
        ),
        "rows": item.get("rows") or [
            ["विज्ञापन संख्या (Notice ID)", notice_id],
            ["विभाग / संस्थान", f"{dept} ({loc_city}, {loc_state})"],
            ["पद / श्रेणी", item.get("postNature") or "स्थायी भर्ती (Permanent)"],
            ["अंतिम तिथि", last_date],
            ["आधिकारिक माध्यम", "ऑनलाइन पोर्टल व PDF विज्ञप्ति"],
        ],
        "extraLinks": extra_links,
        "discoveryUrl": item.get("discoveryUrl") or notif_url,
        "approved": True,
        "officialFactsChecked": True,
        "applyLinkChecked": True,
        "applicationStatus": "OPEN",
        "type": "official-notice",
        "verified": True,
        "verifiedOn": now.date().isoformat(),
        "publishedDate": now.date().isoformat(),
        "reviewedBy": "auto-verify-official-rule-engine",
        "reviewedOn": now.date().isoformat(),
    }

    dup, dup_reason = is_duplicate(rec, idx)
    if dup:
        return None, [dup_reason]
    register_seen(rec, idx)
    return rec, []


def run_auto_verify(discovery_path=DEFAULT_DISCOVERY, write_approved=False, now=None):
    now = now or dt.datetime.now(get_ist())
    if not Path(discovery_path).exists():
        return {"autoApproved": [], "pendingReview": [], "duplicatesSkipped": 0, "error": "discovery_missing"}

    disc = json.loads(Path(discovery_path).read_text(encoding="utf-8"))
    idx = build_existing_index()
    auto_approved = []
    pending_review = []
    dups = 0

    for item in disc.get("officialDiscoveries", []):
        rec, reasons = verify_official_discovery(item, now, idx)
        if rec:
            auto_approved.append(rec)
        elif any(r.startswith("duplicate") for r in reasons):
            dups += 1
        else:
            pending_review.append({
                "sourceUrl": item.get("officialUrl") or item.get("notificationUrl"),
                "title": item.get("title"),
                "status": "pending_review",
                "reasons": reasons,
            })

    # Third-party candidate slugs without structured official facts ALWAYS stay pending_review
    for cand in disc.get("candidates", []):
        u = cand.get("sourceUrl", "")
        if u in idx["sources"]:
            dups += 1
            continue
        pending_review.append({
            "sourceUrl": u,
            "sourceSlug": cand.get("sourceSlug"),
            "categories": cand.get("categories", []),
            "officialLinkCandidates": cand.get("officialLinkCandidates", []),
            "status": "pending_review",
            "reasons": ["awaiting_official_structured_notice_extraction"],
        })

    if write_approved and auto_approved:
        existing_app = json.loads(DEFAULT_APPROVED.read_text(encoding="utf-8")) if DEFAULT_APPROVED.exists() else {"posts": []}
        merged = list(existing_app.get("posts", []))
        seen = {p["id"] for p in merged}
        for r in auto_approved:
            if r["id"] not in seen:
                merged.append(r)
                seen.add(r["id"])
        DEFAULT_APPROVED.write_text(json.dumps({"posts": merged}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    queue_out = {
        "checkedAt": now.isoformat(),
        "autoApprovedCount": len(auto_approved),
        "autoApprovedIds": [r["id"] for r in auto_approved],
        "duplicatesSkipped": dups,
        "pendingReviewCount": len(pending_review),
        "pendingSample": pending_review[:30],
    }
    DEFAULT_REVIEW_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REVIEW_QUEUE.write_text(json.dumps(queue_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return queue_out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--discovery", default=str(DEFAULT_DISCOVERY))
    ap.add_argument("--write-approved", action="store_true")
    args = ap.parse_args()
    res = run_auto_verify(args.discovery, write_approved=args.write_approved)
    print(
        f"Auto-Verify: approved={res['autoApprovedCount']} {res['autoApprovedIds']} | "
        f"duplicates={res['duplicatesSkipped']} | pending_review={res['pendingReviewCount']}"
    )
