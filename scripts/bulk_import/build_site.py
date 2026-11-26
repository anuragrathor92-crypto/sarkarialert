"""Deterministic static site builder and SEO engine for Sarkari Alert."""
import datetime as dt
import hashlib
import html
import json
import os
import re
from pathlib import Path

from discover import get_ist
from seo_keywords import CATEGORY_SEO, infer_employment_type, infer_region, resolve_verified_location

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



def bilingual(en, hi):
    return f'{e(en)} — <span lang="hi">{e(hi)}</span>'


def category_label(slug):
    en, hi, _ = CAT_MAP[slug]
    return bilingual(en, hi)


def application_display(post):
    kind = post.get("applyLinkType") or "GENERAL_RECRUITMENT_PORTAL"
    pending = (post.get("applyStatus") == "VERIFICATION_PENDING"
               or kind == "VERIFICATION_PENDING")
    if pending:
        return "Verification Pending — लिंक सत्यापन बाकी", True
    labels = {
        "DIRECT_APPLICATION_FORM": "Application Form — आवेदन फ़ॉर्म",
        "GENERAL_RECRUITMENT_PORTAL": "Official Recruitment Portal — सरकारी भर्ती पोर्टल",
        "OFFLINE_POSTAL_FORM": "Offline Application Form — ऑफलाइन आवेदन पत्र",
    }
    return labels.get(kind, "Official Link — आधिकारिक लिंक"), False


def clean_text(val):
    return re.sub(r"\s+", " ", str(val or "")).strip()


def make_seo_title(raw_title, brand="Sarkari Alert", max_len=66):
    """Build a concise, high-CTR SEO <title> within SERP display limits."""
    t = clean_text(raw_title)
    suffix = f" | {brand}"
    if len(t) + len(suffix) <= max_len:
        return f"{t}{suffix}"
    budget = max_len - len(suffix)
    if budget < 18:
        return t[:max_len].strip()
    cut = t[:budget]
    if " " in cut and len(t) > budget:
        cut = cut.rsplit(" ", 1)[0]
    cut = cut.rstrip(" –—-:,(/&")
    return f"{cut}{suffix}"


def make_seo_desc(raw_desc, fallback_extra="", max_len=158):
    """Build a crisp, non-truncated 80-158 char meta description."""
    d = clean_text(raw_desc)
    extra = clean_text(fallback_extra)
    if not d:
        d = extra
    elif len(d) < 85 and extra:
        sep = "" if d.endswith(("।", ".", "!")) else " — "
        d = f"{d}{sep}{extra}".strip()
    if len(d) < 80:
        d = f"{d} आधिकारिक पोर्टल, योग्यता व महत्वपूर्ण तिथियाँ Sarkari Alert पर देखें।".strip()
    if len(d) <= max_len:
        return d
    cut = d[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-–—") + "…"


def normalize_valid_through(post):
    """Return ISO-8601 validThrough string with IST offset when possible."""
    dl = post.get("deadline")
    if dl:
        try:
            parsed = dt.datetime.fromisoformat(dl)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=get_ist())
            return parsed.isoformat()
        except ValueError:
            pass
    ld = post.get("lastDate")
    if ld and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(ld)):
        return f"{ld}T23:59:00+05:30"
    return ""


def is_expired(post, now):
    if post.get("applicationStatus") == "EXPIRED":
        return True
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


def is_jobposting_eligible(post, now):
    """Strict eligibility gate per Google JobPosting & Indexing API policy."""
    if post.get("category") not in JOB_CATS:
        return False
    if post.get("applicationStatus") not in ("OPEN", None):
        return False
    if post.get("verified") is False:
        return False
    if not post.get("applyUrl"):
        return False
    if is_expired(post, now):
        return False
    vt = normalize_valid_through(post)
    if not vt:
        return False
    return bool(clean_text(post.get("title")) and clean_text(post.get("department")))


def ext_link(url, label, cls=""):
    cls_attr = f' class="{cls}"' if cls else ""
    return f'<a{cls_attr} href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(label)}</a>'


def load_site_config():
    cfg_path = ROOT / "data/site_config.json"
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return {}


