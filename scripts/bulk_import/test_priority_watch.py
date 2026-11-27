import datetime as dt
import unittest
from priority_watch import targets, due, watch

A = "https://www.icmr.gov.in/a.pdf"
B = "https://www.icmr.gov.in/apply"
NOW = dt.datetime(2026, 11, 26, tzinfo=dt.timezone.utc)
POSTS = [{"id":"one","category":"results","notificationUrl":A},
         {"id":"two","category":"latest-jobs","notificationUrl":A,"applyUrl":B,
          "applyLinkType":"GENERAL_RECRUITMENT_PORTAL"}]

class PriorityWatchTests(unittest.TestCase):
    def test_dedup_and_post_mapping(self):
        t = targets(POSTS)
        self.assertEqual(len(t),2)
        self.assertEqual(t[A]["interval"],15)
        self.assertEqual(len(t[A]["posts"]),2)
    def test_due_again(self):
        state = {A:{"checkedAt":NOW.isoformat()}, B:{"checkedAt":NOW.isoformat()}}
        self.assertEqual(due(targets(POSTS),state,NOW)[0],[])
        self.assertEqual(due(targets(POSTS),state,NOW+dt.timedelta(minutes=15))[0],[A])
    def test_read_only_signals(self):
        state, report = watch(POSTS, {}, NOW, lambda url, prev:{"status":"BASELINE","hash":"a"})
        self.assertEqual(report["checked"],2)
        self.assertEqual(report["publishedPosts"],0)
        state, report = watch(POSTS,state,NOW+dt.timedelta(minutes=31),
                              lambda url, prev:{"status":"POSSIBLE_SOURCE_CHANGE","hash":"b"})
        self.assertEqual(report["counts"]["POSSIBLE_SOURCE_CHANGE"],2)
        self.assertEqual(report["publishedPosts"],0)
    def test_failure_keeps_prior_hash(self):
        state, report = watch(POSTS,{A:{"hash":"old"}},NOW,
                              lambda url, prev:{"status":"CONNECTION_RECHECK"})
        self.assertEqual(state[A]["hash"],"old")
    def test_unknown_domain(self):
        self.assertFalse(targets([{"id":"x","notificationUrl":"https://example.com/x"}]))

if __name__ == "__main__":
    unittest.main()
