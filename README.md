# Sarkari Alert

Independent static portal for verified Indian government jobs, results, admit cards, answer keys, admissions, scholarships, exam dates, upcoming jobs, and 32 Sarkari Yojana guides.

- **Live Website:** https://anuragrathor92-crypto.github.io/sarkarialert/
- **Categories:** Latest Jobs, Results, Admit Cards, Answer Key, Admission (with 2-hour UP RTE 2027-28 monitoring), Sarkari Yojana (32 schemes, no separate Apply buttons), Scholarship, Exam Dates, Upcoming Jobs, 10th / ITI Jobs, Documents, Syllabus, Outsourcing Jobs.
- **Separate Referral Desk:** `/loans-and-cards/` (non-government commercial loans & credit cards configured via `data/referrals.json`).
- **Automation:** GitHub Actions runs every 2 hours (`.github/workflows/bulk-import.yml`) to run tests, discover updates, monitor `rte25.upsdc.gov.in`, check expired deadlines, and publish reviewed changes when `PUBLISH_TOKEN` is configured.
