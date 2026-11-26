"""Deterministic static site builder for Sarkari Alert."""
import datetime as dt, html, json, re
from pathlib import Path
from discover import get_ist

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://anuragrathor92-crypto.github.io/sarkarialert/"

CATEGORIES = [
    ("results", "Results", "परीक्षा परिणाम", "#150d98"),
    ("admit-card", "Admit Cards", "प्रवेश पत्र", "#b44700"),
    ("latest-jobs", "Latest Jobs", "नवीनतम सरकारी नौकरियाँ", "#777600"),
    ("answer-key", "Answer Key", "उत्तर कुंजी", "#c51a18"),
    ("admission", "Admission", "प्रवेश परीक्षा व नामांकन", "#8d1736"),
    ("yojana", "Sarkari Yojana", "सरकारी योजनाएँ", "#18671e"),
    ("scholarship", "Scholarship", "छात्रवृत्ति", "#9e176d"),
    ("exam-date", "Exam Dates", "परीक्षा तिथियाँ", "#006d91"),
    ("upcoming-jobs", "Upcoming Jobs", "आगामी सरकारी भर्तियाँ", "#5b3296"),
    ("10th-iti", "10th / ITI Jobs", "10वीं व ITI भर्तियाँ", "#3f5f1e"),
    ("documents", "Documents", "प्रमाणपत्र व नागरिक सेवाएँ", "#274d7a"),
    ("syllabus", "Syllabus", "पाठ्यक्रम", "#6a3a24"),
    ("outsourcing", "Outsourcing Jobs", "संविदा / आउटसोर्सिंग भर्तियाँ", "#4a4e57"),
]
CAT_MAP = {slug: (en, hi, color) for slug, en, hi, color in CATEGORIES}
JOB_CATS = {"latest-jobs", "10th-iti", "outsourcing"}

NAV_ITEMS = [
    ("", "Home"),
    ("category/latest-jobs/", "Latest Jobs"),
    ("category/results/", "Results"),
    ("category/admit-card/", "Admit Cards"),
    ("category/answer-key/", "Answer Key"),
    ("category/admission/", "Admission"),
    ("category/yojana/", "Sarkari Yojana"),
    ("category/scholarship/", "Scholarship"),
    ("category/exam-date/", "Exam Dates"),
    ("category/upcoming-jobs/", "Upcoming Jobs"),
    ("loans-and-cards/", "Loans & Cards"),
]


def e(val):
    return html.escape(str(val or ""), quote=True)


def is_expired(post, now):
    dl = post.get("deadline")
    if not dl:
        return False
    try:
        parsed = dt.datetime.fromisoformat(dl)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=get_ist())
        return parsed <= now
    except ValueError:
        return False


def ext_link(url, label, cls=""):
    cls_attr = f' class="{cls}"' if cls else ""
    return f'<a{cls_attr} href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(label)}</a>'


def render_shell(prefix, title, desc, canonical_path, main_html, json_ld=None, root_relative=False):
    def nav_href(rel):
        return f"/sarkarialert/{rel}" if root_relative else f"{prefix}{rel}"

    asset_prefix = "/sarkarialert/" if root_relative else prefix
    nav_html = "".join(f'<a href="{nav_href(rel)}">{e(label)}</a>' for rel, label in NAV_ITEMS)
    canonical = BASE + canonical_path.lstrip("/")
    ld_tag = (
        f'<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>'
        if json_ld
        else ""
    )
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{e(title)}</title>"
        f'<meta name="description" content="{e(desc[:160])}">'
        f'<link rel="canonical" href="{e(canonical)}">'
        '<meta name="theme-color" content="#a6193b">'
        f'<meta property="og:title" content="{e(title)}">'
        f'<meta property="og:description" content="{e(desc[:160])}">'
        f'<meta property="og:url" content="{e(canonical)}">'
        '<meta property="og:type" content="website">'
        '<meta property="og:site_name" content="Sarkari Alert">'
        '<meta name="twitter:card" content="summary">'
        f'<link rel="stylesheet" href="{asset_prefix}assets/style.css">'
        f'<script defer src="{asset_prefix}assets/site.js"></script>'
        f"{ld_tag}"
        "</head><body><div class=\"wrap\">"
        f'<header class="brand"><a href="{nav_href("")}"><span class="logo" aria-hidden="true">SA</span>'
        '<span>SARKARI ALERT<small>Verified Government Jobs, Results, Admit Cards &amp; Sarkari Yojana</small></span></a></header>'
        f'<nav aria-label="Main navigation">{nav_html}</nav>'
        f"<main>{main_html}</main>"
        "<footer><b>Sarkari Alert</b> — Independent government information portal."
        f'<div><a href="{nav_href("about/")}">About Us</a> · <a href="{nav_href("privacy/")}">Privacy Policy</a> · '
        f'<a href="{nav_href("disclaimer/")}">Disclaimer</a> · <a href="{nav_href("loans-and-cards/")}">Loans &amp; Cards Referral</a></div>'
        "<p>Not affiliated with any government body. Always verify the original official notification before applying.</p>"
        "</footer></div></body></html>\n"
    )