def render_shell(
    prefix,
    title,
    desc,
    canonical_path,
    main_html,
    json_ld=None,
    root_relative=False,
    site_cfg=None,
    robots="index,follow,max-image-preview:large",
    page_type="site",
    page_category="",
    post_id="",
):
    site_cfg = site_cfg if site_cfg is not None else load_site_config()

    def nav_href(rel):
        return f"/sarkarialert/{rel}" if root_relative else f"{prefix}{rel}"

    asset_prefix = "/sarkarialert/" if root_relative else prefix
    def nav_label(rel, label):
        if rel.startswith("category/"):
            return category_label(rel.split("/")[1])
        return bilingual(label, "मुख्य पृष्ठ" if not rel else "ऋण व कार्ड")
    nav_html = "".join(f'<a href="{nav_href(rel)}">{nav_label(rel, label)}</a>' for rel, label in NAV_ITEMS)
    canonical = BASE + canonical_path.lstrip("/")
    og_image = f"{BASE}assets/og-card.png"
    ld_tag = (
        f'<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>'
        if json_ld
        else ""
    )

    gsc_token = (site_cfg.get("googleSearchConsole") or {}).get("verificationMetaContent", "").strip()
    gsc_tag = f'<meta name="google-site-verification" content="{e(gsc_token)}">' if gsc_token else ""

    bing_token = (site_cfg.get("bingWebmaster") or {}).get("verificationMetaContent", "").strip()
    bing_tag = f'<meta name="msvalidate.01" content="{e(bing_token)}">' if bing_token else ""

    ga4_id = str((site_cfg.get("googleAnalytics4") or {}).get("measurementId", "")).strip()
    ga4_tag = ""
    if re.fullmatch(r"G-[A-Z0-9]{6,14}", ga4_id):
        ga4_tag = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(ga4_id)}"></script>'
            "<script>(function(){if(window.__saGaInit)return;window.__saGaInit=true;"
            "var denied=false;try{denied=localStorage.getItem('sa_ga_consent')==='denied';}catch(ex){}"
            f"if(denied){{window['ga-disable-{e(ga4_id)}']=true;}}"
            "window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
            "window.gtag=window.gtag||gtag;"
            "gtag('consent','default',{'analytics_storage':denied?'denied':'granted','ad_storage':'denied','ad_user_data':'denied','ad_personalization':'denied','wait_for_update':500});"
            "gtag('js',new Date());"
            f"gtag('config','{e(ga4_id)}',{{'anonymize_ip':true,'allow_google_signals':false,'allow_ad_personalization_signals':false,'page_location':location.origin+location.pathname}});"
            "})();</script>"
        )

    ads_cfg = site_cfg.get("googleAdSense") or {}
    pub_id = str(ads_cfg.get("publisherId", "")).strip()
    ads_tag = (
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(pub_id)}" crossorigin="anonymous"></script>'
        if pub_id.startswith("ca-pub-") and ads_cfg.get("enableAutoAds")
        else ""
    )

    safe_desc = desc[:160]
    body_attrs = (
        f'data-ga-id="{e(ga4_id)}" data-asset-prefix="{e(asset_prefix)}" '
        f'data-page-type="{e(page_type)}" data-category="{e(page_category)}" data-post-id="{e(post_id)}"'
    )
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="robots" content="{e(robots)}">'
        f"<title>{e(title)}</title>"
        f'<meta name="description" content="{e(safe_desc)}">'
        f'<link rel="canonical" href="{e(canonical)}">'
        f'<link rel="icon" type="image/svg+xml" href="{asset_prefix}assets/favicon.svg">'
        f'<link rel="alternate" type="application/rss+xml" title="Sarkari Alert Updates" href="{asset_prefix}feed.xml">'
        '<meta name="theme-color" content="#a6193b">'
        f"{gsc_tag}{bing_tag}"
        f'<meta property="og:title" content="{e(title)}">'
        f'<meta property="og:description" content="{e(safe_desc)}">'
        f'<meta property="og:url" content="{e(canonical)}">'
        f'<meta property="og:image" content="{e(og_image)}">'
        '<meta property="og:image:width" content="1200">'
        '<meta property="og:image:height" content="630">'
        '<meta property="og:type" content="website">'
        '<meta property="og:locale" content="en_IN">'
        '<meta property="og:site_name" content="Sarkari Alert">'
        '<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{e(title)}">'
        f'<meta name="twitter:description" content="{e(safe_desc)}">'
        f'<meta name="twitter:image" content="{e(og_image)}">'
        f'<link rel="stylesheet" href="{asset_prefix}assets/style.css">'
        f'<script defer src="{asset_prefix}assets/site.js"></script>'
        f"{ga4_tag}{ads_tag}{ld_tag}"
        f'</head><body {body_attrs}><div class="wrap">'
        f'<header class="brand"><a href="{nav_href("")}"><span class="logo" aria-hidden="true">SA</span>'
        '<span>SARKARI ALERT<small>Verified Government Jobs, Results, Admit Cards &amp; Sarkari Yojana</small></span></a></header>'
        f'<nav aria-label="Main navigation">{nav_html}</nav>'
        f"<main>{main_html}</main>"
        "<footer><b>Sarkari Alert</b> — Independent government information portal."
        f'<div><a href="{nav_href("about/")}">About Us</a> · <a href="{nav_href("privacy/")}">Privacy Policy</a> · '
        f'<a href="{nav_href("disclaimer/")}">Disclaimer</a> · <a href="{nav_href("sitemap/")}">All Updates Directory</a> · '
        f'<a href="{nav_href("loans-and-cards/")}">Loans &amp; Cards Referral</a></div>'
        '<div><button type="button" id="manage-analytics-consent" class="consent-link">Analytics &amp; Privacy Settings</button></div>'
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
    new_badge = '<span class="new-tag">New — नया</span>' if is_new else ""

    if is_scheme:
        loc_tag = post.get("stateOrUt") or ("राज्य" if post.get("scope") == "State" else "केंद्र")
        upc_tag = ' <span class="new-tag">Upcoming</span>' if post.get("upcoming") else ""
        return (
            f'<li data-post data-deadline="" data-department="{e(dept)}" data-qualification="">'
            f'<a href="{prefix}posts/{e(pid)}/">{e(title)}</a>{upc_tag} '
            f'<small class="date-tag">{e(loc_tag)}</small>'
            "</li>"
        )

    date_html = f' <span class="date-tag">Last Date / अंतिम तिथि: {e(date_label)}</span>' if date_label else ""
    actions = ""
    if post.get("category") in JOB_CATS and post.get("applyUrl"):
        apply_label, is_pending = application_display(post)
        apply_cls = "pending-btn" if is_pending else "apply-btn"
        actions = (
            '<div class="job-actions">'
            + ext_link(post["applyUrl"], apply_label, apply_cls)
            + " "
            + ext_link(post.get("notificationUrl") or post["officialUrl"], "Notification", "notice-btn")
            + "</div>"
        )
    return (
        f'<li data-post data-post-id="{e(pid)}" data-deadline="{e(deadline)}" data-department="{e(dept)}" data-qualification="{e(qual)}">'
        f'<a href="{prefix}posts/{e(pid)}/">{e(title)}</a>{new_badge}{date_html}{actions}'
        "</li>"
    )


def find_related_posts(current, active_posts, schemes=None, is_scheme=False, limit=6):
    """Select topically relevant active internal links for crawl depth & UX."""
    cur_id = current.get("id")
    cur_dept = clean_text(current.get("department")).casefold()
    cur_cat = current.get("category", "yojana" if is_scheme else "")
    cur_qual = set(re.findall(r"[a-z0-9]{2,}", str(current.get("qualification", "")).lower()))
    cur_region = infer_region(current) if not is_scheme else current.get("stateOrUt", "")

    scored = []
    if is_scheme and schemes:
        for s in schemes:
            if s["id"] == cur_id:
                continue
            score = 0
            if s.get("stateOrUt") and s.get("stateOrUt") == cur_region:
                score += 6
            if s.get("scope") == current.get("scope"):
                score += 2
            if clean_text(s.get("department")).casefold() == cur_dept:
                score += 4
            if score > 0:
                scored.append((score, s.get("verifiedOn", ""), s["id"], s.get("titleHi") or s["title"], s.get("stateOrUt") or "Yojana"))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        out = scored[:limit]
        # Append 2 relevant active scholarship/job updates for cross-category flow
        for p in active_posts:
            if len(out) >= limit:
                break
            if p.get("category") in ("scholarship", "admission", "latest-jobs"):
                out.append((1, p.get("verifiedOn", ""), p["id"], p["title"], CAT_MAP[p["category"]][0]))
        return out[:limit]

    for p in active_posts:
        if p["id"] == cur_id:
            continue
        score = 0
        if clean_text(p.get("department")).casefold() == cur_dept and cur_dept:
            score += 6
        if cur_region != "India" and infer_region(p) == cur_region:
            score += 3
        p_qual = set(re.findall(r"[a-z0-9]{2,}", str(p.get("qualification", "")).lower()))
        overlap = cur_qual & p_qual - {"pass", "or", "with", "post", "wise", "per", "as", "any", "degree"}
        score += len(overlap) * 2
        if p.get("category") == cur_cat:
            score += 2
        elif cur_cat in JOB_CATS and p.get("category") in ("syllabus", "exam-date", "admit-card", "upcoming-jobs"):
            score += 1
        if score > 0:
            scored.append((score, p.get("publishedDate") or p.get("verifiedOn") or "", p["id"], p["title"], CAT_MAP[p["category"]][0]))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if len(scored) < limit:
        seen = {x[2] for x in scored}
        for p in active_posts:
            if p["id"] != cur_id and p["id"] not in seen:
                scored.append((0, p.get("publishedDate") or "", p["id"], p["title"], CAT_MAP[p["category"]][0]))
                seen.add(p["id"])
                if len(scored) >= limit:
                    break
    return scored[:limit]


def render_related_block(related_items, heading="Related Updates & Similar Opportunities (संबंधित अपडेट)"):
    if not related_items:
        return ""
    lis = "".join(
        f'<li><a href="../../posts/{e(pid)}/">{e(t)}</a> <small class="date-tag">{e(tag)}</small></li>'
        for _, _, pid, t, tag in related_items
    )
    return (
        '<section class="related-box" aria-label="Related Updates">'
        f"<h2>{e(heading)}</h2>"
        f'<ul class="related-grid">{lis}</ul>'
        '<p style="margin:8px 0 0;font-size:13px"><a href="../../category/latest-jobs/">All Latest Jobs »</a> · '
        '<a href="../../sitemap/">Complete Updates Directory »</a></p>'
        "</section>"
    )


