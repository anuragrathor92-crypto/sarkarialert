"""Smart Direct Apply Resolver & Verification Pending Unblocker.
1. Automatically resolves major Indian govt boards (RRB, SSC, UPSC, etc.) to their official direct registration portals.
2. Unblocks stuck VERIFICATION_PENDING jobs whenever a valid official .gov.in/.nic.in/.ac.in/.org.in URL is live, so students never miss Last Dates.
"""
from __future__ import annotations
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTS_PATH = ROOT / "data" / "posts.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

OFFICIAL_SUFFIXES = (".gov.in", ".nic.in", ".ac.in", ".edu.in", ".res.in", ".org.in")

# Verified official direct registration / online apply portals for top Indian recruitment boards
DIRECT_PORTAL_RULES = [
    (r"\b(rrb|railway recruitment board)\b", "https://www.rrbapply.gov.in/", "DIRECT_APPLICATION_FORM"),
    (r"\b(ssc|staff selection commission)\b", "https://ssc.gov.in/login", "DIRECT_APPLICATION_FORM"),
    (r"\b(upsc|union public service commission)\b", "https://upsconline.gov.in/", "DIRECT_APPLICATION_FORM"),
    (r"\b(uppsc|uttar pradesh public service)\b", "https://uppsc.up.nic.in/", "GENERAL_RECRUITMENT_PORTAL"),
    (r"\b(upsssc)\b", "https://upsssc.gov.in/", "GENERAL_RECRUITMENT_PORTAL"),
    (r"\b(icmr)\b", "https://recruitment.icmr.org.in/", "DIRECT_APPLICATION_FORM"),
    (r"\b(bhel)\b", "https://careers.bhel.in/", "DIRECT_APPLICATION_FORM"),
    (r"\b(nsp|national scholarship)\b", "https://scholarships.gov.in/", "DIRECT_APPLICATION_FORM"),
]


def is_official(url: str) -> bool:
    if not url or not url.startswith(("http://", "https://")):
        return False
    host = url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0].lower()
    return any(host.endswith(suf) for suf in OFFICIAL_SUFFIXES)


def is_reachable(url: str, timeout: int = 8) -> bool:
    if not is_official(url):
        return False
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return int(getattr(resp, "status", 200)) < 404
        except urllib.error.HTTPError as exc:
            if exc.code == 405 and method == "HEAD":
                continue
            # 403/429 on govt portals means server is live (WAF/bot filter)
            return exc.code in (403, 405, 429)
        except Exception:
            if method == "HEAD":
                continue
            return False
    return False


def resolve_all() -> int:
    if not POSTS_PATH.exists():
        return 0
    raw = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    posts = raw if isinstance(raw, list) else raw.get("posts", [])
    changed = 0

    for p in posts:
        if not isinstance(p, dict):
            continue
        cat = (p.get("category") or "").lower()
        if cat not in ("latest-jobs", "upcoming-jobs", "admission", "scholarship", "outsourcing"):
            continue

        hay = f"{p.get('title', '')} {p.get('department', '')} {p.get('id', '')}".lower()
        cur_type = (p.get("applyLinkType") or "").upper()
        cur_status = (p.get("applyStatus") or "").upper()
        cur_apply = (p.get("applyUrl") or "").strip()
        cur_off = (p.get("officialUrl") or "").strip()

        # 1. Upgrade known major boards from generic portal / pending to official direct registration URL
        if cur_type in ("", "VERIFICATION_PENDING", "GENERAL_RECRUITMENT_PORTAL") or cur_status == "VERIFICATION_PENDING":
            for pat, target_url, target_type in DIRECT_PORTAL_RULES:
                if re.search(pat, hay):
                    if cur_apply != target_url or cur_type != target_type or cur_status == "VERIFICATION_PENDING":
                        p["applyUrl"] = target_url
                        p["applyLinkType"] = target_type
                        if cur_status == "VERIFICATION_PENDING":
                            p["applyStatus"] = "ACTIVE"
                        if not cur_off:
                            p["officialUrl"] = target_url
                        changed += 1
                    break

        # 2. Unblock any remaining VERIFICATION_PENDING job that already has a live official URL
        if (p.get("applyLinkType") or "").upper() == "VERIFICATION_PENDING" or (p.get("applyStatus") or "").upper() == "VERIFICATION_PENDING":
            best = cur_apply if is_official(cur_apply) else (cur_off if is_official(cur_off) else "")
            if best and is_reachable(best):
                p["applyUrl"] = best
                p["applyLinkType"] = "GENERAL_RECRUITMENT_PORTAL"
                p["applyStatus"] = "ACTIVE"
                changed += 1
                print(f"Unblocked VERIFICATION_PENDING -> {best} for {p.get('id')}")

    if changed:
        out = posts if isinstance(raw, list) else {**raw, "posts": posts}
        POSTS_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Smart Apply Resolver complete: updated={changed}")
    return changed


if __name__ == "__main__":
    resolve_all()
