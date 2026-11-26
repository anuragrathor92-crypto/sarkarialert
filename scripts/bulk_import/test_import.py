import datetime as dt, json, re, unittest
from pathlib import Path
from discover import article_url, official, Anchors, get_ist
from build_site import build_all, ROOT
from publish import validate, build
from verify_links import check_internal_links


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 11, 26, 12, tzinfo=get_ist())
        self.p = {
            "id": "test-only-synthetic-2026",
            "title": "Synthetic test fixture only",
            "category": "latest-jobs",
            "department": "Test",
            "noticeId": "TEST-2026",
            "notificationUrl": "https://ssc.gov.in/test",
            "officialUrl": "https://ssc.gov.in/",
            "applyUrl": "https://ssc.gov.in/login",
            "summary": "Synthetic fixture; never publish.",
            "reviewedBy": "Test",
            "reviewedOn": "2026-11-26",
            "approved": True,
            "officialFactsChecked": True,
            "applyLinkChecked": True,
            "applicationStatus": "OPEN",
            "deadline": "2026-12-01T18:00:00+05:30",
            "rows": [["Status", "Fixture"]],
        }

    def test_official(self):
        self.assertTrue(official("https://ssc.gov.in/"))
        self.assertTrue(official("https://aees.onlineregistrationforms.com/#/home"))
        self.assertFalse(official("https://ssc.gov.in.evil.example/"))
        self.assertFalse(official("http://ssc.gov.in/"))

    def test_source(self):
        self.assertIsNotNone(article_url("/upsssc-recruitment-2026/"))
        self.assertIsNone(article_url("/latest-jobs/"))
        self.assertIsNone(article_url("https://example.com/test-2026/"))

    def test_parser(self):
        a = Anchors()
        a.feed('<ul><li><a href="/test-2026/">Example</a></li></ul>')
        self.assertEqual(a.links, [("/test-2026/", True)])

    def test_expired(self):
        with self.assertRaises(ValueError):
            validate(dict(self.p, deadline="2026-11-20T18:00:00+05:30"), self.now)

    def test_unapproved(self):
        with self.assertRaises(ValueError):
            validate(dict(self.p, approved=False), self.now)

    def test_scheme_apply(self):
        with self.assertRaises(ValueError):
            validate(dict(self.p, category="yojana"), self.now)

    def test_batch_dry_run(self):
        files, errors = build([self.p, self.p], self.now)
        self.assertEqual(len(errors), 1)
        self.assertIn("posts/test-only-synthetic-2026/index.html", files)
        self.assertIn("test-only-synthetic-2026", files["index.html"])
        self.assertIn("test-only-synthetic-2026", files["category/latest-jobs/index.html"])
        self.assertIn("category/yojana/", files["index.html"])

    def test_empty(self):
        self.assertEqual(build([], self.now), ({}, []))

    def test_site_integrity(self):
        schemes = json.loads((ROOT / "data/schemes_directory.json").read_text(encoding="utf-8"))["records"]
        self.assertGreaterEqual(len(schemes), 67)
        # Verify coverage of all 28 States + 8 UTs + All India Central
        jurisdictions = {s.get("stateOrUt") for s in schemes if s.get("stateOrUt")}
        self.assertGreaterEqual(len(jurisdictions), 37)
        files, active, expired = build_all(now=self.now)
        self.assertIn("robots.txt", files)
        self.assertTrue((ROOT / "data/site_config.json").exists())
        # Ensure all schemes exist and have NO apply buttons
        yojana_cat = files["category/yojana/index.html"]
        self.assertNotIn("apply-btn", yojana_cat)
        for s in schemes:
            self.assertIn(s["id"], yojana_cat)
            post_html = files[f"posts/{s['id']}/index.html"]
            self.assertNotIn("apply-btn", post_html)
            self.assertNotIn("Apply Online", post_html)
            self.assertIn("GovernmentService", post_html)
            self.assertTrue(s.get("eligibility"))
            self.assertTrue(s.get("benefit"))
            self.assertTrue(s.get("requiredDocuments"))
        # Ensure all 6 previously added posts are present
        for pid in (
            "nta-cmat-2027",
            "nta-shreshta-2027",
            "ibps-po-mt-xvi-main-result-2026",
            "ugc-net-december-2026-exam-date",
            "csir-net-december-2026-exam-date",
            "upsc-dental-surgeon-2026",
        ):
            self.assertIn(f"posts/{pid}/index.html", files)
            self.assertIn(pid, files["sitemap.xml"])
        # Ensure separate referral page exists
        self.assertIn("loans-and-cards/index.html", files)
        self.assertIn("Non-Government", files["loans-and-cards/index.html"].replace("गैर-सरकारी", "Non-Government"))
        # Ensure UP RTE monitor is present
        self.assertIn("up-rte-admission-2027-28-monitor", files["category/admission/index.html"])
        # Ensure zero empty categories (all 13 categories populated with verified entries)
        for cat_slug in (
            "latest-jobs", "results", "admit-card", "answer-key", "admission",
            "yojana", "scholarship", "exam-date", "upcoming-jobs", "10th-iti",
            "documents", "syllabus", "outsourcing",
        ):
            self.assertIn(f"category/{cat_slug}/index.html", files)
            self.assertIn("<li data-post", files[f"category/{cat_slug}/index.html"], f"Empty category: {cat_slug}")
        # Ensure all active jobs have official HTTPS apply/notification/official links
        posts_data = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))["posts"]
        seen_ids = set()
        for post in posts_data:
            self.assertNotIn(post["id"], seen_ids)
            seen_ids.add(post["id"])
            self.assertTrue(official(post["officialUrl"]), f"Unapproved officialUrl: {post['id']} -> {post['officialUrl']}")
            if post["category"] in ("latest-jobs", "10th-iti", "outsourcing"):
                self.assertTrue(official(post["applyUrl"]), f"Unapproved applyUrl: {post['id']} -> {post.get('applyUrl')}")
                self.assertTrue(official(post["notificationUrl"]), f"Unapproved notificationUrl: {post['id']}")
        # Ensure zero broken relative links in generated HTML
        for rel_path, content in files.items():
            if not rel_path.endswith(".html") or rel_path == "404.html":
                continue
            for m in re.finditer(r'href="([^"]+)"', content):
                href = m.group(1)
                if href.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                    continue
                clean = href.split("?")[0].split("#")[0]
                if not clean or clean.endswith("/"):
                    clean = clean + "index.html"
                resolved = (Path(rel_path).parent / clean).as_posix()
                # Normalize '..'
                parts = []
                for part in resolved.split("/"):
                    if part in ("", "."):
                        continue
                    if part == "..":
                        if parts:
                            parts.pop()
                    else:
                        parts.append(part)
                norm = "/".join(parts)
                self.assertTrue(norm in files or (ROOT / norm).exists(), f"Broken link {href} -> {norm} in {rel_path}")
        # Ensure built disk HTML + sitemap have zero broken internal links
        internal = check_internal_links(ROOT)
        self.assertEqual(internal["broken"], [], f"Broken internal links on disk: {internal['broken']}")
        # Ensure unverified portals (4 pending links) are marked Verification Pending rather than Apply Online
        for pid in ("assam-rifles-technical-tradesman-2026", "bhel-engineer-supervisor-trainee-2026", "rrc-nr-apprentice-2026"):
            html_txt = files[f"posts/{pid}/index.html"]
            self.assertIn("Verification Pending", html_txt)
            self.assertIn("pending-btn", html_txt)
        pending_tracked = [p["id"] for p in posts_data if p.get("applyStatus") == "VERIFICATION_PENDING" or p.get("linkStatus") == "VERIFICATION_PENDING"]
        self.assertGreaterEqual(len(pending_tracked), 4)
        self.assertIn("JobPosting", files["posts/upsc-dental-surgeon-2026/index.html"])
        self.assertIn("feed.xml", files)
        self.assertIn("sitemap/index.html", files)

    def test_seo_audit_and_expired_jobposting_removal(self):
        from build_site import render_standard_post, is_jobposting_eligible
        from seo_audit import audit_site

        # Expired vacancy must NOT be JobPosting-eligible and must render noindex without JobPosting
        expired_job = dict(self.p, deadline="2026-11-20T18:00:00+05:30")
        self.assertFalse(is_jobposting_eligible(expired_job, self.now))
        exp_html = render_standard_post(expired_job, now=self.now)
        self.assertIn('content="noindex,follow"', exp_html)
        self.assertNotIn('"@type": "JobPosting"', exp_html)
        self.assertIn("Application Closed", exp_html)

        # Ineligible category (results) must never emit JobPosting
        res_post = dict(self.p, category="results", deadline="")
        self.assertFalse(is_jobposting_eligible(res_post, self.now))
        res_html = render_standard_post(res_post, now=self.now)
        self.assertNotIn('"@type": "JobPosting"', res_html)

        # Disk audit check
        rep = audit_site(now=self.now)
        self.assertTrue(rep["passed"], f"SEO audit errors: {rep['errors']}")
        self.assertEqual(rep["duplicateTitlesCount"], 0)
        self.assertEqual(rep["duplicateDescriptionsCount"], 0)
        self.assertEqual(rep["expiredOrIneligibleJobPostings"], 0)
        self.assertGreaterEqual(rep["eligibleJobPostingPages"], 95)

    def test_indexing_queue_strict_eligibility(self):
        import tempfile
        from google_indexing import build_indexing_queue, BASE

        posts_db = {
            "posts": [
                self.p,
                dict(self.p, id="test-result-not-job", category="results", deadline=""),
            ],
            "archivedExpiredIds": ["test-expired-removed-2026"],
        }
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            pfile = td_p / "posts.json"
            sfile = td_p / "indexing_state.json"
            pfile.write_text(json.dumps(posts_db), encoding="utf-8")
            sfile.write_text(
                json.dumps({
                    "urls": {
                        f"{BASE}posts/test-expired-removed-2026/": {"status": "ACTIVE", "fingerprint": "old"},
                    }
                }),
                encoding="utf-8",
            )
            q = build_indexing_queue(now=self.now, state_path=sfile, posts_path=pfile)
            self.assertEqual(q["eligibleJobPostingCount"], 1)
            self.assertEqual(q["updatedQueued"], 1)
            self.assertEqual(q["deletedQueued"], 1)
            types = {x["url"]: x["type"] for x in q["batch"]}
            self.assertEqual(types[f"{BASE}posts/test-only-synthetic-2026/"], "URL_UPDATED")
            self.assertEqual(types[f"{BASE}posts/test-expired-removed-2026/"], "URL_DELETED")
            self.assertNotIn(f"{BASE}posts/test-result-not-job/", types)

    def test_ga4_integration_and_privacy(self):
        cfg = json.loads((ROOT / "data/site_config.json").read_text(encoding="utf-8"))
        ga_id = cfg["googleAnalytics4"]["measurementId"]
        self.assertEqual(ga_id, "G-K7T49V1PWN")
        files, _, _ = build_all(now=self.now)
        for rel in ("index.html", "category/latest-jobs/index.html", "posts/upsc-dental-surgeon-2026/index.html", "loans-and-cards/index.html", "privacy/index.html"):
            h = files[rel]
            self.assertIn(f"https://www.googletagmanager.com/gtag/js?id={ga_id}", h)
            self.assertIn("window.__saGaInit", h)
            self.assertIn("anonymize_ip", h)
            self.assertIn("consent", h)
            self.assertIn("manage-analytics-consent", h)
        self.assertIn("sa_ga_consent", files["privacy/index.html"] + (ROOT / "assets/site.js").read_text(encoding="utf-8"))
        self.assertIn("G-K7T49V1PWN", files["privacy/index.html"])
        js_txt = (ROOT / "assets/site.js").read_text(encoding="utf-8")
        for ev_name in ("category_visit", "apply_online_click", "notification_download", "referral_click", "outbound_click"):
            self.assertIn(ev_name, js_txt)

    def test_auto_verify_official_pipeline(self):
        import tempfile
        from unittest.mock import patch
        import auto_verify

        disc_payload = {
            "officialDiscoveries": [
                {
                    "title": "Scientist-D (Non-Medical) Test Open Recruitment",
                    "department": "ICMR Test Institute",
                    "noticeId": "ICMR/TEST/SC-D/2026",
                    "lastDateRaw": "2026-12-31",
                    "applyUrl": "https://recruitment.icmr.org.in/",
                    "notificationUrl": "https://www.icmr.gov.in/test_open.pdf",
                    "officialUrl": "https://www.icmr.gov.in/employment-opportunities",
                    "postNature": "Permanent Posts",
                },
                {
                    "title": "ICMR Temporary Project Technician",
                    "department": "ICMR Test Institute",
                    "noticeId": "ICMR/TEST/TEMP/2026",
                    "lastDateRaw": "2026-12-31",
                    "applyUrl": "https://recruitment.icmr.org.in/",
                    "notificationUrl": "https://www.icmr.gov.in/test_temp.pdf",
                    "officialUrl": "https://www.icmr.gov.in/employment-opportunities",
                    "postNature": "Temporary Posts",
                },
                {
                    # Duplicate noticeId of existing published ICMR post
                    "title": "Duplicate Advertisement",
                    "department": "ICMR-Hqrs New Delhi",
                    "noticeId": "ICMR/Rectt/Sc-D/02/2026-RPCell",
                    "lastDateRaw": "2026-12-31",
                    "applyUrl": "https://recruitment.icmr.org.in/",
                    "notificationUrl": "https://www.icmr.gov.in/dup.pdf",
                    "officialUrl": "https://www.icmr.gov.in/employment-opportunities",
                    "postNature": "Permanent Posts",
                },
            ],
            "candidates": [
                {"sourceUrl": "https://sarkariresult.com.cm/unverified-sample/", "sourceSlug": "unverified-sample"}
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            dpath = Path(td) / "disc.json"
            dpath.write_text(json.dumps(disc_payload), encoding="utf-8")
            mock_ok = {"ok": True, "status": 200, "isPdf": True, "finalUrl": "https://www.icmr.gov.in/", "reason": ""}
            with patch.object(auto_verify, "probe_official", return_value=mock_ok):
                res = auto_verify.run_auto_verify(discovery_path=dpath, write_approved=False, now=self.now)
            self.assertEqual(res["autoApprovedCount"], 1)
            self.assertEqual(res["duplicatesSkipped"], 1)
            self.assertEqual(res["pendingReviewCount"], 2)

    def test_jobposting_audit_compliance_and_sitemap_stability(self):
        import tempfile
        from build_site import render_standard_post, update_sitemap_lastmod, BASE

        # Direct application form vs General recruitment portal directApply semantics + verified location + noticeDate
        direct_job = dict(
            self.p,
            id="test-direct-form-2026",
            noticeDate="2026-11-20",
            publishedDate="2026-11-26",
            applyLinkType="DIRECT_APPLICATION_FORM",
            locationLocality="New Delhi",
            locationRegion="Delhi",
            eligibilityHi="स्नातक डिग्री आवश्यक है।",
        )
        portal_job = dict(
            self.p,
            id="test-general-portal-2026",
            applyLinkType="GENERAL_RECRUITMENT_PORTAL",
            locationLocality="Lucknow",
            locationRegion="Uttar Pradesh",
        )
        d_html = render_standard_post(direct_job, now=self.now)
        p_html = render_standard_post(portal_job, now=self.now)

        self.assertIn('"datePosted": "2026-11-20"', d_html)
        self.assertIn('"directApply": true', d_html)
        self.assertIn('"addressLocality": "New Delhi"', d_html)
        self.assertIn('"addressRegion": "Delhi"', d_html)
        self.assertIn('"directApply": false', p_html)
        self.assertIn("Direct Form", d_html)
        self.assertIn("General Portal", p_html)

        # Sitemap lastmod stability across wrapper rebuilds vs semantic change
        urls = [BASE, f"{BASE}posts/test-direct-form-2026/"]
        base_dates = {BASE: "2026-11-26", f"{BASE}posts/test-direct-form-2026/": "2026-11-20"}
        sem = {BASE: "abc123", f"{BASE}posts/test-direct-form-2026/": "postfp1"}
        with tempfile.TemporaryDirectory() as td:
            sp = Path(td) / "seo_state.json"
            out1 = {"index.html": "<html>v1</html>", "posts/test-direct-form-2026/index.html": d_html}
            lm1 = update_sitemap_lastmod(urls, out1, dt.date(2026, 11, 26), base_dates, semantic_hashes=sem, state_path=sp)
            sp.write_text(out1["data/seo_state.json"], encoding="utf-8")
            self.assertEqual(lm1[f"{BASE}posts/test-direct-form-2026/"], "2026-11-20")

            # Rebuild on next day with different wrapper HTML but SAME semantic hash -> lastmod unchanged
            out2 = {"index.html": "<html>v2 wrapper</html>", "posts/test-direct-form-2026/index.html": d_html + "<!-- GA -->"}
            lm2 = update_sitemap_lastmod(urls, out2, dt.date(2026, 11, 27), base_dates, semantic_hashes=sem, state_path=sp)
            self.assertEqual(lm2[f"{BASE}posts/test-direct-form-2026/"], "2026-11-20")

            # Change substantive semantic hash -> lastmod advances to rebuild date
            sem_changed = dict(sem, **{f"{BASE}posts/test-direct-form-2026/": "postfp2"})
            lm3 = update_sitemap_lastmod(urls, out2, dt.date(2026, 11, 27), base_dates, semantic_hashes=sem_changed, state_path=sp)
            self.assertEqual(lm3[f"{BASE}posts/test-direct-form-2026/"], "2026-11-27")

    def test_up_rte_strict_ssl_no_cert_none(self):
        for rel in ("scripts/bulk_import/discover.py", "scripts/bulk_import/auto_verify.py"):
            src = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("CERT_NONE", src)
            self.assertNotIn("verify=False", src)

    def test_google_indexing_rs256_jwt_and_indexnow(self):
        import base64
        import hashlib
        from google_indexing import sign_rs256, build_indexnow_urls, BASE

        # Construct two proven 256-bit primes for fast zero-dependency RSA-512 test keypair (RFC 8017)
        p = (1 << 256) - 189
        q = (1 << 256) - 357
        n = p * q
        e = 65537
        d = pow(e, -1, (p - 1) * (q - 1))

        def der_len(nbytes: int) -> bytes:
            if nbytes < 128:
                return bytes([nbytes])
            lb = nbytes.to_bytes((nbytes.bit_length() + 7) // 8, "big")
            return bytes([0x80 | len(lb)]) + lb

        def der_tlv(tag: int, body: bytes) -> bytes:
            return bytes([tag]) + der_len(len(body)) + body

        def der_uint(v: int) -> bytes:
            b = v.to_bytes((v.bit_length() + 7) // 8 or 1, "big")
            if b[0] & 0x80:
                b = b"\x00" + b
            return der_tlv(0x02, b)

        pkcs1 = der_tlv(0x30, b"".join(der_uint(x) for x in (0, n, e, d, p, q, d % (p - 1), d % (q - 1), pow(q, -1, p))))
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            + base64.encodebytes(pkcs1).decode("ascii")
            + "-----END RSA PRIVATE KEY-----\n"
        )
        payload = b"header.claims.rs256check"
        sig = sign_rs256(payload, pem)
        k = (n.bit_length() + 7) // 8
        self.assertEqual(len(sig), k)
        digest_info = (
            b"\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20"
            + hashlib.sha256(payload).digest()
        )
        expected_em = b"\x00\x01" + (b"\xff" * (k - len(digest_info) - 3)) + b"\x00" + digest_info
        verified_em = pow(int.from_bytes(sig, "big"), e, n).to_bytes(k, "big")
        self.assertEqual(verified_em, expected_em)

        inow = build_indexnow_urls({"batch": [{"url": f"{BASE}posts/upsc-dental-surgeon-2026/", "type": "URL_UPDATED"}]})
        self.assertIn(BASE, inow)
        self.assertGreater(len(inow), 1)


if __name__ == "__main__":
    unittest.main()