def render_scheme_post(scheme, related_items=None, site_cfg=None, title_override=None, desc_override=None):
    title_hi = scheme.get("titleHi") or scheme["title"]
    title_en = scheme["title"]
    dept = scheme.get("department", "")
    scope = "राज्य सरकार" if scheme.get("scope") == "State" else "केंद्र सरकार"
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

    related_html = render_related_block(related_items, "Related Government Schemes & Citizen Services (संबंधित योजनाएँ)")
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
        f"{related_html}"
        '<p class="warning" lang="hi">Sarkari Alert सरकारी विभाग नहीं है। आधार, OTP, बैंक विवरण या व्यक्तिगत दस्तावेज इस वेबसाइट पर न दें; केवल ऊपर दी गई आधिकारिक सरकारी वेबसाइट का उपयोग करें।</p>'
        "</article>"
    )
    seo_title = title_override or make_seo_title(f"{title_hi} ({scheme.get('stateOrUt', 'India')})")
    desc = desc_override or make_seo_desc(
        f"{title_en} ({title_hi}) — {dept} योजना के लाभ, पात्रता, आवश्यक दस्तावेज व आधिकारिक पोर्टल।"
    )
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "GovernmentService",
            "name": f"{title_hi} | {title_en}",
            "serviceType": "Government Welfare Scheme Information",
            "provider": {"@type": "GovernmentOrganization", "name": dept},
            "areaServed": scheme.get("stateOrUt") or "India",
            "url": f"{BASE}posts/{scheme['id']}/",
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE},
                {"@type": "ListItem", "position": 2, "name": "Sarkari Yojana", "item": f"{BASE}category/yojana/"},
                {"@type": "ListItem", "position": 3, "name": title_en, "item": f"{BASE}posts/{scheme['id']}/"},
            ],
        },
    ]
    return render_shell(
        "../../",
        seo_title,
        desc,
        f"posts/{scheme['id']}/",
        body,
        ld,
        site_cfg=site_cfg,
        page_type="scheme",
        page_category="yojana",
        post_id=scheme["id"],
    )


def build_checklist_box(post):
    cat = post["category"]
    if cat not in JOB_CATS and cat not in ("admission", "scholarship", "exam-date", "upcoming-jobs"):
        return ""
    dept = post.get("department", "")
    qual = post.get("qualification") or "विज्ञापन के अनुसार (See Notice)"
    last_date = post.get("lastDate") or "विज्ञप्ति देखें"
    is_offline = "offline" in str(post.get("applyLabel", "")).lower() or "डाक" in str(post.get("applyLabel", ""))
    mode = "ऑफलाइन / डाक आवेदन (Postal Offline)" if is_offline else "ऑनलाइन आवेदन (Official Portal)"
    link_status = "Verification Pending (स्वचालित पुनः जाँच सक्रिय)" if post.get("applyStatus") == "VERIFICATION_PENDING" else "सत्यापित आधिकारिक लिंक (Verified Official URL)"
    return (
        '<section class="checklist-box" lang="hi">'
        "<h2>प्रमुख सारांश व आवेदन जांच सूची (Verification Checklist)</h2>"
        "<ul>"
        f"<li><strong>भर्ती विभाग / बोर्ड:</strong> {e(dept)}</li>"
        f"<li><strong>शैक्षिक योग्यता:</strong> {e(qual)}</li>"
        f"<li><strong>आवेदन माध्यम:</strong> {e(mode)}</li>"
        f"<li><strong>अंतिम तिथि / समय-सीमा:</strong> {e(last_date)}</li>"
        f"<li><strong>लिंक सत्यापन स्थिति:</strong> {e(link_status)}</li>"
        "</ul></section>"
    )


def build_auto_faqs(post):
    if post.get("faqs"):
        return post["faqs"]
    cat = post["category"]
    title = post["title"]
    dept = post.get("department", "Issuing Authority")
    last_date = post.get("lastDate")
    if cat in JOB_CATS:
        vac = post.get("vacancies")
        vac_txt = f"कुल {vac:,} पद हैं।" if isinstance(vac, int) else "पदों का विस्तृत विवरण आधिकारिक नोटिफिकेशन में देखें।"
        date_txt = f"अंतिम तिथि {last_date} है।" if last_date else "आवेदन तिथियाँ आधिकारिक नोटिस में देखें।"
        return [
            (f"{title} में आवेदन करने की अंतिम तिथि क्या है?", f"{dept} की इस भर्ती के लिए {date_txt}"),
            (f"{dept} भर्ती की योग्यता और कुल पद कितने हैं?", f"{vac_txt} शैक्षिक योग्यता: {post.get('qualification') or 'आधिकारिक विज्ञापन के अनुसार'}।"),
            ("आधिकारिक आवेदन व नोटिफिकेशन PDF कहाँ से प्राप्त करें?", "ऊपर दिए गए Important Official Links अनुभाग में सीधे आधिकारिक पोर्टल और नोटिफिकेशन PDF लिंक दिए गए हैं।"),
        ]
    return []


