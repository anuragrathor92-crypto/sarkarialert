"""Google Indexing API & Bing IndexNow automation strictly for eligible JobPosting URLs."""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from build_site import BASE, ROOT, is_jobposting_eligible, load_site_config
from discover import get_ist

DEFAULT_STATE = ROOT / "data/indexing_state.json"
DEFAULT_OUTPUT = ROOT / "import-output/indexing-queue.json"
TOKEN_URL = "https://oauth2.googleapis.com/token"
INDEXING_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
SCOPE = "https://www.googleapis.com/auth/indexing"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sign_rs256(signing_input: bytes, private_key_pem: str) -> bytes:
    """Sign JWT payload with RS256 using cryptography if installed, else openssl CLI."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        return key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    except ImportError:
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="utf-8") as kf:
            kf.write(private_key_pem)
            key_path = kf.name
        try:
            res = subprocess.run(
                ["openssl", "dgst", "-sha256", "-sign", key_path],
                input=signing_input,
                capture_output=True,
                check=True,
            )
            return res.stdout
        finally:
            try:
                Path(key_path).unlink()
            except OSError:
                pass


def fetch_google_access_token(sa_json: dict) -> str:
    now_ts = int(dt.datetime.now(dt.timezone.utc).timestamp())
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    claims = b64url(
        json.dumps(
            {
                "iss": sa_json["client_email"],
                "scope": SCOPE,
                "aud": TOKEN_URL,
                "exp": now_ts + 3600,
                "iat": now_ts,
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    signing_input = f"{header}.{claims}".encode("ascii")
    sig = b64url(sign_rs256(signing_input, sa_json["private_key"]))
    jwt_assertion = f"{header}.{claims}.{sig}"

    body = urllib.parse.urlencode(
        {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt_assertion}
    ).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def job_fingerprint(post: dict) -> str:
    fields = {
        "title": post.get("title"),
        "category": post.get("category"),
        "department": post.get("department"),
        "noticeId": post.get("noticeId"),
        "lastDate": post.get("lastDate"),
        "deadline": post.get("deadline"),
        "applyUrl": post.get("applyUrl"),
        "notificationUrl": post.get("notificationUrl"),
        "verifiedOn": post.get("verifiedOn"),
        "vacancies": post.get("vacancies"),
    }
    return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def build_indexing_queue(now=None, state_path=DEFAULT_STATE, posts_path=None):
    """Identify eligible JobPosting URLs needing URL_UPDATED or URL_DELETED."""
    now = now or dt.datetime.now(get_ist())
    posts_file = Path(posts_path) if posts_path else (ROOT / "data/posts.json")
    posts_db = json.loads(posts_file.read_text(encoding="utf-8"))
    posts = posts_db.get("posts", [])
    archived_ids = list(posts_db.get("archivedExpiredIds") or [])

    state = json.loads(Path(state_path).read_text(encoding="utf-8")) if Path(state_path).exists() else {}
    tracked = dict(state.get("urls") or {})

    eligible_map = {}
    ineligible_or_expired = set(f"{BASE}posts/{pid}/" for pid in archived_ids)

    for p in posts:
        url = f"{BASE}posts/{p['id']}/"
        if is_jobposting_eligible(p, now):
            # Also confirm built HTML actually contains JobPosting JSON-LD if rendered on disk
            html_file = ROOT / f"posts/{p['id']}/index.html"
            if html_file.exists() and '"@type": "JobPosting"' not in html_file.read_text(encoding="utf-8"):
                continue
            eligible_map[url] = {
                "url": url,
                "type": "URL_UPDATED",
                "id": p["id"],
                "fingerprint": job_fingerprint(p),
                "validThrough": p.get("deadline") or p.get("lastDate"),
            }
        else:
            if url in tracked and tracked[url].get("status") != "DELETED":
                ineligible_or_expired.add(url)

    # Also catch any previously tracked active URL no longer eligible
    for prev_url, prev_meta in tracked.items():
        if prev_meta.get("status") == "ACTIVE" and prev_url not in eligible_map:
            ineligible_or_expired.add(prev_url)

    cfg = load_site_config().get("googleIndexingApi") or {}
    daily_limit = int(cfg.get("dailyLimit", 180))

    updated_queue = []
    for url, item in sorted(eligible_map.items()):
        prev = tracked.get(url)
        if not prev or prev.get("fingerprint") != item["fingerprint"] or prev.get("status") != "ACTIVE":
            updated_queue.append(item)

    deleted_queue = []
    for url in sorted(ineligible_or_expired):
        prev = tracked.get(url)
        if prev and prev.get("status") == "ACTIVE":
            deleted_queue.append({"url": url, "type": "URL_DELETED", "fingerprint": "expired", "id": url.rstrip("/").split("/")[-1]})

    combined = (deleted_queue + updated_queue)[:daily_limit]
    return {
        "generatedAt": now.isoformat(),
        "eligibleJobPostingCount": len(eligible_map),
        "updatedQueued": len(updated_queue),
        "deletedQueued": len(deleted_queue),
        "dailyQuotaLimit": daily_limit,
        "batch": combined,
        "eligibleMap": eligible_map,
        "tracked": tracked,
    }


def submit_google_indexing(queue_data, state_path=DEFAULT_STATE):
    sa_raw = os.environ.get("GOOGLE_INDEXING_SA_JSON", "").strip()
    if not sa_raw:
        return {"status": "AWAITING_AUTHORIZATION", "submitted": 0, "failed": 0, "results": []}

    batch = queue_data["batch"]
    if not batch:
        return {"status": "UP_TO_DATE", "submitted": 0, "failed": 0, "results": []}

    sa_json = json.loads(sa_raw)
    access_token = fetch_google_access_token(sa_json)
    tracked = dict(queue_data["tracked"])
    results = []
    submitted = 0
    failed = 0

    for item in batch:
        payload = json.dumps({"url": item["url"], "type": item["type"]}).encode("utf-8")
        req = urllib.request.Request(
            INDEXING_ENDPOINT,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                resp_body = json.loads(resp.read().decode("utf-8"))
                results.append({"url": item["url"], "type": item["type"], "httpStatus": resp.status, "ok": True})
                submitted += 1
                tracked[item["url"]] = {
                    "status": "DELETED" if item["type"] == "URL_DELETED" else "ACTIVE",
                    "fingerprint": item["fingerprint"],
                    "lastNotifiedAt": dt.datetime.now(get_ist()).isoformat(),
                    "notifyType": item["type"],
                }
        except urllib.error.HTTPError as ex:
            err_msg = ex.read().decode("utf-8", errors="ignore")[:240]
            results.append({"url": item["url"], "type": item["type"], "httpStatus": ex.code, "ok": False, "error": err_msg})
            failed += 1
        except Exception as ex:
            results.append({"url": item["url"], "type": item["type"], "httpStatus": 0, "ok": False, "error": str(ex)[:200]})
            failed += 1

    Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    Path(state_path).write_text(
        json.dumps({"updatedAt": dt.datetime.now(get_ist()).isoformat(), "urls": tracked}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    status = "SUBMITTED" if failed == 0 else ("PARTIAL_ERROR" if submitted > 0 else "FAILED")
    return {"status": status, "submitted": submitted, "failed": failed, "results": results}


def submit_bing_indexnow(queue_data):
    key = os.environ.get("BING_INDEXNOW_KEY", "").strip()
    if not key:
        return {"status": "AWAITING_AUTHORIZATION", "submitted": 0}
    urls = [item["url"] for item in queue_data["batch"] if item["type"] == "URL_UPDATED"]
    if not urls:
        return {"status": "UP_TO_DATE", "submitted": 0}
    host = urllib.parse.urlparse(BASE).netloc
    payload = json.dumps(
        {
            "host": host,
            "key": key,
            "keyLocation": f"{BASE}{key}.txt",
            "urlList": urls[:500],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return {"status": "SUBMITTED", "httpStatus": resp.status, "submitted": len(urls[:500])}
    except Exception as ex:
        return {"status": "FAILED", "error": str(ex)[:200], "submitted": 0}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--submit", action="store_true", help="Submit eligible URLs when secrets are configured")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = ap.parse_args()

    q = build_indexing_queue()
    if args.submit:
        google_res = submit_google_indexing(q)
        bing_res = submit_bing_indexnow(q)
    else:
        has_secret = bool(os.environ.get("GOOGLE_INDEXING_SA_JSON", "").strip())
        google_res = {
            "status": "READY_DRY_RUN" if has_secret else "AWAITING_AUTHORIZATION",
            "submitted": 0,
            "failed": 0,
            "results": [],
        }
        bing_res = {"status": "DRY_RUN", "submitted": 0}

    report = {
        "generatedAt": q["generatedAt"],
        "eligibleJobPostingCount": q["eligibleJobPostingCount"],
        "updatedQueued": q["updatedQueued"],
        "deletedQueued": q["deletedQueued"],
        "batchCount": len(q["batch"]),
        "sampleBatch": [{"url": x["url"], "type": x["type"]} for x in q["batch"][:10]],
        "googleIndexingApi": google_res,
        "bingIndexNow": bing_res,
    }
    out_p = Path(args.output)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Indexing Queue: eligible={q['eligibleJobPostingCount']} update={q['updatedQueued']} "
        f"delete={q['deletedQueued']} | Google={google_res['status']} ({google_res['submitted']} sent) | Bing={bing_res['status']}"
    )