def render_item(post, prefix, is_scheme=False, now_date=None):
    pid = post["id"]
    title = post.get("titleHi") if is_scheme and post.get("titleHi") else post["title"]
    dept = post.get("department", "")
    qual = post.get("qualification", "")
    deadline = post.get("deadline", "")
    date_label = post.get("lastDate") or (deadline[:10] if deadline else "")
    pub = post.get("publishedDate") or post.get("verifiedOn") or ""
    is_new = bool(now_date and pub and (now_date - dt.date.fromisoformat(pub)).days <= 3)
    new_badge = '<span class="new-tag">New</span>' if is_new else ""

    if is_scheme:
        scope_tag = "राज्य" if post.get("scope") == "State" else "केंद्र"
        return (
            f'<li data-post data-deadline="" data-department="{e(dept)}" data-qualification="">'
            f'<a href="{prefix}posts/{e(pid)}/">{e(title)}</a> '
            f'<small class="date-tag">{e(scope_tag)}</small>'
            "</li>"
        )

    date_html = f' <span class="date-tag">Last Date: {e(date_label)}</span>' if date_label else ""
    actions = ""
    if post.get("category") in JOB_CATS and post.get("applyUrl"):
        is_pending = post.get("applyStatus") == "VERIFICATION_PENDING"
        apply_label = post.get("applyLabel") or (
            "Portal (Verification Pending)" if is_pending else "Apply Online"
        )
        apply_cls = "pending-btn" if is_pending else "apply-btn"
        actions = (
            '<div class="job-actions">'
            + ext_link(post["applyUrl"], apply_label, apply_cls)
            + " "
            + ext_link(post.get("notificationUrl") or post["officialUrl"], "Notification", "notice-btn")
            + "</div>"
        )
    return (
        f'<li data-post data-deadline="{e(deadline)}" data-department="{e(dept)}" data-qualification="{e(qual)}">'
        f'<a href="{prefix}posts/{e(pid)}/">{e(title)}</a>{new_badge}{date_html}{actions}'
        "</li>"
    )