def render_standard_post(
    post,
    now=None,
    related_items=None,
    site_cfg=None,
    title_override=None,
    desc_override=None,
):
    now = now or dt.datetime.now(get_ist())
    cat = post["category"]
    cat_en = CAT_MAP[cat][0]
    title = post["title"]
    dept = post.get("department", "")
    verified_on = post.get("verifiedOn", "2026-11-26")
    deadline = post.get("deadline", "")
    expired_flag = is_expired(post, now)

    action_box = ""
    if not expired_flag and cat in JOB_CATS and post.get("applyUrl"):
        apply_label, is_pending = application_display(post)
        link_type = "VERIFICATION_PENDING" if is_pending else post.get("applyLinkType") or (
            "VERIFICATION_PENDING" if is_pending else "GENERAL_RECRUITMENT_PORTAL"
        )
        type_badge_map = {
            "DIRECT_APPLICATION_FORM": '<span class="apply-type-badge direct">सीधा ऑनलाइन आवेदन फ़ॉर्म (Direct Form)</span>',
            "GENERAL_RECRUITMENT_PORTAL": '<span class="apply-type-badge portal">सामान्य सरकारी भर्ती पोर्टल (General Portal)</span>',
            "OFFLINE_POSTAL_FORM": '<span class="apply-type-badge portal">ऑफलाइन डाक आवेदन (Postal Form)</span>',
            "VERIFICATION_PENDING": '<span class="apply-type-badge pending">लिंक सत्यापन प्रतीक्षित (Verification Pending)</span>',
        }
        type_badge = type_badge_map.get(link_type, "")
        apply_cls = "pending-btn" if is_pending else "apply-btn"
        box_cls = "apply-box pending-box" if is_pending else "apply-box"
        instr = f'<p>{e(post.get("applyInstructions"))}</p>' if post.get("applyInstructions") else ""
        otr = (
            " " + ext_link(post["otrUrl"], "OTR Registration / Login", "notice-btn")
            if post.get("otrUrl")
            else ""
        )
        action_box = (
            f'<div class="{box_cls}" data-apply-box data-deadline="{e(deadline)}" data-apply-type="{e(link_type)}">'
            + (f'<div style="margin-bottom:6px">{type_badge}</div>' if type_badge else "")
            + ext_link(post["applyUrl"], apply_label, apply_cls)
            + " "
            + ext_link(post.get("notificationUrl") or post["officialUrl"], "Official Notification", "notice-btn")
            + otr
            + instr
            + "</div>"
        )
    elif expired_flag:
        action_box = (
            '<div class="closed-banner" lang="hi"><strong>आवेदन समाप्त (Application Closed):</strong> '
            'इस भर्ती/अपडेट की अंतिम तिथि समाप्त हो चुकी है। नीचे संबंधित सक्रिय सरकारी भर्तियाँ देखें।</div>'
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
        f'<tr><th scope="row">{e(k)}</th><td>{e(v)}</td></tr>'
        for k, v in rows
    )

    dates_list = list(post.get("detailDates") or [])
    fees_list = list(post.get("detailFees") or [])
    age_list = list(post.get("detailAge") or [])
    if not dates_list:
        if post.get("startDate"):
            dates_list.append(f"Application Start: {post['startDate']}")
        if post.get("lastDate"):
            dates_list.append(f"Last Date: {post['lastDate']}")
        elif post.get("noticeDate"):
            dates_list.append(f"Notice Date: {post['noticeDate']}")
    if not fees_list:
        for k, v in rows:
            if "fee" in str(k).lower() or "शुल्क" in str(k):
                fees_list.append(f"{k}: {v}")
    if not age_list:
        for k, v in rows:
            if "age" in str(k).lower() or "आयु" in str(k):
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
            f"<section><h3>Important Dates — महत्वपूर्ण तिथियाँ</h3><ul>{d_li}</ul></section>"
            f"<section><h3>Application Fee — आवेदन शुल्क</h3><ul>{f_li}</ul></section>"
            f"<section><h3>Age Limit — आयु सीमा</h3><ul>{a_li}</ul></section>"
            f'<section class="vacancy"><h3>Total Vacancies — कुल पद</h3><strong>{e(v_str)}</strong><p>{e(v_sub)}</p></section>'
            "</div>"
        )

    how_html = ""
    if not expired_flag:
        if post.get("howToApply"):
            steps_li = "".join(f"<li>{e(st)}</li>" for st in post["howToApply"])
            how_html = f'<h2 class="detail-bar">How to Apply — आवेदन कैसे करें</h2><ol>{steps_li}</ol>'
        elif cat in JOB_CATS:
            is_offline = "offline" in str(post.get("applyLabel", "")).lower() or "डाक" in str(post.get("applyLabel", ""))
            if is_offline:
                how_html = (
                    '<h2 class="detail-bar">How to Apply (Postal / Offline) — डाक से आवेदन</h2>'
                    "<ol><li>Download and read the official notification PDF carefully.</li>"
                    "<li>Fill the prescribed offline application format with self-attested copies of documents.</li>"
                    "<li>Send via Speed Post / Registered Post to the exact address before the closing date.</li>"
                    "<li>Keep the postal dispatch receipt safely for future reference.</li></ol>"
                )
            else:
                how_html = (
                    '<h2 class="detail-bar">How to Apply — आवेदन कैसे करें</h2>'
                    "<ol><li>Read the full official notification PDF before starting registration.</li>"
                    "<li>Click the official Apply Online portal link above and complete OTR/registration.</li>"
                    "<li>Fill accurate details, upload required photo/signature/documents, and pay applicable fee before deadline.</li>"
                    "<li>Download and save the final submitted application confirmation page.</li></ol>"
                )

    faq_pairs = build_auto_faqs(post)
    faq_html = ""
    if faq_pairs:
        faq_items = "".join(
            f"<details><summary>{e(q)}</summary><p>{e(ans)}</p></details>" for q, ans in faq_pairs
        )
        faq_html = f"<h2>Frequently Asked Questions — सामान्य प्रश्न</h2>{faq_items}"

    links = []
    if not expired_flag and cat in JOB_CATS and post.get("applyUrl"):
        tbl_label, _ = application_display(post)
        links.append((tbl_label, post["applyUrl"]))
    if not expired_flag and post.get("actionUrl"):
        links.append((post.get("actionLabel") or "Direct Official Link", post["actionUrl"]))
    if not expired_flag and post.get("otrUrl"):
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

    summary = clean_text(post.get("summary") or f"{title} — Official verified update from {dept}.")
    elig_hi = clean_text(post.get("eligibilityHi") or "")
    elig_hi_html = (
        f'<p class="notice" lang="hi"><strong>योग्यता व मुख्य विवरण:</strong> {e(elig_hi)}</p>'
        if elig_hi
        else ""
    )
    checklist_html = build_checklist_box(post) if not expired_flag else ""
    related_html = render_related_block(related_items)

    body = (
        '<article class="article detail">'
        f'<a href="../../">Home</a> › <a href="../../category/{e(cat)}/">{category_label(cat)}</a>'
        f"<h1>{e(title)}</h1>"
        + (f'<p lang="hi" class="hindi"><strong>{e(post["titleHi"])}</strong></p>' if post.get("titleHi") and post["titleHi"] != title else "")
        + f"{action_box}"
        f"{ssl_warn}"
        f'<p>Published &amp; Verified: {e(verified_on)} · Department: <strong>{e(dept)}</strong></p>'
        f'<p lang="hi">{e(summary)}</p>'
        + (f'<p lang="en">{e(post["summaryEn"])}</p>' if post.get("summaryEn") else "")
        + f"{elig_hi_html}"
        '<div class="detail-box">'
        f'<div class="detail-heading"><h2>{e(title)}</h2><p>{e(dept)} · Verified Official Update</p><strong>SARKARI ALERT</strong></div>'
        f"{grid_html}"
        '<h2 class="detail-bar">Important Dates, Eligibility, Fees &amp; Details — तिथियाँ, पात्रता, शुल्क व विवरण</h2>'
        f"<table><tbody>{rows_html}</tbody></table>"
        f"{how_html}"
        '<h2 class="detail-bar">Important Official Links — महत्वपूर्ण आधिकारिक लिंक</h2>'
        f'<table class="important-links"><tbody>{links_html}</tbody></table>'
        "</div>"
        f"{checklist_html}"
        f"{related_html}"
        f"{faq_html}"
        '<p class="warning">Confirm current dates, eligibility, and fees against the original official notification. Sarkari Alert never collects application fees or personal documents.</p>'
        "</article>"
    )

    page_url = f"{BASE}posts/{post['id']}/"
    eligible_jp = is_jobposting_eligible(post, now)
    if eligible_jp:
        vt = normalize_valid_through(post)
        org_obj = {"@type": "Organization", "name": dept}
        if post.get("officialUrl"):
            org_obj["sameAs"] = post["officialUrl"]
        loc_locality, loc_region = resolve_verified_location(post)
        desc_bullets = "".join(f"<li><strong>{e(k)}:</strong> {e(v)}</li>" for k, v in rows[:10])
        elig_para = f"<p><strong>Eligibility:</strong> {e(elig_hi)}</p>" if elig_hi else ""
        instr_para = f"<p><strong>Application Process:</strong> {e(post.get('applyInstructions'))}</p>" if post.get("applyInstructions") else ""
        full_jp_desc = (
            f"<p>{e(summary)}</p>"
            f"{elig_para}"
            f"<ul><li><strong>Hiring Organization:</strong> {e(dept)}</li>"
            f"<li><strong>Location:</strong> {e(loc_locality)}, {e(loc_region)}, India</li>"
            f"<li><strong>Last Date:</strong> {e(post.get('lastDate') or vt[:10])}</li>"
            f"{desc_bullets}</ul>"
            f"{instr_para}"
        )
        raw_date_posted = post.get("noticeDate") or post.get("startDate") or post.get("publishedDate") or verified_on
        actual_date_posted = raw_date_posted if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(raw_date_posted)) else verified_on
        is_direct_form = post.get("applyLinkType") == "DIRECT_APPLICATION_FORM"
        ld_main = {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": title,
            "description": full_jp_desc,
            "datePosted": actual_date_posted,
            "dateModified": verified_on,
            "validThrough": vt,
            "employmentType": infer_employment_type(post),
            "hiringOrganization": org_obj,
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": loc_locality,
                    "addressRegion": loc_region,
                    "addressCountry": "IN",
                },
            },
            "applicantLocationRequirements": {"@type": "Country", "name": "IN"},
            "directApply": is_direct_form,
            "url": page_url,
        }
        if post.get("noticeId"):
            ld_main["identifier"] = {"@type": "PropertyValue", "name": dept, "value": post["noticeId"]}
    else:
        # Expired or non-job updates NEVER carry active JobPosting markup
        ld_main = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": summary,
            "datePublished": post.get("publishedDate", verified_on),
            "dateModified": verified_on,
            "publisher": {"@type": "Organization", "name": "Sarkari Alert"},
            "mainEntityOfPage": page_url,
        }

    ld = [
        ld_main,
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE},
                {"@type": "ListItem", "position": 2, "name": cat_en, "item": f"{BASE}category/{cat}/"},
                {"@type": "ListItem", "position": 3, "name": title, "item": page_url},
            ],
        },
    ]

    seo_title = title_override or make_seo_title(title)
    cat_tpl = CATEGORY_SEO.get(cat, {}).get("desc_template", "{title} — {dept}.")
    vac_phrase = f"{vac_val:,} Posts" if isinstance(vac_val, int) else (str(vac_val) if vac_val else "Verified Update")
    fallback_desc = cat_tpl.format(
        title=title,
        dept=dept,
        vac_phrase=vac_phrase,
        qual=post.get("qualification") or "As per Notice",
        last_date=post.get("lastDate") or "Official Notice",
        title_en=title,
        title_hi=title,
    )
    seo_desc = desc_override or make_seo_desc(summary, fallback_extra=fallback_desc)
    robots = "noindex,follow" if expired_flag else "index,follow,max-image-preview:large"

    return render_shell(
        "../../",
        seo_title,
        seo_desc,
        f"posts/{post['id']}/",
        body,
        ld,
        site_cfg=site_cfg,
        robots=robots,
        page_type="post",
        page_category=cat,
        post_id=post["id"],
    )


