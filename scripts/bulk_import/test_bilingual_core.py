import unittest
from build_site import application_display, category_label, render_item

class BilingualCoreTests(unittest.TestCase):
    def test_route_labels(self):
        self.assertIn("सरकारी भर्ती पोर्टल", application_display({"applyLinkType":"GENERAL_RECRUITMENT_PORTAL","applyLabel":"Direct Apply"})[0])
        self.assertTrue(application_display({"applyLinkType":"VERIFICATION_PENDING"})[1])
        self.assertTrue(application_display({"applyLinkType":"DIRECT_APPLICATION_FORM","applyStatus":"VERIFICATION_PENDING"})[1])
    def test_category_label(self):
        label = category_label("latest-jobs")
        self.assertIn("Latest Jobs", label)
        self.assertIn('lang="hi"', label)
        self.assertIn("नवीनतम सरकारी नौकरियाँ", label)
    def test_pending_list(self):
        post = {"id":"example","title":"Example","category":"latest-jobs","applyUrl":"https://www.icmr.gov.in/apply","officialUrl":"https://www.icmr.gov.in/","applyLinkType":"VERIFICATION_PENDING"}
        output = render_item(post, "./")
        self.assertIn("pending-btn", output)
        self.assertIn("Verification Pending", output)
        self.assertNotIn("Apply Online", output)

if __name__ == "__main__":
    unittest.main()