def render_scheme_post(scheme):
    title_hi = scheme.get("titleHi") or scheme["title"]
    title_en = scheme["title"]
    dept = scheme.get("department", "")
    scope = "उत्तर प्रदेश सरकार" if scheme.get("scope") == "State" else "केंद्र सरकार"
    verified_on = scheme.get("verifiedOn", "2026-11-26")
    docs = scheme.get("requiredDocuments") or []
    docs_html = "".join(f"<li>{e(d)}</li>" for d in docs)

    # STRICT PRIORITY 2 RULE: NO separate Apply buttons for government schemes!
    links = [("Official Website", scheme["officialUrl"])]
    if scheme.get("sourceUrl") and scheme["sourceUrl"] != scheme["officialUrl"]:
        links.append(("Official Guidelines / Source", scheme["sourceUrl"]))
    links_rows = "".join(
        f'<tr><th scope="row">{e(k)}</th><td>{ext_link(v, v)}</td></tr>' for k, v in links
    )

    body = (
        '<article class="article detail">'
        '<a href="../../">Home</a> › <a href="../../category/yojana/">Sarkari Yojana</a>'
        f'<h1 lang="hi">{e(title_hi)}</h1>'
        f"<p><strong>{e(title_en)}</strong> · {e(dept)} · {e(scope)} · सत्यापन तिथि: {e(verified_on)}</p>"
        '<div class="notice" lang="hi"><strong>सरकारी योजना जानकारी मार्गदर्शिका</strong> — '
        "इस पृष्ठ पर केवल पात्रता, लाभ, आवश्यक दस्तावेज और आधिकारिक सरकारी वेबसाइट का विवरण दिया गया है।</div>"
        '<div class="detail-box">'
        '<h2 class="detail-bar">योजना का लाभ (Benefits)</h2>'
        f'<p class="inset" lang="hi">{e(scheme.get("benefit", ""))}</p>'
        '<h2 class="detail-bar">पात्रता (Eligibility)</h2>'
        f'<p class="inset" lang="hi">{e(scheme.get("eligibility", ""))}</p>'
        '<h2 class="detail-bar">आवश्यक दस्तावेज (Required Documents)</h2>'
        f'<ul lang="hi">{docs_html}</ul>'
        '<h2 class="detail-bar">महत्वपूर्ण नोट (Official Guidance)</h2>'
        f'<p class="inset" lang="hi">{e(scheme.get("notes", ""))}</p>'
        '<h2 class="detail-bar">आधिकारिक सरकारी वेबसाइट (Official Website)</h2>'
        f'<table class="important-links"><tbody>{links_rows}</tbody></table>'
        "</div>"
        '<p class="warning" lang="hi">Sarkari Alert सरकारी विभाग नहीं है। आधार, OTP, बैंक विवरण या व्यक्तिगत दस्तावेज इस वेबसाइट पर न दें; केवल ऊपर दी गई आधिकारिक सरकारी वेबसाइट का उपयोग करें।</p>'
        "</article>"
    )
    desc = f"{title_en} ({title_hi}) — पात्रता, लाभ, आवश्यक दस्तावेज और आधिकारिक वेबसाइट।"
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{title_hi} | {title_en}",
        "description": desc,
        "dateModified": verified_on,
        "publisher": {"@type": "Organization", "name": "Sarkari Alert"},
    }
    return render_shell("../../", f"{title_hi} | Sarkari Alert", desc, f"posts/{scheme['id']}/", body, ld)