def render_referrals_page(referrals, site_cfg=None):
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
        make_seo_title("Loans & Credit Cards Referral Desk"),
        make_seo_desc("Separate partner referral directory for education loans, personal/MSME loans, and credit cards from verified commercial banking institutions."),
        "loans-and-cards/",
        body,
        site_cfg=site_cfg,
        page_type="referrals",
        page_category="loans-and-cards",
    )


def render_html_sitemap(active_posts, schemes, by_cat, site_cfg=None):
    sections = []
    for slug, en, hi, _ in CATEGORIES:
        if slug == "yojana":
            lis = "".join(
                f'<li><a href="../posts/{e(s["id"])}/">{e(s.get("titleHi") or s["title"])}</a> <small>({e(s.get("stateOrUt") or "India")})</small></li>'
                for s in schemes
            )
            sections.append(f'<section><h2><a href="../category/yojana/">{e(en)} ({len(schemes)}) — {e(hi)}</a></h2><ul>{lis}</ul></section>')
        else:
            items = by_cat.get(slug, [])
            if not items:
                continue
            lis = "".join(
                f'<li><a href="../posts/{e(p["id"])}/">{e(p["title"])}</a> <small>({e(p.get("verifiedOn") or "")})</small></li>'
                for p in items
            )
            sections.append(f'<section><h2><a href="../category/{slug}/">{e(en)} ({len(items)}) — {e(hi)}</a></h2><ul>{lis}</ul></section>')
    body = (
        '<article class="article">'
        '<a href="../">← Home</a>'
        '<h1>All Verified Updates &amp; Government Schemes Directory</h1>'
        f'<p class="notice" lang="hi">संपूर्ण वेबसाइट इंडेक्स: {len(active_posts)} सक्रिय सरकारी अपडेट और {len(schemes)} सरकारी योजनाएँ।</p>'
        + "".join(sections)
        + "</article>"
    )
    return render_shell(
        "../",
        make_seo_title("All Govt Jobs & Yojana Sitemap Directory"),
        make_seo_desc(f"Complete HTML directory of {len(active_posts)} active government jobs, results, admit cards & {len(schemes)} Sarkari Yojana entries on Sarkari Alert."),
        "sitemap/",
        body,
        site_cfg=site_cfg,
    )


def render_rss_feed(active_posts, now):
    items_xml = []
    for p in active_posts[:40]:
        link = f"{BASE}posts/{p['id']}/"
        pub_d = p.get("publishedDate") or p.get("verifiedOn") or now.date().isoformat()
        try:
            pub_dt = dt.datetime.fromisoformat(f"{pub_d}T09:00:00+05:30")
            rfc_date = pub_dt.strftime("%a, %d %b %Y %H:%M:%S +0530")
        except ValueError:
            rfc_date = now.strftime("%a, %d %b %Y %H:%M:%S +0530")
        items_xml.append(
            "<item>"
            f"<title>{e(p['title'])}</title>"
            f"<link>{e(link)}</link>"
            f"<guid isPermaLink=\"true\">{e(link)}</guid>"
            f"<pubDate>{rfc_date}</pubDate>"
            f"<category>{e(CAT_MAP[p['category']][0])}</category>"
            f"<description>{e(p.get('summary') or p['title'])}</description>"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
        "<channel>"
        "<title>Sarkari Alert — Verified Govt Jobs &amp; Results</title>"
        f"<link>{BASE}</link>"
        f'<atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/>'
        "<description>Verified government jobs, exam results, admit cards, answer keys, and Sarkari Yojana updates.</description>"
        "<language>en-IN</language>"
        + "".join(items_xml)
        + "</channel></rss>\n"
    )


