# Sarkari Alert — Task Status & Link Audit Tracker

Last Updated: `2026-11-26 13:41 IST`
Corrective Branch: `fix/broken-links-and-audit-2026-11-26` (Base: `main` at `c75b852`; Backup branch: `backup/main-2026-11-26`)

## Summary Metrics (Post-Fix Audit)
- **Total Active Verified Posts:** `96` (`0` expired posts in active listings) + **`32` Government Schemes (`Sarkari Yojana`)** (`0` Apply buttons on schemes) = **`128` Detail Pages (`148` total generated files)**
- **Internal Link Audit (`verify_links.py --check-internal`):** `147` HTML pages checked, **`3,397` internal links checked, `broken = 0`**
- **External Official URL Audit:** **`180`** unique external URLs checked (`154/180` direct Python `urllib` 2xx/3xx; **`hard404orBadPDF = 0`**; remaining portals verified via curl/SChannel GET `200`, except 3 explicitly marked `Verification Pending`)
- **Automated Tests (`test_import.py`):** `Ran 9 tests in 0.780s — OK` (now includes disk HTML/`sitemap.xml` broken-link enforcement & `Verification Pending` assertion)

## Broken / Generic / Mismatched Links Fixed
1. `ayushman-70plus`: Fixed `422` soft-404 PDF `https://nha.gov.in/img/resources/English_FAQs_related_to_the_benefits_for_senior_citizens.pdf` -> `https://nha.gov.in/` (`200 OK`)
2. `iaf-afcat-01-2027`: Fixed `422` HTML-disguised-as-PDF `Notification for AFCAT 01 of 2027.pdf` -> `https://afcat.edcil.co.in/AFCAT/` (`200 OK`)
3. `nsap`: Fixed dead DNS `nsap.nic.in` -> `https://nsap.dord.gov.in/` (`200 OK`)
4. `stand-up-india`: Fixed timed-out `standupmitra.in` -> `https://financialservices.gov.in/stand-india-scheme-supi` (`200 OK`)
5. `loans-and-cards` (`data/referrals.json`): Fixed `403 Access Denied` `npci.org.in/...` -> `https://www.rbi.org.in/` (`200 OK`)
6. `uppsc-ro-aro-2026`: Fixed TLS-failing `otr.pariksha.nic.in` -> `https://uppsc.up.nic.in/` (`200 OK`)
7. `sidbi-grade-a-b-2026`: Updated generic `/index` -> exact 2026–27 SIDBI recruitment detail URL (`200 OK`)
8. `bihar-vidhan-sabha-jsa-attendant-2026`: Updated generic portal -> direct application portal `https://blasrecruit.in/` (`200 OK`)
9. `ukpsc-lower-pcs-2026`: Updated -> direct application portal `https://ukpsc.net.in/` (`200 OK`)
10. `mp-nhm-staff-nurse-2026`: Updated -> direct application form portal `https://iforms.mponline.gov.in/` (`200 OK`)
11. `aiims-gorakhpur-faculty-2026`: Updated -> direct Faculty Group-A advertisement page (`200 OK`)
12. `aiims-bilaspur-faculty-2026`: Updated -> direct `/recruitment` page (`200 OK`)
13. `coconut-development-board-2026`: Updated -> direct `/Vacancy.aspx` page (`200 OK`)
14. Portal-homepage apply links (`bbmb`, `ecil`, `nlc-india-get-10-2026`, `bel`, `isro-sdsc-shar`, `uksssc`, `haryana-htet`, `dsssb`, `rrb-isolated`, `ssc-steno`): Labeled accurately with portal-specific `applyLabel` (`Official NAPS Portal`, `Official NATS Portal`, `Official UMANG Portal`, etc.)

## Remaining Verification Pending / Blocked Portals (Honest Labeling)
- `assam-rifles-technical-tradesman-2026` (`assamrifles.gov.in`): Marked **`Verification Pending`** (automated checks timed out `rc=28`)
- `bhel-engineer-supervisor-trainee-2026` (`careers.bhel.in`): Marked **`Verification Pending`** (ISP local DNS `rc=6`; resolves to `3.7.210.81` HTTP `200` on `8.8.8.8`)
- `rrc-nr-apprentice-2026` (`www.rrcnr.org`): Marked **`Verification Pending`** (Cloudflare/WAF HTTP `403` blocks automated verification)
- `mp-police-constable-2026-exam-admit` (`esb.mp.gov.in`): Marked with `linkHealth` warning (server uses Legacy TLS Renegotiation, works on SChannel Windows TLS `200 OK`)

## Missing Verified Data Added
- `nlc-india-executive-11-2026`: NLC India Executive Recruitment 2026 (Advt. 11/2026) — `145` Posts (Grades E-1 to E-7, Apply `20 Nov – 19 Dec 2026`)

## Permanent GitHub Actions Broken-Link Checker
- Added `check_internal_links()` + PDF-HTML fallback check (`status 422`) to `scripts/bulk_import/verify_links.py`, enforced inside `test_import.py`, and gated on `schedule`, `push`, `pull_request`, and `workflow_dispatch` in `.github/workflows/bulk-import.yml`.
