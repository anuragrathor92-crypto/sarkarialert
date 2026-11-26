# Sarkari Alert — Task Status Tracker

Last Updated: `2026-11-26 14:33 IST`
Feature Branch: `feat/all-states-seo-workflows-2026-11-26` (Base: `main` at `592cb9e`; Backup: `backup/main-2026-11-26`)

## Summary Metrics
- **Active Verified Posts (`data/posts.json`):** `114` (`0` expired posts excluded)
  - `latest-jobs`: `40` | `results`: `16` | `admit-card`: `14` | `admission`: `9` (incl. 3 Upcoming + UP RTE Monitor)
  - `upcoming-jobs`: `8` | `documents`: `7` | `scholarship`: `6` | `answer-key`: `5` | `exam-date`: `5` | `syllabus`: `3` | `outsourcing`: `1` (+ `10th-iti` cross-tag)
- **Government Schemes (`data/schemes_directory.json`):** **`67` total verified schemes** covering **27 Central schemes + ALL 28 States + ALL 8 Union Territories (37 jurisdictions)**; **ZERO separate Apply buttons** (`applyUrl` = `0`)
- **Built Files (`build_site.py`):** `202` generated static files (`200` HTML pages + `sitemap.xml` + `robots.txt`)
- **GitHub Pages Automation (`actions/deploy-pages@v4`):** Configured cleanly inside `.github/workflows/bulk-import.yml` using built-in `GITHUB_TOKEN` (no external PAT or paid tools required) so 2-hourly `schedule`, `workflow_dispatch`, and `main` pushes build, link-check, and deploy autonomously even when local laptop is OFF.

## Completed Tasks (1–14)
- [x] **1. SarkariResult.com.cm Active Comparison & Additions:** Compared `452` candidates (`0` source errors), added missing verified Admit Cards (`upsssc-cane-supervisor-2026`, `gims-noida-staff-nurse-2026`), Results (`up-special-tet-2026-result`, `upsssc-forest-guard-result-2026`, `csbc-bihar-special-branch-constable-result-2026`), Scholarships, and Upcoming Jobs/Admissions while preserving all existing data.
- [x] **2. Direct Apply Link Verification:** Every active vacancy's link verified; working direct forms labeled accurately, portal homepages labeled via `applyLabel`, and 4 unverified/restricted portals marked honestly as `Verification Pending`.
- [x] **3 & 4. Cloud Autonomous Discovery, Verification, Approval & Publishing:** `.github/workflows/bulk-import.yml` runs every 2 hours (`cron: '17 */2 * * *'`) using built-in `GITHUB_TOKEN`, stages discovery artifacts, publishes admin-approved `data/import_approved.json` records + expiry cleanup + `verify_links.py --check-internal` directly in the cloud without requiring a local laptop. Tested via real GitHub Actions `workflow_dispatch` (`publish_approved: true`) + PR workflow runs.
- [x] **5. All 28 States + 8 UTs Government Schemes (`67` Schemes):** Expanded `data/schemes_directory.json` cleanly using live-verified official `.gov.in`/state portals across every State and Union Territory with eligibility, benefits, required documents, and zero Apply buttons.
- [x] **6. Upcoming Jobs, Upcoming Admissions, Upcoming Schemes & Scholarships:** Expanded `upcoming-jobs` (`8`), `scholarship` (`6`: NSP, UP Scholarship, AICTE Pragati/Saksham, PM YASASVI, Bihar Post-Matric BC/EBC & SC/ST, PMSS), `admission` (`9` incl. CUET PG/UG/NEET UG 2027 upcoming + UP RTE monitor), and Upcoming Schemes watch inside `Sarkari Yojana`.
- [x] **7. UP RTE Admission 2027-28 Live Monitor:** Active every 2 hours (`https://rte25.upsdc.gov.in/`, `NOTIFICATION_AWAITED`).
- [x] **8. Technical SEO, Structured Data, Sitemap, Canonical URLs & Mobile Optimization:** Added `JobPosting`, `GovernmentService`, `CollectionPage`, `Organization`, `WebSite`, and `BreadcrumbList` JSON-LD schemas, canonical URLs, `robots.txt`, OpenGraph/Twitter tags, dynamic `sitemap.xml`, and responsive CSS.
- [x] **9. Google Search Console & AdSense Integration Prep:** Created `data/site_config.json` and `docs/SEO_ADSENSE_GSC.md` supporting non-intrusive GSC verification `<meta>` and conditional AdSense + `/ads.txt` generation once real owner IDs are entered (zero fake IDs published).
- [x] **10. Loan & Credit Card Referral Section:** Strictly isolated on `/loans-and-cards/` (`data/referrals.json`) using verified bank/regulator info URLs only (zero invented affiliate links).
- [x] **11. Continuous 2-Hourly Pending Link Recheck (4 Links):** All 4 pending portals (`bhel-engineer-supervisor-trainee-2026`, `assam-rifles-technical-tradesman-2026`, `rrc-nr-apprentice-2026`, `mp-police-constable-2026-exam-admit`) remain marked `Verification Pending` and are rechecked every 2 hours (`pendingRechecked = 4`).
- [x] **12. Live Website Check of 6 Previously Monitored Posts:** Verified live `HTTP 200` on `nta-cmat-2027`, `nta-shreshta-2027`, `ibps-po-mt-xvi-main-result-2026`, `ugc-net-december-2026-exam-date`, `csir-net-december-2026-exam-date`, and `upsc-dental-surgeon-2026`.
- [x] **13. Automated Tests & Pull Request:** Full test suite passed (`9/9 OK`), Pull Request #3 opened for approval.
- [x] **14. Status Tracking:** `TASK_STATUS.md` updated with exact completed and remaining items.

## Remaining / Owner-Input Pending Items
- [ ] **Owner Approval to Merge PR #3** (`feat/all-states-seo-workflows-2026-11-26` -> `main`) and deploy updated `199`-file build to GitHub Pages.
- [ ] **Owner-Specific Credentials (Cannot Be Invented):** Add your personal Google Search Console `verificationMetaContent`, Google AdSense `publisherId` (`ca-pub-...`) in `data/site_config.json`, and any commercial affiliate `referralUrl` values in `data/referrals.json`.
- [ ] **4 Govt Portals Unblock Check:** Automatically monitored every 2 hours (`bhel`, `assam-rifles`, `rrcnr`, `mp-esb`) until reliably accessible/TLS-compliant.