def ensure_unique_seo_meta(items, is_scheme=False):
    """Precompute unique SEO <title> and <meta description> for all posts/schemes."""
    used_titles = set()
    used_descs = set()
    meta_map = {}
    for item in items:
        pid = item["id"]
        if is_scheme:
            raw_t = f"{item.get('titleHi') or item['title']} ({item.get('stateOrUt', 'India')})"
            raw_d = f"{item['title']} ({item.get('titleHi') or ''}) — {item.get('department', '')} योजना के लाभ, पात्रता, आवश्यक दस्तावेज व आधिकारिक वेबसाइट।"
            extra = item.get("eligibility", "")
        else:
            raw_t = item["title"]
            raw_d = clean_text(item.get("summary", ""))
            cat = item.get("category", "latest-jobs")
            tpl = CATEGORY_SEO.get(cat, {}).get("desc_template", "{title} — {dept}.")
            vac_val = item.get("vacancies")
            vac_phrase = f"{vac_val:,} Posts" if isinstance(vac_val, int) else (str(vac_val) if vac_val else "Verified Update")
            extra = tpl.format(
                title=item["title"],
                dept=item.get("department", ""),
                vac_phrase=vac_phrase,
                qual=item.get("qualification") or "विज्ञापन के अनुसार",
                last_date=item.get("lastDate") or "Official Notice",
                title_en=item["title"],
                title_hi=item["title"],
            )

        t = make_seo_title(raw_t)
        if t.casefold() in used_titles:
            cat_tag = "Scheme" if is_scheme else CAT_MAP.get(item.get("category", ""), ("Update",))[0]
            nid = item.get("noticeId") or item.get("stateOrUt") or pid
            suffix_tag = clean_text(f"{cat_tag} {nid}")[:22]
            short_base = clean_text(raw_t)[: max(16, 48 - len(suffix_tag) - 3)].rsplit(" ", 1)[0].rstrip(" –—-:,(/&")
            t = make_seo_title(f"{short_base} ({suffix_tag})")
        if t.casefold() in used_titles:
            t = make_seo_title(f"{raw_t[:26].strip()} [{pid[:18]}]")
        used_titles.add(t.casefold())

        d = make_seo_desc(raw_d, fallback_extra=extra)
        if d.casefold() in used_descs:
            # Disambiguate cleanly with post role/title + noticeId so duplicate descriptions never happen
            role_prefix = clean_text(item.get("title", "").split("–")[0])[:55]
            d = make_seo_desc(f"{role_prefix}: {raw_d}", fallback_extra=extra)
        used_descs.add(d.casefold())
        meta_map[pid] = (t, d)
    return meta_map


def semantic_fp(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]


def update_sitemap_lastmod(urls, files, now_date, base_dates, semantic_hashes=None, state_path=None):
    """Maintain genuine per-URL lastmod in data/seo_state.json based on substantive content hashes."""
    state_path = Path(state_path) if state_path else (ROOT / "data/seo_state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    entries = dict(state.get("urls") or {})
    changed = False

    rel_for_url = {BASE: "index.html"}
    for u in urls:
        if u != BASE and u.startswith(BASE):
            rel_for_url[u] = u[len(BASE):] + "index.html"

    lastmods = {}
    semantic_hashes = semantic_hashes or {}
    for u in urls:
        rel = rel_for_url.get(u, "")
        fp = semantic_hashes.get(u) or ""
        if not fp:
            content = files.get(rel, "")
            fp = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16] if content else ""
        default_lm = base_dates.get(u) or now_date.isoformat()
        prev = entries.get(u)
        if not prev:
            entries[u] = {"hash": fp, "lastmod": default_lm}
            changed = True
        elif fp and prev.get("hash") != fp:
            entries[u] = {"hash": fp, "lastmod": now_date.isoformat()}
            changed = True
        lastmods[u] = entries[u]["lastmod"]

    new_state_obj = {"updatedAt": now_date.isoformat(), "urls": {u: entries[u] for u in urls}}
    if changed or not state_path.exists():
        files["data/seo_state.json"] = json.dumps(new_state_obj, ensure_ascii=False, indent=2) + "\n"
    return lastmods


