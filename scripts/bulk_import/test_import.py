import datetime as dt, json, re, unittest
from pathlib import Path
from discover import article_url, official, Anchors, get_ist
from build_site import build_all, ROOT
from publish import validate, build


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
        self.assertEqual(len(schemes), 32)
        files, active, expired = build_all(now=self.now)
        # Ensure all 32 schemes exist and have NO apply buttons
        yojana_cat = files["category/yojana/index.html"]
        self.assertNotIn("apply-btn", yojana_cat)
        for s in schemes:
            self.assertIn(s["id"], yojana_cat)
            post_html = files[f"posts/{s['id']}/index.html"]
            self.assertNotIn("apply-btn", post_html)
            self.assertNotIn("Apply Online", post_html)
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


if __name__ == "__main__":
    unittest.main()