def render_standard_post(post):
    cat = post["category"]
    cat_en = CAT_MAP[cat][0]
    title = post["title"]
    dept = post.get("department", "")
    verified_on = post.get("verifiedOn", "2026-11-26")
    deadline = post.get("deadline", "")

    action_box = ""
    if cat in JOB_CATS and post.get("applyUrl"):
        is_pending = post.get("applyStatus") == "VERIFICATION_PENDING"
        apply_label = post.get("applyLabel") or (
            "Official Portal (Verification Pending)" if is_pending else "Apply Online – Official Portal"
        )
        apply_cls = "pending-btn" if is_pending else "apply-btn"
        box_cls = "apply-box pending-box" if is_pending else "apply-box"
        instr = f'<p>{e(post.get("applyInstructions"))}</p>' if post.get("applyInstructions") else ""
        otr = (
            " " + ext_link(post["otrUrl"], "OTR Registration / Login", "notice-btn")
            if post.get("otrUrl")
            else ""
        )
        action_box = (
            f'<div class="{box_cls}" data-apply-box data-deadline="{e(deadline)}">'
            + ext_link(post["applyUrl"], apply_label, apply_cls)
            + " "
            + ext_link(post.get("notificationUrl") or post["officialUrl"], "Official Notification", "notice-btn")
            + otr
            + instr
            + "</div>"
        )
    elif post.get("actionUrl"):
        action_box = (
            '<div class="apply-box">'
            + ext_link(post["actionUrl"], post.get("actionLabel") or "Open Official Link", "apply-btn")
            + " "
            + ext_link(post["officialUrl"], "Official Website", "notice-btn")
            + "</div>"
        )

    ssl_warn = ""
    if post.get("linkHealth"):
        ssl_warn = (
            '<p class="warning" lang="hi"><strong>सुरक्षा चेतावनी:</strong> '
            f'{e(post["linkHealth"])} ब्राउज़र में SSL/Certificate त्रुटि आने पर आगे न बढ़ें।</p>'
        )

    rows = post.get("rows") or []
    rows_html = "".join(
        f'<tr><th scope="row" style="background:#f7f8fa;color:#161616;text-align:left;width:36%">{e(k)}</th><td>{e(v)}</td></tr>'
        for k, v in rows
    )

    # Rich 4-box Sarkari summary grid when structured detail fields or vacancies/dates are available
    dates_list = post.get("detailDates") or []
    fees_list = post.get("detailFees") or []
    age_list = post.get("detailAge") or []
    if not dates_list:
        if post.get("startDate"):
            dates_list.append(f"Application Start: {post['startDate']}")
        if post.get("lastDate"):
            dates_list.append(f"Last Date: {post['lastDate']}")
        elif post.get("noticeDate"):
            dates_list.append(f"Notice Date: {post['noticeDate']}")
    if not fees_list:
        for k, v in rows:
            if "fee" in str(k).lower():
                fees_list.append(f"{k}: {v}")
    if not age_list:
        for k, v in rows:
            if "age" in str(k).lower():
                age_list.append(f"{k}: {v}")

    vac_val = post.get("vacancies")
    grid_html = ""
    if (cat in JOB_CATS or cat == "admission") and (dates_list or fees_list or age_list or vac_val):
        d_li = "".join(f"<li>{e(x)}</li>" for x in dates_list) or "<li>See official notification</li>"
        f_li = "".join(f"<li>{e(x)}</li>" for x in fees_list) or "<li>Refer official notice PDF</li>"
        a_li = "".join(f"<li>{e(x)}</li>" for x in age_list) or "<li>Refer official notice PDF</li>"
        v_str = f"{vac_val:,} Posts" if isinstance(vac_val, int) else (str(vac_val) if vac_val else "As per notice")
        v_sub = post.get("qualification") or dept
        grid_html = (
            '<div class="detail-columns">'
            f"<section><h3>Important Dates</h3><ul>{d_li}</ul></section>"
            f"<section><h3>Application Fee</h3><ul>{f_li}</ul></section>"
            f"<section><h3>Age Limit</h3><ul>{a_li}</ul></section>"
            f'<section class="vacancy"><h3>Total Vacancies</h3><strong>{e(v_str)}</strong><p>{e(v_sub)}</p></section>'
            "</div>"
        )

    how_html = ""
    if post.get("howToApply"):
        steps_li = "".join(f"<li>{e(st)}</li>" for st in post["howToApply"])
        how_html = f'<h2 class="detail-bar">How to Apply</h2><ol>{steps_li}</ol>'
    elif cat in JOB_CATS:
        how_html = (
            '<h2 class="detail-bar">How to Apply</h2>'
            "<ol><li>Read the full official notification PDF before starting registration.</li>"
            "<li>Click the official Apply Online portal link above and complete OTR/registration.</li>"
            "<li>Fill accurate details, upload required photo/signature/documents, and pay applicable fee before deadline.</li>"
            "<li>Download and save the final submitted application confirmation page.</li></ol>"
        )

    faq_html = ""
    if post.get("faqs"):
        faq_items = "".join(
            f"<details><summary>{e(q)}</summary><p>{e(ans)}</p></details>" for q, ans in post["faqs"]
        )
        faq_html = f"<h2>Frequently Asked Questions</h2>{faq_items}"

    links = []
    if cat in JOB_CATS and post.get("applyUrl"):
        tbl_label = post.get("applyLabel") or (
            "Official Portal (Verification Pending)"
            if post.get("applyStatus") == "VERIFICATION_PENDING"
            else "Apply Online – Official Portal"
        )
        links.append((tbl_label, post["applyUrl"]))
    if post.get("actionUrl"):
        links.append((post.get("actionLabel") or "Direct Official Link", post["actionUrl"]))
    if post.get("otrUrl"):
        links.append(("OTR Registration / Login", post["otrUrl"]))
    if post.get("notificationUrl"):
        links.append(("Official Notification / Notice", post["notificationUrl"]))
    if post.get("officialUrl"):
        links.append(("Official Website", post["officialUrl"]))
    for label, url in post.get("extraLinks") or []:
        links.append((label, url))

    links_html = "".join(
        f'<tr><th scope="row">{e(k)}</th><td>{ext_link(v, "Click Here")}</td></tr>' for k, v in links
    )

    summary = post.get("summary") or f"{title} — Official verified update from {dept}."
    body = (
        '<article class="article detail">'
        f'<a href="../../">Home</a> › <a href="../../category/{e(cat)}/">{e(cat_en)}</a>'
        f"<h1>{e(title)}</h1>"
        f"{action_box}"
        f"{ssl_warn}"
        f'<p>Published &amp; Verified: {e(verified_on)} · Department: <strong>{e(dept)}</strong></p>'
        f'<p lang="hi">{e(summary)}</p>'
        '<div class="detail-box">'
        f'<div class="detail-heading"><h2>{e(title)}</h2><p>{e(dept)} · Verified Official Update</p><strong>SARKARI ALERT</strong></div>'
        f"{grid_html}"
        '<h2 class="detail-bar">Important Dates, Eligibility, Fees &amp; Details</h2>'
        f"<table><tbody>{rows_html}</tbody></table>"
        f"{how_html}"
        '<h2 class="detail-bar">Important Official Links</h2>'
        f'<table class="important-links"><tbody>{links_html}</tbody></table>'
        "</div>"
        f"{faq_html}"
        '<p class="warning">Confirm current dates, eligibility, and fees against the original official notification. Sarkari Alert never collects application fees or personal documents.</p>'
        "</article>"
    )
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": summary,
        "datePublished": post.get("publishedDate", verified_on),
        "dateModified": verified_on,
        "publisher": {"@type": "Organization", "name": "Sarkari Alert"},
    }
    return render_shell("../../", f"{title} | Sarkari Alert", summary, f"posts/{post['id']}/", body, ld)