def build_all(now=None, prune_expired=False, posts_override=None):
    now = now or dt.datetime.now(get_ist())
    now_date = now.date()
    site_cfg = load_site_config()

    posts_path = ROOT / "data/posts.json"
    schemes_path = ROOT / "data/schemes_directory.json"
    referrals_path = ROOT / "data/referrals.json"
    monitor_path = ROOT / "data/monitor_status.json"

    posts_data = (
        json.loads(json.dumps(posts_override))
        if posts_override is not None
        else json.loads(posts_path.read_text(encoding="utf-8"))
    )
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

    active_posts.sort(
        key=lambda x: (x.get("publishedDate") or x.get("verifiedOn") or "", x.get("lastDate") or ""),
        reverse=True,
    )

    files = {}
    post_meta = ensure_unique_seo_meta(active_posts, is_scheme=False)
    scheme_meta = ensure_unique_seo_meta(schemes, is_scheme=True)

    from public_search import public_feed
    files["data/public-search.json"] = public_feed(active_posts, schemes, BASE, now)

    # 1. Render all active non-scheme posts with unique meta & related internal links
    for p in active_posts:
        rel_items = find_related_posts(p, active_posts, schemes=schemes, is_scheme=False)
        t_ov, d_ov = post_meta[p["id"]]
        files[f"posts/{p['id']}/index.html"] = render_standard_post(
            p, now=now, related_items=rel_items, site_cfg=site_cfg, title_override=t_ov, desc_override=d_ov
        )

    # 2. Render any newly expired posts cleanly WITHOUT JobPosting markup (Task #8)
    for ep in expired_posts:
        rel_items = find_related_posts(ep, active_posts, schemes=schemes, is_scheme=False)
        files[f"posts/{ep['id']}/index.html"] = render_standard_post(
            ep, now=now, related_items=rel_items, site_cfg=site_cfg
        )

    # 3. Render all verified Sarkari Yojana pages (NO Apply buttons)
    for s in schemes:
        rel_items = find_related_posts(s, active_posts, schemes=schemes, is_scheme=True)
        t_ov, d_ov = scheme_meta[s["id"]]
        files[f"posts/{s['id']}/index.html"] = render_scheme_post(
            s, related_items=rel_items, site_cfg=site_cfg, title_override=t_ov, desc_override=d_ov
        )

    # 4. Group active posts by category
    by_cat = {slug: [] for slug, _, _, _ in CATEGORIES}
    for p in active_posts:
        c = p.get("category")
        if c in by_cat:
            by_cat[c].append(p)
        ec = p.get("extraCategory")
        if ec and ec in by_cat and p not in by_cat[ec]:
            by_cat[ec].append(p)

    # 5. Render all 13 category pages
    for slug, en, hi, _ in CATEGORIES:
        seo_meta = CATEGORY_SEO.get(slug, {})
        if slug == "yojana":
            upcoming_s = [s for s in schemes if s.get("upcoming")]
            upc_bar = ""
            if upcoming_s:
                upc_links = " · ".join(
                    f'<a href="../../posts/{e(s["id"])}/">{e(s.get("titleHi") or s["title"])}</a>'
                    for s in upcoming_s
                )
                upc_bar = (
                    '<div class="monitor-bar"><div>'
                    '<span class="monitor-badge">Upcoming Schemes Watch</span> '
                    f'<span lang="hi">{upc_links}</span></div></div>'
                )
            items_html = "".join(render_item(s, "../../", is_scheme=True, now_date=now_date) for s in schemes)
            body = (
                '<article class="article">'
                '<a href="../../">← Home</a>'
                f"<h1>{e(en)} ({len(schemes)}) — {e(hi)}</h1>"
                f'<p class="notice" lang="hi"><strong>कुल {len(schemes)} सत्यापित सरकारी योजनाएँ</strong> (केंद्रीय + सभी 28 राज्य और 8 केंद्र शासित प्रदेश) · पात्रता, लाभ, आवश्यक दस्तावेज और आधिकारिक वेबसाइट विवरण। सरकारी योजनाओं के लिए अलग Apply बटन नहीं दिए गए हैं।</p>'
                f"{upc_bar}<ul>{items_html}</ul>"
                "</article>"
            )
            desc = make_seo_desc(
                f"{en} 2026 — Complete directory of {len(schemes)} central, 28 state and 8 UT government welfare schemes with eligibility, benefits, documents and official websites."
            )
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
                    '<span class="monitor-badge">Live 2-Hour Monitor</span> <strong>' + e(m["name"]) + "</strong>: "
                    f'<span lang="hi">{e(m.get("summaryHi") or m["summary"])}</span></div>'
                    + ext_link(m["url"], "Check Official RTE Portal", "notice-btn")
                    + "</div>"
                )
            intro_hi = seo_meta.get("intro_hi", "")
            intro_html = f'<p class="notice" lang="hi">{e(intro_hi)}</p>' if intro_hi else ""
            body = (
                '<article class="article">'
                '<a href="../../">← Home</a>'
                f'<h1>{e(en)} ({len(items)}) <small lang="hi">({e(hi)})</small></h1>'
                f"{intro_html}{extra_mon}{list_block}"
                "</article>"
            )
            desc = make_seo_desc(
                f"{en} 2026 ({hi}) — Verified {len(items)} active updates, deadlines, eligibility and official portal links on Sarkari Alert."
            )
        cat_ld = [
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": f"{en} | Sarkari Alert",
                "description": desc,
                "url": f"{BASE}category/{slug}/",
            },
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": en, "item": f"{BASE}category/{slug}/"},
                ],
            },
        ]
        files[f"category/{slug}/index.html"] = render_shell(
            "../../",
            make_seo_title(f"{en} 2026 ({hi})"),
            desc,
            f"category/{slug}/",
            body,
            cat_ld,
            site_cfg=site_cfg,
            page_type="category",
            page_category=slug,
        )

    # 6. Render Separate Loans & Credit Cards Referral Page + HTML Sitemap Directory
    files["loans-and-cards/index.html"] = render_referrals_page(referrals, site_cfg=site_cfg)
    files["sitemap/index.html"] = render_html_sitemap(active_posts, schemes, by_cat, site_cfg=site_cfg)

    # 7. Render Static Info Pages & 404 (noindex on 404)
    privacy_body = (
        '<article class="article"><a href="../">← Home</a><h1>Privacy Policy</h1>'
        "<p>Sarkari Alert does not require user accounts or collect Aadhaar numbers, PAN details, bank information, passwords, or personal application documents. External government recruitment portals and partner links follow their own privacy policies.</p>"
        "<h2>Google Analytics 4 (Measurement ID: G-K7T49V1PWN)</h2>"
        "<p>Sarkari Alert uses Google Analytics 4 solely for aggregated, privacy-preserving traffic insights (page views, category visits, notification notice clicks, Apply Online outbound clicks, and partner referral clicks).</p>"
        "<ul>"
        "<li><strong>No PII Collected:</strong> Personally identifiable information (names, emails, phone numbers, Aadhaar, form inputs, and URL search query strings) is stripped before any analytics payload is sent.</li>"
        "<li><strong>IP Anonymization &amp; Zero Ad Profiling:</strong> <code>anonymize_ip</code> is enabled and Google Signals / ad personalization signals are disabled.</li>"
        '<li><strong>Your Consent Controls:</strong> Current status: <strong id="privacy-consent-state">Checking…</strong>. You may allow or opt out of analytics at any time using the buttons below or via <em>Analytics &amp; Privacy Settings</em> in the footer.</li>'
        "</ul>"
        '<div class="consent-actions" style="margin:14px 0">'
        '<button type="button" id="privacy-allow-analytics" class="consent-accept">Allow Anonymized Analytics</button>'
        '<button type="button" id="privacy-deny-analytics" class="consent-decline">Opt Out (Disable Analytics)</button>'
        "</div>"
        '<h2 lang="hi">गोपनीयता व एनालिटिक्स नीति (Privacy Policy — हिंदी)</h2>'
        '<p class="notice" lang="hi">Sarkari Alert किसी भी यूज़र का व्यक्तिगत डेटा (नाम, ईमेल, मोबाइल, आधार या बैंक विवरण) एकत्र नहीं करता और न ही Google Analytics को कोई PII भेजता है। केवल अनाम विज़िट व आधिकारिक लिंक क्लिक आँकड़ों के लिए GA4 का उपयोग होता है, जिसे आप ऊपर दिए गए बटन से कभी भी बंद (Opt Out) कर सकते हैं।</p>'
        "</article>"
    )
    files["privacy/index.html"] = render_shell(
        "../",
        make_seo_title("Privacy Policy & Analytics Consent"),
        make_seo_desc("Sarkari Alert Privacy Policy: Zero PII policy, anonymized Google Analytics 4 consent controls, and official external portal safety notice."),
        "privacy/",
        privacy_body,
        site_cfg=site_cfg,
        page_type="static",
    )

    static_pages = [
        ("about", "About Us", "Sarkari Alert is an independent information portal for verified government recruitment, examination, admission, result, and welfare scheme updates. It is not affiliated with any government agency."),
        ("disclaimer", "Disclaimer", "Always verify eligibility, deadlines, fees, and official instructions directly on the original issuing government website or notification PDF before applying. Sarkari Alert never accepts application fees."),
    ]
    for slug, heading, text in static_pages:
        body = f'<article class="article"><a href="../">← Home</a><h1>{e(heading)}</h1><p>{e(text)}</p></article>'
        files[f"{slug}/index.html"] = render_shell(
            "../", make_seo_title(heading), make_seo_desc(text), f"{slug}/", body, site_cfg=site_cfg, page_type="static"
        )

    files["404.html"] = render_shell(
        "/sarkarialert/",
        make_seo_title("Page Not Found (404)"),
        make_seo_desc("Requested page was not found on Sarkari Alert. Browse active latest government jobs, results, admit cards, and Sarkari Yojana updates."),
        "404.html",
        '<h1>Page not found</h1><p><a href="/sarkarialert/">Return to Sarkari Alert Home</a></p>',
        root_relative=True,
        site_cfg=site_cfg,
        robots="noindex,follow",
    )

    # 8. Render Homepage (index.html)
    depts = sorted({p.get("department") for p in active_posts + schemes if p.get("department")})
    quals = sorted({p.get("qualification") for p in active_posts if p.get("qualification")})
    dept_opts = '<option value="">All departments — सभी विभाग</option>' + "".join(f"<option>{e(d)}</option>" for d in depts)
    qual_opts = '<option value="">All qualifications — सभी योग्यताएँ</option>' + "".join(f"<option>{e(q)}</option>" for q in quals)

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
        f'{e(p["title"])}<small>{e(CAT_MAP[p["category"]][0])}</small></a>'
        for i, p in enumerate(hl_candidates)
    )

    ticker_links = " · ".join(
        f'<a href="./posts/{e(p["id"])}/">{e(p["title"])}</a>'
        for p in (by_cat["latest-jobs"][:2] + by_cat["results"][:1] + by_cat["answer-key"][:1])
    )

    tiles_html = "".join(
        f'<a style="--tile:{color}" href="./category/{slug}/">{category_label(slug)}'
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
                f'<p class="inset" lang="hi"><strong>कुल {len(schemes)} योजनाएँ</strong> · केंद्रीय + सभी 28 राज्य व 8 UT (बिना अलग Apply बटन)।</p>'
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
                f'<h2><a href="./category/{slug}/">{category_label(slug)}{heading_count}</a></h2>'
                f"{content}"
                f'<a class="more" href="./category/{slug}/">View More — और देखें »</a></section>'
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
        f'<div class="ticker"><strong>LIVE UPDATES — ताज़ा अपडेट:</strong> {ticker_links}</div>'
        f'<div class="highlight-grid">{hl_html}</div>'
        f"{rte_html}"
        '<div class="quick-links">'
        '<a href="./category/latest-jobs/">Latest Jobs</a>'
        '<a href="./category/results/">Exam Results</a>'
        '<a href="./category/admit-card/">Admit Cards</a>'
        '<a href="./category/answer-key/">Answer Key</a>'
        f'<a href="./category/yojana/">Sarkari Yojana ({len(schemes)})</a>'
        '<a href="./category/upcoming-jobs/">Upcoming Jobs</a>'
        '<a href="./sitemap/">All Updates Directory</a>'
        '<a href="./loans-and-cards/">Loans &amp; Cards Referral</a>'
        "</div>"
        '<p><a href="./assets/smart-search.html" class="smart-page-link">Smart Search — हिंदी / English</a></p>'
        '<form id="search" class="search">'
        '<input id="query" type="search" aria-label="Search posts" placeholder="Search jobs, results, schemes, exams…">'
        f'<select id="department" aria-label="Department">{dept_opts}</select>'
        f'<select id="qualification" aria-label="Qualification">{qual_opts}</select>'
        '<button type="submit">Search — खोजें</button><button type="reset" class="reset">Reset — रीसेट</button>'
        "</form>"
        '<p id="search-status" role="status" hidden></p>'
        f'<div class="tiles">{tiles_html}</div>'
        f'<div class="panels">{"".join(panels_html)}</div>'
        '<div class="referral-banner">'
        '<div><strong>Separate Partner Referral Desk — Loans &amp; Credit Cards</strong>'
        '<p style="margin:4px 0 0;font-size:14px">Non-government commercial banking offers, education loans &amp; credit cards separated from government listings.</p></div>'
        '<a class="referral-cta" href="./loans-and-cards/">Explore Loans &amp; Credit Cards »</a></div>'
        '<section class="about"><h2>About Sarkari Alert</h2>'
        f"<p>Sarkari Alert publishes verified official government recruitment notices, results, admit cards, answer keys, admissions, scholarships, exam calendars, and {len(schemes)} central, 28 state &amp; 8 UT government welfare schemes. Automated checks run every 2 hours to monitor updates and exclude expired forms.</p></section>"
    )

    home_ld = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Sarkari Alert",
            "url": BASE,
            "potentialAction": {
                "@type": "SearchAction",
                "target": BASE + "?q={search_term_string}",
                "query-input": "required name=search_term_string",
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Sarkari Alert",
            "url": BASE,
            "logo": f"{BASE}assets/favicon.svg",
        },
    ]
    files["index.html"] = render_shell(
        "./",
        "Latest Govt Jobs 2026, Results, Sarkari Yojana | Sarkari Alert",
        make_seo_desc(
            f"Sarkari Alert: Verified government jobs 2026, Sarkari Result, admit cards, answer keys, scholarships & {len(schemes)} central/state Sarkari Yojana guides."
        ),
        "",
        home_main,
        home_ld,
        site_cfg=site_cfg,
        page_type="home",
    )

    # 9. Build sitemap.xml with accurate per-URL lastmod (substantive data fingerprint), feed.xml, robots.txt, ads.txt & optional IndexNow key file
    urls = [BASE]
    base_dates = {BASE: max([p.get("verifiedOn") or now_date.isoformat() for p in active_posts] or [now_date.isoformat()])}
    mon_summary = (monitors[0].get("summaryHi") if monitors else "")
    semantic_hashes = {
        BASE: semantic_fp({
            "posts": [(p["id"], p.get("verifiedOn"), p.get("lastDate"), p.get("applyStatus")) for p in active_posts],
            "schemes": [(s["id"], s.get("verifiedOn")) for s in schemes],
            "monitor": mon_summary,
        })
    }
    for slug, _, _, _ in CATEGORIES:
        u = f"{BASE}category/{slug}/"
        urls.append(u)
        if slug == "yojana":
            base_dates[u] = max([s.get("verifiedOn") or now_date.isoformat() for s in schemes] or [now_date.isoformat()])
            semantic_hashes[u] = semantic_fp([(s["id"], s.get("verifiedOn"), s.get("title")) for s in schemes])
        else:
            cat_dates = [p.get("verifiedOn") or p.get("publishedDate") or now_date.isoformat() for p in by_cat[slug]]
            base_dates[u] = max(cat_dates) if cat_dates else now_date.isoformat()
            semantic_hashes[u] = semantic_fp(
                [(p["id"], p.get("verifiedOn"), p.get("lastDate"), p.get("applyStatus")) for p in by_cat[slug]]
            )
    for extra in ("sitemap/", "loans-and-cards/", "about/", "privacy/", "disclaimer/"):
        u = f"{BASE}{extra}"
        urls.append(u)
        base_dates[u] = base_dates[BASE] if extra == "sitemap/" else "2026-11-26"
        if extra == "sitemap/":
            semantic_hashes[u] = semantic_hashes[BASE]
        elif extra == "loans-and-cards/":
            semantic_hashes[u] = semantic_fp(referrals)
        else:
            semantic_hashes[u] = semantic_fp(extra)
    for p in active_posts:
        u = f"{BASE}posts/{p['id']}/"
        urls.append(u)
        base_dates[u] = p.get("verifiedOn") or p.get("publishedDate") or now_date.isoformat()
        semantic_hashes[u] = semantic_fp({
            k: p.get(k)
            for k in (
                "title", "titleHi", "category", "department", "summary", "eligibilityHi",
                "vacancies", "qualification", "noticeDate", "startDate", "lastDate", "deadline",
                "applyUrl", "applyLinkType", "applyStatus", "applyInstructions",
                "notificationUrl", "officialUrl", "rows", "verifiedOn",
            )
        })
    for s in schemes:
        u = f"{BASE}posts/{s['id']}/"
        urls.append(u)
        base_dates[u] = s.get("verifiedOn") or now_date.isoformat()
        semantic_hashes[u] = semantic_fp({
            k: s.get(k)
            for k in (
                "title", "titleHi", "category", "department", "summary",
                "officialUrl", "benefits", "eligibility", "documents", "verifiedOn",
            )
        })

    lastmods = update_sitemap_lastmod(urls, files, now_date, base_dates, semantic_hashes=semantic_hashes)
    url_tags = "".join(f"<url><loc>{e(u)}</loc><lastmod>{e(lastmods[u])}</lastmod></url>" for u in urls)
    files["sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{url_tags}</urlset>\n'
    )
    files["feed.xml"] = render_rss_feed(active_posts, now)
    files["robots.txt"] = f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n"

    pub_id = str((site_cfg.get("googleAdSense") or {}).get("publisherId", "")).strip()
    if pub_id.startswith("ca-pub-"):
        files["ads.txt"] = f"google.com, {pub_id.replace('ca-pub-', 'pub-')}, DIRECT, f08c47fec0942fa0\n"

    inow_key = os.environ.get("BING_INDEXNOW_KEY", "").strip()
    if re.fullmatch(r"[A-Za-z0-9-]{8,128}", inow_key):
        files[f"{inow_key}.txt"] = f"{inow_key}\n"

    if prune_expired and expired_posts:
        archived = list(posts_data.get("archivedExpiredIds") or [])
        for ep in expired_posts:
            if ep["id"] not in archived:
                archived.append(ep["id"])
        posts_data["posts"] = active_posts
        posts_data["archivedExpiredIds"] = archived
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
