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
