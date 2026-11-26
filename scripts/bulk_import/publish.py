"""Validate and publish admin-approved records, prune expired jobs, and rebuild static site."""
import argparse, datetime as dt, html, json, re
from pathlib import Path
from discover import official, article_url, get_ist
from build_site import build_all, CATEGORIES, JOB_CATS

ROOT = Path(__file__).resolve().parents[2]
CATS = {slug: en for slug, en, _, _ in CATEGORIES}


def normalize(t):
    return re.sub(r"[\W_]+", "", t.casefold())


def validate(p, now):
    for key in ("id", "title", "category", "department", "noticeId", "notificationUrl", "officialUrl", "summary", "reviewedBy", "reviewedOn"):
        if not isinstance(p.get(key), str) or not p[key].strip():
            raise ValueError("missing " + key)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,90}", p["id"]):
        raise ValueError("invalid ID")
    if p["category"] not in CATS:
        raise ValueError("invalid category")
    if p.get("approved") is not True or p.get("officialFactsChecked") is not True:
        raise ValueError("approval and source review required")
    review = dt.date.fromisoformat(p["reviewedOn"])
    if review > now.date() or (now.date() - review).days > 7:
        raise ValueError("review date must be within 7 days")
    for key in ("officialUrl", "notificationUrl"):
        if not official(p[key]):
            raise ValueError("unapproved official domain: " + key)
    if not isinstance(p.get("rows"), list) or not p["rows"] or any(not isinstance(r, list) or len(r) != 2 for r in p["rows"]):
        raise ValueError("reviewed facts rows required")
    if p.get("discoveryUrl") and not official(p["discoveryUrl"]) and article_url(p["discoveryUrl"]) != p["discoveryUrl"]:
        raise ValueError("invalid discovery URL")
    if p["category"] == "yojana":
        if p.get("applyUrl") or p.get("actionUrl"):
            raise ValueError("scheme application links prohibited")
    if p["category"] in JOB_CATS:
        if not p.get("applyUrl") or not official(p["applyUrl"]) or p.get("applyLinkChecked") is not True:
            raise ValueError("reviewed official application link required")
        if p.get("applicationStatus") != "OPEN":
            raise ValueError("job not marked open")
        if not p.get("deadline"):
            raise ValueError("deadline required")
    if p.get("deadline"):
        deadline = dt.datetime.fromisoformat(p["deadline"])
        if deadline.tzinfo is None or deadline <= now:
            raise ValueError("expired/invalid deadline")
    return p


def build(approved, now, prune_expired=False):
    posts_path = ROOT / "data/posts.json"
    schemes_path = ROOT / "data/schemes_directory.json"
    db = json.loads(posts_path.read_text(encoding="utf-8"))
    directory = json.loads(schemes_path.read_text(encoding="utf-8"))["records"]

    old = db["posts"] + directory
    ids = {p["id"] for p in old}
    titles = {normalize(p["title"]) for p in old}
    notices = {(p.get("department", "").casefold(), p.get("noticeId")) for p in old if p.get("noticeId")}
    sourceids = {p.get("discoveryUrl") for p in old if p.get("discoveryUrl")}

    accepted = []
    rejected = []
    for row in approved:
        try:
            p = dict(validate(row, now))
            nk = (p["department"].casefold(), p["noticeId"])
            nt = normalize(p["title"])
            if p["id"] in ids or nt in titles or nk in notices or (p.get("discoveryUrl") and p.get("discoveryUrl") in sourceids):
                raise ValueError("duplicate or already published")
            ids.add(p["id"])
            titles.add(nt)
            notices.add(nk)
            if p.get("discoveryUrl"):
                sourceids.add(p["discoveryUrl"])
            p.update(verified=True, verifiedOn=p["reviewedOn"], publishedDate=now.date().isoformat())
            accepted.append(p)
        except (ValueError, TypeError, KeyError) as ex:
            rejected.append({"id": row.get("id") if isinstance(row, dict) else None, "reason": str(ex)})

    if not accepted and not prune_expired:
        return {}, rejected

    if accepted:
        db["posts"].extend(accepted)
    files, active, expired = build_all(now=now, prune_expired=prune_expired, posts_override=db)
    if accepted and "data/posts.json" not in files:
        files["data/posts.json"] = json.dumps(db, ensure_ascii=False, indent=2) + "\n"

    return files, rejected


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved", default="data/import_approved.json")
    ap.add_argument("--output", default="import-output/publish-report.json")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--prune-expired", action="store_true")
    args = ap.parse_args()

    rows = json.loads(Path(args.approved).read_text(encoding="utf-8"))["posts"]
    now = dt.datetime.now(get_ist())
    files, rejected = build(rows, now, prune_expired=args.prune_expired)

    if args.write:
        for path, content in files.items():
            dest = ROOT / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        # Clear published records from import_approved.json if accepted
        if rows and not rejected and "data/posts.json" in files:
            Path(args.approved).write_text('{"posts": []}\n', encoding="utf-8")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"changedFiles": sorted(files), "rejected": rejected, "written": args.write}, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Changed files:", len(files), "Skipped/rejected:", len(rejected))
