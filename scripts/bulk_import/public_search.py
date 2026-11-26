"""Public read-only search feed. Only already published, verified records."""
import json
import re

FIELDS = ("title", "titleHi", "category", "department", "qualification", "eligibilityHi",
          "noticeId", "publishedDate", "verifiedOn", "startDate", "lastDate",
          "deadline", "vacancies", "summary", "eligibility", "benefit",
          "requiredDocuments", "state", "stateOrUt", "scope", "theme",
          "locationLocality", "locationRegion", "applyLinkType",
          "extraCategory", "applicationStatus", "applyStatus", "linkStatus",
          "applyLabel", "applyInstructions", "rows", "officialUrl",
          "notificationUrl", "sourceUrl")

def public_feed(posts, schemes, base, now):
    records = []
    seen = set()
    for p in [*posts, *schemes]:
        pid = p.get("id")
        if not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,100}", pid):
            continue
        if pid in seen or p.get("verified") is not True:
            continue
        seen.add(pid)
        r = {k: p[k] for k in FIELDS if k in p}
        r.update(id=pid, url=base + "posts/" + pid + "/", verified=True)
        for k in ("officialUrl", "notificationUrl", "sourceUrl"):
            if k in r and (not isinstance(r[k], str) or not r[k].startswith("https://")):
                r.pop(k)
        pending = any("PENDING" in str(p.get(k, "")).upper() for k in ("applyStatus", "linkStatus", "applicationStatus")) or "pending" in str(p.get("applyLabel", "")).lower()
        if p.get("category") != "yojana" and not pending and str(p.get("applyUrl", "")).startswith("https://"):
            r["applyUrl"] = p["applyUrl"]
        r["verificationPending"] = pending
        records.append(r)
    return json.dumps({"schemaVersion": 1, "site": base,
                       "generatedOn": now.isoformat(timespec="seconds"),
                       "count": len(records), "records": records},
                      ensure_ascii=False, indent=2) + "\n"
