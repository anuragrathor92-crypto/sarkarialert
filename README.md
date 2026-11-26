# Sarkari Alert

Independent static portal for verified Indian government jobs, results, admit cards, answer keys, admissions, scholarships, exam dates, upcoming jobs, and **67 Sarkari Yojana** guides (Central + all 28 States and 8 Union Territories).

- **Live Website:** https://anuragrathor92-crypto.github.io/sarkarialert/
- **Categories (13):** Latest Jobs, Results, Admit Cards, Answer Key, Admission (with 2-hour UP RTE 2027–28 monitoring), Sarkari Yojana (67 schemes across Central + 28 States + 8 UTs, zero separate Apply buttons), Scholarship, Exam Dates, Upcoming Jobs, 10th / ITI Jobs, Documents, Syllabus, Outsourcing Jobs.
- **Separate Referral Desk:** `/loans-and-cards/` (non-government commercial loans & credit cards configured via `data/referrals.json`).
- **Google Search Console & AdSense Prep:** Configured via `data/site_config.json` (canonical URLs, JSON-LD schemas, `sitemap.xml`, `robots.txt`).
- **Cloud Automation:** GitHub Actions runs every 2 hours (`.github/workflows/bulk-import.yml`) using built-in `GITHUB_TOKEN` (`discover` → `publish` → `deploy` via `actions/deploy-pages@v4`) to test, discover updates, monitor `rte25.upsdc.gov.in`, recheck pending links, remove expired vacancies, and deploy automatically without requiring a local laptop.
