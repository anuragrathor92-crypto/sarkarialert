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


if __name__ == "__main__":
    unittest.main()
