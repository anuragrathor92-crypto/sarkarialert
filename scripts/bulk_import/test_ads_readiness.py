import unittest
from build_site import render_shell

class AdReadinessTests(unittest.TestCase):
    def test_approval_missing_blocks_ad_code(self):
        cfg = {"googleAdSense":{"publisherId":"ca-pub-1234567890123456","enableAutoAds":True}}
        html = render_shell("./","Test","Test","", "<main>Test</main>", site_cfg=cfg, page_type="post",post_id="example")
        self.assertNotIn("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",html)
    def test_non_reviewed_page_blocks_ads(self):
        cfg = {"googleAdSense":{"publisherId":"ca-pub-1234567890123456","enableAutoAds":True,"siteApprovalConfirmed":True,"commercialHostingConfirmed":True,"consentSetupConfirmed":True,"reviewedAdEligiblePostIds":["other"]}}
        html = render_shell("./","Test","Test","", "<main>Test</main>", site_cfg=cfg, page_type="post",post_id="example")
        self.assertNotIn("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",html)

if __name__ == "__main__":
    unittest.main()
