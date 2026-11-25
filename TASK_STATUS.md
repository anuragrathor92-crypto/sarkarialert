# SARKARI ALERT - Task Status Tracker

Last Updated: 2026-11-26

## PRIORITY 1: Backup, Latest Vacancies & Verification
- [x] Inspect existing website and create backup branch (`backup/main-2026-11-26`)
- [x] Create development branch (`dev/complete-update-2026-11-26`)
- [x] Collect all latest valid government vacancies (13 new verified active jobs + 9 existing active jobs = 22 active jobs)
- [x] Verify vacancies using official government websites (`upsssc.gov.in`, `upessc.up.gov.in`, `rrbapply.gov.in`, `aees.gov.in`, `nlcindia.in`, `afcat.edcil.co.in`, `asrb.gov.in`, `sbi.bank.in`, `ssc.gov.in`, `bbmb.gov.in`, `sjvn.nic.in`, `upsc.gov.in`, `uppsc.up.nic.in`, `dsssbonline.nic.in`, `rrccr.com`)
- [x] Add direct working Apply Online links and official notifications
- [x] Add eligibility, vacancy details, fees, and important dates
- [x] Exclude expired and duplicate vacancies

## PRIORITY 2: Government Schemes (Sarkari Yojana) from Excel
- [x] Read Excel file `SARKARI_ALERT_GOVT_SCHEMES_OFFICIAL_APPLY_LINKS_2026(1).xlsx` (32 schemes extracted)
- [x] Add all missing government schemes (8 new schemes: PMEGP, PM-Vidyalaxmi, PMFME, Skill India Digital, PMMSY, PM POSHAN, PM SHRI, UP RTE 2027-28)
- [x] Update verified official website links (all 32 schemes verified)
- [x] Add eligibility, benefits, and required documents for all 32 schemes
- [x] Show all 32 schemes inside Sarkari Yojana category (`category/yojana/` + homepage panel)
- [x] Ensure NO separate Apply buttons for government schemes

## PRIORITY 3: Categories, Existing Posts & Monitoring
- [x] Update Results (+3), Admit Cards (+3), Answer Keys (+3), Admissions (+1 UP RTE Monitor), Scholarships (+2), Exam Dates (+2), 10th/ITI (+2), and Upcoming Jobs (+3)
- [x] Monitor UP RTE Admission 2027-28 (`rte25.upsdc.gov.in` — automated 2-hour monitor active)
- [x] Fix broken links and category navigation (removed stale `release=24-schemes-v2` cache-busting hack; verified 0 broken internal links)
- [x] Verify the 6 previously added posts:
  - [x] CMAT 2027 (`nta-cmat-2027`) — Verified 200 OK
  - [x] SHRESHTA NETS 2027 (`nta-shreshta-2027`) — Verified 200 OK
  - [x] IBPS PO/MT XVI Result (`ibps-po-mt-xvi-main-result-2026`) — Verified 200 OK
  - [x] UGC NET December 2026 (`ugc-net-december-2026-exam-date`) — Verified 200 OK
  - [x] CSIR UGC NET December 2026 (`csir-net-december-2026-exam-date`) — Verified 200 OK
  - [x] UPSC Dental Surgeon (`upsc-dental-surgeon-2026`) — Verified 200 OK

## PRIORITY 4: Design, Automation, SEO & Referral Section
- [x] Complete website design inspired by reference (`sarkariresult.com.cm`) — live ticker, 8 highlight cards, filter/search, 12 tiles, 13 category panels, responsive CSS
- [x] Implement automatic data fetching and verification (`scripts/bulk_import/discover.py`)
- [x] Configure GitHub Actions to check for updates every two hours (`.github/workflows/bulk-import.yml` `17 */2 * * *`)
- [x] Implement automatic duplicate and expiry management (`scripts/bulk_import/publish.py`, `build_site.py`, `assets/site.js`)
- [x] Implement admin approval and authorized automatic publishing (`data/import_approved.json` + `PUBLISH_TOKEN`)
- [x] Complete SEO, sitemap, mobile optimization, and website performance (OG tags, Twitter cards, JSON-LD, `sitemap.xml` with `lastmod`, responsive CSS)
- [x] Prepare separate referral section for loans and credit cards (`loans-and-cards/` + `data/referrals.json`)

## DEPLOYMENT
- [x] Work on development branch (`dev/complete-update-2026-11-26`)
- [x] Preserve existing correct data
- [x] Run all tests (9/9 unit & integrity tests passing)
- [ ] Push branches & create pull request for user approval
- [ ] Merge and deploy to GitHub Pages (after user approval)
- [ ] Verify live website content and all new links (after GitHub Pages deployment)
