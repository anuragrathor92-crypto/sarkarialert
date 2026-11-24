import datetime as dt, unittest
from zoneinfo import ZoneInfo
from discover import article_url,official,Anchors
from publish import validate,build

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,24,12,tzinfo=ZoneInfo("Asia/Kolkata"))
        self.p={"id":"test-only-synthetic-2026","title":"Synthetic test fixture only","category":"latest-jobs","department":"Test","noticeId":"TEST-2026","notificationUrl":"https://ssc.gov.in/test","officialUrl":"https://ssc.gov.in/","applyUrl":"https://ssc.gov.in/login","summary":"Synthetic fixture; never publish.","reviewedBy":"Test","reviewedOn":"2026-11-24","approved":True,"officialFactsChecked":True,"applyLinkChecked":True,"applicationStatus":"OPEN","deadline":"2026-12-01T18:00:00+05:30","rows":[["Status","Fixture"]]}
    def test_official(self):
        self.assertTrue(official("https://ssc.gov.in/"))
        self.assertFalse(official("https://ssc.gov.in.evil.example/"))
        self.assertFalse(official("http://ssc.gov.in/"))
    def test_source(self):
        self.assertIsNotNone(article_url("/upsssc-recruitment-2026/"))
        self.assertIsNone(article_url("/latest-jobs/"))
        self.assertIsNone(article_url("https://example.com/test-2026/"))
    def test_parser(self):
        a=Anchors();a.feed('<ul><li><a href="/test-2026/">Example</a></li></ul>')
        self.assertEqual(a.links,[("/test-2026/",True)])
    def test_expired(self):
        with self.assertRaises(ValueError):validate(dict(self.p,deadline="2026-11-20T18:00:00+05:30"),self.now)
    def test_unapproved(self):
        with self.assertRaises(ValueError):validate(dict(self.p,approved=False),self.now)
    def test_scheme_apply(self):
        with self.assertRaises(ValueError):validate(dict(self.p,category="yojana"),self.now)
    def test_batch_dry_run(self):
        files,errors=build([self.p,self.p],self.now)
        self.assertEqual(len(errors),1)
        self.assertIn("posts/test-only-synthetic-2026/index.html",files)
        self.assertIn("test-only-synthetic-2026",files["index.html"])
        self.assertIn("test-only-synthetic-2026",files["category/latest-jobs/index.html"])
        self.assertIn("category/yojana/index.html",files["index.html"])
    def test_empty(self):
        self.assertEqual(build([],self.now),({},[]))