def render_referrals_page(referrals):
    cats_html = []
    for cat in referrals.get("categories", []):
        cards = []
        for item in cat.get("items", []):
            target = item.get("referralUrl") or item.get("officialInfoUrl") or "#"
            cta = ext_link(target, item.get("ctaLabel") or "View Details", "referral-cta")
            cards.append(
                '<div class="referral-card">'
                f'<h3>{e(item["name"])}</h3>'
                f'<p><strong>Provider:</strong> {e(item["provider"])} · <strong>Type:</strong> {e(item["type"])}</p>'
                f'<p>{e(item["highlights"])}</p>'
                f'<p><strong>Eligibility:</strong> {e(item["eligibility"])}</p>'
                f"{cta}"
                "</div>"
            )
        cats_html.append(
            f'<h2>{e(cat["title"])} <small lang="hi">({e(cat.get("titleHi", ""))})</small></h2>'
            f'<div class="referral-grid">{"".join(cards)}</div>'
        )

    body = (
        '<article class="article">'
        '<a href="../">← Home</a>'
        f'<h1>{e(referrals["sectionTitle"])}</h1>'
        f'<p class="hindi" lang="hi">{e(referrals["sectionTitleHi"])}</p>'
        f'<div class="warning"><strong>Disclosure:</strong> {e(referrals["disclosure"])}'
        f'<br><span lang="hi">{e(referrals["disclosureHi"])}</span></div>'
        f'{"".join(cats_html)}'
        '<div class="notice"><strong>Admin Configuration:</strong> Commercial referral links can be updated in <code>data/referrals.json</code> without modifying government job or Sarkari Yojana sections.</div>'
        "</article>"
    )
    return render_shell(
        "../",
        "Loans & Credit Cards Referral Desk | Sarkari Alert",
        "Separate partner referral directory for education loans, personal/MSME loans, and credit cards.",
        "loans-and-cards/",
        body,
    )


