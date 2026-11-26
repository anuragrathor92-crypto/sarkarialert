# Google Search Console & Google AdSense Setup Guide (Sarkari Alert)

## 1. Google Search Console (GSC)
The website is technically pre-configured for Search Console indexing:
- **Sitemap:** `https://anuragrathor92-crypto.github.io/sarkarialert/sitemap.xml` (automatically rebuilt on every update)
- **Robots:** `https://anuragrathor92-crypto.github.io/sarkarialert/robots.txt`
- **Canonical URLs & Structured Data:** Every HTML page includes a canonical URL, OpenGraph/Twitter tags, `BreadcrumbList`, and `JobPosting` / `CollectionPage` / `Article` JSON-LD schemas.

### How to Activate Verification:
1. Open Google Search Console and add URL-prefix property: `https://anuragrathor92-crypto.github.io/sarkarialert/`.
2. Choose **HTML tag verification**, copy only the `content="..."` value, and put it in `data/site_config.json` -> `googleSearchConsole.verificationMetaContent`.
3. Rebuild (`python scripts/bulk_import/build_site.py`) and push to `main`. Once deployed, submit `sitemap.xml` inside Search Console.

## 2. Google AdSense Preparation
- **Clean Layout & Policy Compliance:** Informational pages (`About`, `Privacy Policy`, `Disclaimer`), clear official source citations, and non-deceptive button labeling (`Apply Online`, `Verification Pending`, and `No Separate Apply Button` on `Sarkari Yojana`) are in place.
- **Separate Commercial Desk:** Loan and credit card partner referrals remain strictly isolated on `/loans-and-cards/` (`data/referrals.json`).

### How to Enable AdSense Once Approved:
1. Obtain your real publisher ID (`ca-pub-XXXXXXXXXXXXXXXX`) from Google AdSense.
2. Put it in `data/site_config.json` -> `googleAdSense.publisherId` and set `enableAutoAds: true`.
3. Re-run `python scripts/bulk_import/build_site.py` — `build_site.py` will automatically inject the AdSense script tag cleanly and generate `/ads.txt`.
