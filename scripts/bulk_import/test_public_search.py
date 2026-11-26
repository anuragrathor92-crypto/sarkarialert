import datetime as dt
import json
import unittest
import shutil
import subprocess
from pathlib import Path
from build_site import build_all

class PublicSearchTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for JS search tests')
    def test_browser_search_logic(self):
        subprocess.run(['node', str(Path(__file__).with_name('test_smart_search.js'))], check=True)

    def test_generated_feed(self):
        now = dt.datetime.fromisoformat("2026-11-26T12:00:00+05:30")
        files, active, expired = build_all(now=now)
        feed = json.loads(files["data/public-search.json"])
        records = feed["records"]
        self.assertEqual(feed["count"], len(records))
        self.assertEqual(len({r["id"] for r in records}), len(records))
        self.assertTrue(all(r["verified"] for r in records))
        for r in records:
            self.assertIn("posts/" + r["id"] + "/index.html", files)
            if r["category"] == "yojana" or r["verificationPending"]:
                self.assertNotIn("applyUrl", r)
            self.assertNotIn("reviewedBy", r)
        self.assertIn("assets/smart-search.html", files["index.html"])
        self.assertIn("upsc-dental-surgeon-2026", {r["id"] for r in records})
        self.assertIn("pm-kisan", {r["id"] for r in records})
        # Expired post must never leak into public-search.json
        expired_sample = {"id": "expired-test-job", "title": "Expired Sample", "category": "latest-jobs", "verified": True, "deadline": "2026-11-20T23:59:00+05:30"}
        from public_search import public_feed
        self.assertEqual(json.loads(public_feed([], [], "https://anuragrathor92-crypto.github.io/sarkarialert/", now))["count"], 0)
        # Ensure smart-search.html carries GA4 G-K7T49V1PWN & consent controls
        ss_html = (Path(__file__).resolve().parents[2] / "assets/smart-search.html").read_text(encoding="utf-8")
        self.assertIn("G-K7T49V1PWN", ss_html)
        self.assertIn("manage-analytics-consent", ss_html)
        # Verify real query coverage against generated public-search records
        quals_txt = [str(r.get("qualification", "")) for r in records]
        self.assertTrue(any("10" in q for q in quals_txt))
        self.assertTrue(any("12" in q or "10+2" in q or "12वीं" in q for q in quals_txt))
        self.assertTrue(any("ITI" in q.upper() for q in quals_txt))
        self.assertTrue(any("UPSC" in (r.get("department", "") + " " + r.get("title", "")).upper() for r in records))
        self.assertTrue(any(k in (r.get("department", "") + " " + r.get("title", "")).upper() for r in records for k in ("RAILWAY", "RRB", "RRC")))
        self.assertGreaterEqual(sum(1 for r in records if r.get("category") == "yojana"), 67)
