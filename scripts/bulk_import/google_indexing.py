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


def _find_openssl() -> str:
    import shutil
    found = shutil.which("openssl")
    if found:
        return found
    for cand in (r"C:\Program Files\Git\usr\bin\openssl.exe", r"C:\Program Files\Git\mingw64\bin\openssl.exe"):
        if Path(cand).exists():
            return cand
    return "openssl"


def _read_asn1_tl(buf: bytes, offset: int):
    tag = buf[offset]
    idx = offset + 1
    first_len = buf[idx]
    idx += 1
    if first_len & 0x80:
        nbytes = first_len & 0x7F
        length = int.from_bytes(buf[idx : idx + nbytes], "big")
        idx += nbytes
    else:
        length = first_len
    return tag, idx, idx + length


def _parse_rsa_pkcs1_or_pkcs8(private_key_pem: str):
    b64_lines = [ln.strip() for ln in private_key_pem.strip().splitlines() if not ln.strip().startswith("-----")]
    der = base64.b64decode("".join(b64_lines))
    _, s, e = _read_asn1_tl(der, 0)
    pos = s
    tag, vs, ve = _read_asn1_tl(der, pos)  # version
    pos = ve
    nxt_tag, ns, ne = _read_asn1_tl(der, pos)
    if nxt_tag == 0x30:
        # PKCS#8: AlgorithmIdentifier SEQUENCE followed by OCTET STRING privateKey
        pos = ne
        _, os_s, os_e = _read_asn1_tl(der, pos)
        der = der[os_s:os_e]
        _, s, e = _read_asn1_tl(der, 0)
        _, _, pos = _read_asn1_tl(der, s)  # skip PKCS#1 version INTEGER
    ints = []
    while pos < e and len(ints) < 3:
        t, is_, ie = _read_asn1_tl(der, pos)
        if t == 0x02:
            ints.append(int.from_bytes(der[is_:ie], "big"))
        pos = ie
    return ints[0], ints[1], ints[2]  # (n, e, d)


def _sign_rs256_pure_python(signing_input: bytes, private_key_pem: str) -> bytes:
    """RFC 8017 EMSA-PKCS1-v1_5 SHA-256 fallback when cryptography/openssl are absent."""
    n, _, d = _parse_rsa_pkcs1_or_pkcs8(private_key_pem)
    k = (n.bit_length() + 7) // 8
    digest_info = (
        b"\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20"
        + hashlib.sha256(signing_input).digest()
    )
    ps_len = k - len(digest_info) - 3
    if ps_len < 8:
        raise ValueError("RSA key modulus too small for SHA-256 signature")
    em = b"\x00\x01" + (b"\xff" * ps_len) + b"\x00" + digest_info
    sig_int = pow(int.from_bytes(em, "big"), d, n)
    return sig_int.to_bytes(k, "big")


def sign_rs256(signing_input: bytes, private_key_pem: str) -> bytes:
    """Sign JWT payload with RS256 using cryptography, openssl CLI, or pure-Python RSA."""
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
                [_find_openssl(), "dgst", "-sha256", "-sign", key_path],
                input=signing_input,
                capture_output=True,
                check=True,
            )
            return res.stdout
        except (OSError, subprocess.CalledProcessError):
            return _sign_rs256_pure_python(signing_input, private_key_pem)
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


def build_indexnow_urls(queue_data, seo_state_path=ROOT / "data/seo_state.json"):
    """Gather all new/updated indexable URLs (jobs, results, admit cards, schemes, homepage) for Bing IndexNow."""
    urls = []
    seen = set()

    def add_u(u):
        if u and u not in seen:
            seen.add(u)
            urls.append(u)

    add_u(BASE)
    for item in queue_data.get("batch", []):
        if item.get("type") == "URL_UPDATED":
            add_u(item.get("url"))

    if Path(seo_state_path).exists():
        try:
            seo_state = json.loads(Path(seo_state_path).read_text(encoding="utf-8")).get("urls") or {}
            if seo_state:
                latest_lm = max((m.get("lastmod", "") for m in seo_state.values()), default="")
                for u, meta in sorted(seo_state.items()):
                    if latest_lm and meta.get("lastmod") == latest_lm:
                        add_u(u)
        except Exception:
            pass
    return urls[:500]


def submit_bing_indexnow(queue_data):
    key = os.environ.get("BING_INDEXNOW_KEY", "").strip()
    urls = build_indexnow_urls(queue_data)
    if not key:
        return {"status": "AWAITING_AUTHORIZATION", "submitted": 0, "queued": len(urls)}
    if not urls:
        return {"status": "UP_TO_DATE", "submitted": 0, "queued": 0}
    host = urllib.parse.urlparse(BASE).netloc
    payload = json.dumps(
        {
            "host": host,
            "key": key,
            "keyLocation": f"{BASE}{key}.txt",
            "urlList": urls,
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
            return {"status": "SUBMITTED", "httpStatus": resp.status, "submitted": len(urls), "queued": len(urls)}
    except Exception as ex:
        return {"status": "FAILED", "error": str(ex)[:200], "submitted": 0, "queued": len(urls)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--submit", action="store_true", help="Submit eligible URLs when secrets are configured")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = ap.parse_args()

    q = build_indexing_queue()
    inow_urls = build_indexnow_urls(q)
    if args.submit:
        google_res = submit_google_indexing(q)
        bing_res = submit_bing_indexnow(q)
    else:
        has_secret = bool(os.environ.get("GOOGLE_INDEXING_SA_JSON", "").strip())
        has_bkey = bool(os.environ.get("BING_INDEXNOW_KEY", "").strip())
        google_res = {
            "status": "READY_DRY_RUN" if has_secret else "AWAITING_AUTHORIZATION",
            "submitted": 0,
            "failed": 0,
            "results": [],
        }
        bing_res = {
            "status": "DRY_RUN" if has_bkey else "AWAITING_AUTHORIZATION",
            "submitted": 0,
            "queued": len(inow_urls),
        }

    report = {
        "generatedAt": q["generatedAt"],
        "eligibleJobPostingCount": q["eligibleJobPostingCount"],
        "updatedQueued": q["updatedQueued"],
        "deletedQueued": q["deletedQueued"],
        "batchCount": len(q["batch"]),
        "sampleBatch": [{"url": x["url"], "type": x["type"]} for x in q["batch"][:10]],
        "indexNowQueued": len(inow_urls),
        "indexNowSample": inow_urls[:10],
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
