import json
import unittest
from ai_notice_drafts import run, providers, validate, FIELDS

SOURCE = "Official advertisement: Total vacancies 12. Applications close 30 December 2026."
URL = "https://www.icmr.gov.in/notice.pdf"
DISC = {"officialDiscoveries": [{"notificationUrl": URL}]}

def draft():
    return json.dumps({"title_en": "Recruitment", "title_hi": "भर्ती",
                       "summary_en": "12 vacancies", "summary_hi": "12 पद",
                       "facts": {**dict.fromkeys(FIELDS), "vacancies":
                                 {"value": "12", "quote": "Total vacancies 12."}}})

class FreeDraftTests(unittest.TestCase):
    def test_local_no_key(self):
        result = run(DISC, {}, {}, lambda _: SOURCE, lambda *a: self.fail("unexpected API"))
        self.assertEqual(result["status"], "LOCAL_EVIDENCE_ONLY")
    def test_gemini_billing_gate(self):
        self.assertEqual(providers({"GEMINI_API_KEY": "fake"}), [])
        self.assertEqual(len(providers({"GEMINI_API_KEY": "a", "GEMINI_API_KEY_2": "b",
                                        "GEMINI_FREE_TIER_CONFIRMED": "true"})), 1)
    def test_fallback_review_only(self):
        def generate(provider, key, source):
            if provider == "gemini":
                raise ValueError("fake failure")
            return draft()
        result = run(DISC, {}, {"GEMINI_API_KEY": "fake",
                                "GEMINI_FREE_TIER_CONFIRMED": "true",
                                "OPENROUTER_API_KEY": "fake2"}, lambda _: SOURCE, generate)
        self.assertEqual(result["status"], "DRAFT_READY_FOR_REVIEW")
        self.assertFalse(result["drafts"][0]["approved"])
        self.assertFalse(result["drafts"][0]["verified"])
        self.assertEqual(result["drafts"][0]["provider"], "openrouter_free")
        self.assertNotIn("fake", json.dumps(result))
    def test_invalid_quote(self):
        with self.assertRaises(ValueError):
            validate(draft().replace("Total vacancies 12.", "Total vacancies 99."), SOURCE)
    def test_no_repeat_existing(self):
        result = run(DISC, {"posts": [{"notificationUrl": URL}]}, {},
                     lambda _: self.fail("unexpected download"))
        self.assertEqual(result["status"], "NO_NEW_OFFICIAL_PDF")
    def test_unapproved_domain(self):
        result = run({"officialDiscoveries": [{"notificationUrl": "https://example.com/a.pdf"}]},
                     {}, {}, lambda _: self.fail("unexpected download"))
        self.assertEqual(result["status"], "NO_NEW_OFFICIAL_PDF")

if __name__ == "__main__":
    unittest.main()