def build_all(now=None, prune_expired=False, posts_override=None):
    now = now or dt.datetime.now(get_ist())
    now_date = now.date()

    posts_path = ROOT / "data/posts.json"
    schemes_path = ROOT / "data/schemes_directory.json"
    referrals_path = ROOT / "data/referrals.json"
    monitor_path = ROOT / "data/monitor_status.json"

    posts_data = posts_override if posts_override is not None else json.loads(posts_path.read_text(encoding="utf-8"))
    raw_posts = list(posts_data["posts"])
    schemes = json.loads(schemes_path.read_text(encoding="utf-8"))["records"]
    referrals = json.loads(referrals_path.read_text(encoding="utf-8"))
    monitors = json.loads(monitor_path.read_text(encoding="utf-8")).get("monitors", [])

    active_posts = []
    expired_posts = []
    for p in raw_posts:
        if is_expired(p, now):
            p["applicationStatus"] = "EXPIRED"
            expired_posts.append(p)
        else:
            active_posts.append(p)

    # Sort newest verified/published first
    active_posts.sort(
        key=lambda x: (x.get("publishedDate") or x.get("verifiedOn") or "", x.get("lastDate") or ""),
        reverse=True,
    )

    files = {}

    # 1. Render all active non-scheme posts
    for p in active_posts:
        files[f"posts/{p['id']}/index.html"] = render_standard_post(p)

    # 2. Render all 32 Sarkari Yojana pages (NO Apply buttons)
    for s in schemes:
        files[f"posts/{s['id']}/index.html"] = render_scheme_post(s)

    # 3. Group active posts by category (supporting extraCategory e.g. 10th-iti)
    by_cat = {slug: [] for slug, _, _, _ in CATEGORIES}
    for p in active_posts:
        c = p.get("category")
        if c in by_cat:
            by_cat[c].append(p)
        ec = p.get("extraCategory")
        if ec and ec in by_cat and p not in by_cat[ec]:
            by_cat[ec].append(p)

    # 4. Render all 13 category pages
    for slug, en, hi, _ in CATEGORIES:
        if slug == "yojana":
            items_html = "".join(render_item(s, "../../", is_scheme=True, now_date=now_date) for s in schemes)
            body = (
                '<article class="article">'
                '<a href="../../">← Home</a>'
                f"<h1>{e(en)} ({len(schemes)}) — {e(hi)}</h1>"
                f'<p class="notice" lang="hi"><strong>कुल {len(schemes)} सत्यापित सरकारी योजनाएँ</strong> (27 केंद्रीय + 5 उत्तर प्रदेश) · पात्रता, लाभ, आवश्यक दस्तावेज और आधिकारिक वेबसाइट विवरण। सरकारी योजनाओं के लिए अलग Apply बटन नहीं दिए गए हैं।</p>'
                f"<ul>{items_html}</ul>"
                "</article>"
            )
            desc = f"{en} — Complete directory of {len(schemes)} central and state government schemes with eligibility, benefits, documents, and official websites."
        else:
            items = by_cat[slug]
            if items:
                items_html = "".join(render_item(p, "../../", is_scheme=False, now_date=now_date) for p in items)
                list_block = f"<ul>{items_html}</ul>"
            else:
                list_block = '<p class="empty" lang="hi">अभी कोई सक्रिय सत्यापित अपडेट नहीं है।</p>'
            extra_mon = ""
            if slug == "admission" and monitors:
                m = monitors[0]
                extra_mon = (
                    '<div class="monitor-bar"><div>'
                    f'<span class="monitor-badge">Live 2-Hour Monitor</span> <strong>{e(m["name"])}</strong>: '
                    f'<span lang="hi">{e(m.get("summaryHi") or m["summary"])}</span></div>'
                    + ext_link(m["url"], "Check Official RTE Portal", "notice-btn")
                    + "</div>"
                )
            body = (
                '<article class="article">'
                '<a href="../../">← Home</a>'
                f"<h1>{e(en)} <small lang=\"hi\">({e(hi)})</small></h1>"
                f"{extra_mon}{list_block}"
                "</article>"
            )
            desc = f"{en} — Verified official {en.lower()} updates, dates, and direct official links on Sarkari Alert."
        files[f"category/{slug}/index.html"] = render_shell("../../", f"{en} | Sarkari Alert", desc, f"category/{slug}/", body)

    # 5. Render Separate Loans & Credit Cards Referral Page
    files["loans-and-cards/index.html"] = render_referrals_page(referrals)

    # 6. Render Static Info Pages & 404
    static_pages = [
        ("about", "About Us", "Sarkari Alert is an independent information portal for verified government recruitment, examination, admission, result, and welfare scheme updates. It is not affiliated with any government agency."),
        ("privacy", "Privacy Policy", "Sarkari Alert does not require user accounts or collect Aadhaar, bank details, or application documents. External official government portals and partner links have their own privacy policies."),
        ("disclaimer", "Disclaimer", "Always verify eligibility, deadlines, fees, and official instructions directly on the original issuing government website or notification PDF before applying. Sarkari Alert never accepts application fees."),
    ]
    for slug, heading, text in static_pages:
        body = f'<article class="article"><a href="../">← Home</a><h1>{e(heading)}</h1><p>{e(text)}</p></article>'
        files[f"{slug}/index.html"] = render_shell("../", f"{heading} | Sarkari Alert", text, f"{slug}/", body)

    files["404.html"] = render_shell(
        "/sarkarialert/",
        "Page not found | Sarkari Alert",
        "Requested page was not found on Sarkari Alert.",
        "404.html",
        '<h1>Page not found</h1><p><a href="/sarkarialert/">Return to Sarkari Alert Home</a></p>',
        root_relative=True,
    )

    # 7. Render Homepage (index.html)
    depts = sorted({p.get("department") for p in active_posts + schemes if p.get("department")})
    quals = sorted({p.get("qualification") for p in active_posts if p.get("qualification")})
    dept_opts = '<option value="">All departments</option>' + "".join(f"<option>{e(d)}</option>" for d in depts)
    qual_opts = '<option value="">All qualifications</option>' + "".join(f"<option>{e(q)}</option>" for q in quals)

    # Top 8 highlight boxes (inspired by sarkariresult.com.cm)
    hl_colors = ["#9c1637", "#14539a", "#146c2e", "#b04300", "#6a1b9a", "#006978", "#8b2635", "#3b4252"]
    hl_candidates = (
        by_cat["latest-jobs"][:3]
        + by_cat["admission"][:2]
        + by_cat["answer-key"][:1]
        + by_cat["admit-card"][:1]
        + by_cat["results"][:1]
    )[:8]
    hl_html = "".join(
        f'<a class="highlight-card" style="--hl:{hl_colors[i % len(hl_colors)]}" href="./posts/{e(p["id"])}/">'
        f'{e(p["title"][:62])}<small>{e(CAT_MAP[p["category"]][0])}</small></a>'
        for i, p in enumerate(hl_candidates)
    )

    ticker_links = " · ".join(
        f'<a href="./posts/{e(p["id"])}/">{e(p["title"][:55])}</a>'
        for p in (by_cat["latest-jobs"][:2] + by_cat["results"][:1] + by_cat["answer-key"][:1])
    )

    tiles_html = "".join(
        f'<a style="--tile:{color}" href="./category/{slug}/">{e(en)}'
        f'{f" ({len(schemes)})" if slug == "yojana" else ""}</a>'
        for slug, en, _, color in CATEGORIES[:11]
    ) + '<a style="--tile:#0f4c81" href="./loans-and-cards/">Loans &amp; Cards</a>'

    panel_order = [
        "results", "admit-card", "latest-jobs",
        "answer-key", "admission", "yojana",
        "scholarship", "exam-date", "upcoming-jobs",
        "10th-iti", "documents", "syllabus", "outsourcing",
    ]
    panels_html = []
    for slug in panel_order:
        en, _, _ = CAT_MAP[slug]
        if slug == "yojana":
            ul = "".join(render_item(s, "./", is_scheme=True, now_date=now_date) for s in schemes)
            panels_html.append(
                f'<section class="panel" data-category="yojana">'
                f'<h2><a href="./category/yojana/">Sarkari Yojana ({len(schemes)})</a></h2>'
                f'<p class="inset" lang="hi"><strong>कुल {len(schemes)} योजनाएँ</strong> · पात्रता, लाभ व दस्तावेज (बिना अलग Apply बटन)।</p>'
                f"<ul>{ul}</ul>"
                f'<a class="more" href="./category/yojana/">View All {len(schemes)} Schemes »</a></section>'
            )
        else:
            items = by_cat[slug]
            heading_count = f" ({len(items)})" if items else ""
            content = (
                f'<ul>{"".join(render_item(p, "./", is_scheme=False, now_date=now_date) for p in items)}</ul>'
                if items
                else '<p class="empty" lang="hi">अभी कोई सक्रिय अपडेट नहीं है।</p>'
            )
            panels_html.append(
                f'<section class="panel" data-category="{slug}">'
                f'<h2><a href="./category/{slug}/">{e(en)}{heading_count}</a></h2>'
                f"{content}"
                f'<a class="more" href="./category/{slug}/">View More »</a></section>'
            )

    rte_mon = monitors[0] if monitors else {}
    rte_html = (
        '<div class="monitor-bar"><div>'
        '<span class="monitor-badge">2-Hour Auto Monitor</span> '
        f'<strong>{e(rte_mon.get("name", "UP RTE 2027-28"))}:</strong> '
        f'<span lang="hi">{e(rte_mon.get("summaryHi", "सत्र 2027–28 नोटिफिकेशन प्रतीक्षित"))}</span></div>'
        '<a class="notice-btn" href="./posts/up-rte-admission-2027-28-monitor/">Monitor Details</a></div>'
    )

    home_main = (
        "<h1>Sarkari Alert — Latest Government Jobs, Results, Admit Cards &amp; Sarkari Yojana</h1>"
        '<p class="hindi" lang="hi">सत्यापित सरकारी नौकरी, परीक्षा परिणाम, प्रवेश पत्र, उत्तर कुंजी और सरकारी योजनाओं की सटीक जानकारी</p>'
        f'<p class="launch">{len(active_posts)} verified active notices &amp; service guides + {len(schemes)} Sarkari Yojana entries · Updated {now_date.isoformat()}</p>'
        f'<div class="ticker"><strong>LIVE UPDATES:</strong> {ticker_links}</div>'
        f'<div class="highlight-grid">{hl_html}</div>'
        f"{rte_html}"
        '<div class="quick-links">'
        '<a href="./category/latest-jobs/">Latest Jobs</a>'
        '<a href="./category/results/">Exam Results</a>'
        '<a href="./category/admit-card/">Admit Cards</a>'
        '<a href="./category/answer-key/">Answer Key</a>'
        '<a href="./category/yojana/">Sarkari Yojana (32)</a>'
        '<a href="./category/upcoming-jobs/">Upcoming Jobs</a>'
        '<a href="./loans-and-cards/">Loans &amp; Cards Referral</a>'
        "</div>"
        '<form id="search" class="search">'
        '<input id="query" type="search" aria-label="Search posts" placeholder="Search jobs, results, schemes, exams…">'
        f'<select id="department" aria-label="Department">{dept_opts}</select>'
        f'<select id="qualification" aria-label="Qualification">{qual_opts}</select>'
        '<button type="submit">Search</button><button type="reset" class="reset">Reset</button>'
        "</form>"
        '<p id="search-status" role="status" hidden></p>'
        f'<div class="tiles">{tiles_html}</div>'
        f'<div class="panels">{"".join(panels_html)}</div>'
        '<div class="referral-banner">'
        '<div><strong>Separate Partner Referral Desk — Loans &amp; Credit Cards</strong>'
        '<p style="margin:4px 0 0;font-size:14px">Non-government commercial banking offers, education loans &amp; credit cards separated from government listings.</p></div>'
        '<a class="referral-cta" href="./loans-and-cards/">Explore Loans &amp; Credit Cards »</a></div>'
        '<section class="about"><h2>About Sarkari Alert</h2>'
        "<p>Sarkari Alert publishes verified official government recruitment notices, results, admit cards, answer keys, admissions, scholarships, exam calendars, and 32 government welfare schemes. Automated checks run every 2 hours to monitor updates and exclude expired forms.</p></section>"
    )

    home_ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Sarkari Alert",
        "url": BASE,
        "potentialAction": {
            "@type": "SearchAction",
            "target": BASE + "?q={search_term_string}",
            "query-input": "required name=search_term_string",
        },
    }
    files["index.html"] = render_shell(
        "./",
        "Latest Government Jobs, Results, Admit Cards, Sarkari Yojana | Sarkari Alert",
        "Verified government jobs, exam results, admit cards, answer keys, admissions, scholarships, upcoming jobs, and 32 Sarkari Yojana guides.",
        "",
        home_main,
        home_ld,
    )

    # 8. Build sitemap.xml
    urls = [BASE]
    for slug, _, _, _ in CATEGORIES:
        urls.append(f"{BASE}category/{slug}/")
    for extra in ("loans-and-cards/", "about/", "privacy/", "disclaimer/"):
        urls.append(f"{BASE}{extra}")
    for p in active_posts:
        urls.append(f"{BASE}posts/{p['id']}/")
    for s in schemes:
        urls.append(f"{BASE}posts/{s['id']}/")

    lastmod = now_date.isoformat()
    url_tags = "".join(f"<url><loc>{e(u)}</loc><lastmod>{lastmod}</lastmod></url>" for u in urls)
    files["sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{url_tags}</urlset>\n'
    )

    if prune_expired and expired_posts:
        posts_data["posts"] = active_posts
        posts_data["archivedExpiredCount"] = posts_data.get("archivedExpiredCount", 0) + len(expired_posts)
        files["data/posts.json"] = json.dumps(posts_data, ensure_ascii=False, indent=2) + "\n"

    return files, active_posts, expired_posts


if __name__ == "__main__":
    files, active, expired = build_all()
    for rel, content in files.items():
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    print(f"Built {len(files)} files; active posts: {len(active)}, expired excluded: {len(expired)}")
