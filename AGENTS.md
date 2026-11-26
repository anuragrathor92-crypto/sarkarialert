# Sarkari Alert — permanent agent instructions

## Owner objective and priorities
Operate the existing independent government-information website on GitHub Pages, without requiring the owner to relay prompts, run local commands or leave a laptop on. Do not rebuild or delete the existing site. Use free services and existing plan allowances; never enable billing or purchase anything without explicit permission.

1. First finish and test the 24x7 cloud data pipeline and resolve existing PRs (especially SEO/GA4 PR #5). Smart Search PR #6 was merged; preserve its search page and public JSON feed. Inspect current main and open PRs before changing anything; avoid concurrent conflicting edits.
2. Then finish technical SEO, analytics, Google/Bing integration and live checks.
3. Then develop free browser-based tools and other enhancements. Monetization is last.

## Content and publishing
- Cover jobs, admissions, upcoming jobs, results, admit cards, answer keys, exam dates, scholarships, schemes, notifications and document guides. Cover central government, all 28 states and 8 UTs, including UP RTE 25% 2027-28 monitoring. Official scheme website links only, no separate scheme apply buttons.
- Discover new items from authorized public sources; obey robots, terms, rate limits and TLS. Use original Hindi/English text; independently validate against issuing authority's notices. Never treat a third-party article, successful HTTP response, or guessed values as official fact verification.
- Verify notice identity, vacancy count, eligibility, dates, fee, source PDF and application URL. Distinguish actual direct forms, general portals and offline applications. Never fabricate missing facts or dates. Uncertain, unavailable, contradictory or unverified items must stay pending, not be automatically approved. Recheck restricted portals without bypassing access controls.
- Deduplicate by stable notice ID, issuing authority and source. Remove expired jobs from active views/feed; correctly label archived notices and remove expired JobPosting markup. Preserve useful historical result and admit-card pages where appropriate.
- Use scheduled GitHub Actions, preferably existing 2-hour schedule. Make jobs idempotent and bounded; avoid redundant deployment when nothing material changed. Fail closed on data validation errors; source failures must be visible in logs and must not erase valid records. Retain reports and rollback capability.
- Prove the full pipeline with at least one genuinely new official notice if available. If none is verifiable, report no verified new item, not success at autonomous publication. Separate synthetic tests from real publication.

## Development and acceptance
- Work on branches and PRs; preserve user data and existing layout. Do not force-push main, delete backups, disable checks, or overwrite concurrent changes. Verify exact head SHA and test results before merging; follow owner approval and branch rules. Never solicit routine manual commands; request owner action only for unavailable permissions or genuinely necessary decisions.
- Run Python unit tests (`python -m unittest discover -s scripts/bulk_import -p 'test_*.py'`), build (`python scripts/bulk_import/build_site.py`), internal link checker, applicable JS tests, and new feature regression tests. Inspect actual workflows and adapt commands to current repository. Fix failures before deployment.
- Verify the actual deployed site, category links, representative post pages, search, and public JSON feed at `https://anuragrathor92-crypto.github.io/sarkarialert/`. Check HTTP response and expected content; a merged PR is not proof of live deployment. No unsupported success claims. Keep TASK_STATUS.md current with exact evidence and remaining blockers.
- Ensure mobile usability, accessible interfaces, original content, unique titles/meta, canonical links, accurate sitemap lastmod, valid eligible JobPosting schema, and reliable internal links. Google Indexing API only for eligible page types and with owner-authorized credentials; Bing IndexNow after valid key setup. Do not guarantee indexing, ranking, traffic or approval.
- GA4 measurement ID G-K7T49V1PWN; preserve privacy/consent controls, avoid PII, verify deployed tracking independently where possible. Owner must authorize account connections if required. Do not put tokens or private data in public repo or artifacts.
- Smart Search should support Hindi/English, qualification/category filters and expired record handling. JSON API is static, public, read-only and generated each build, not a server-side service. Never imply keyword matching proves eligibility.
- Future free tools: photo/passport/signature resizing/compression, PDF compression/merge, age calculator, eligibility checker, typing/mock tests, job comparison, deadline reminders and WhatsApp alerts using authorized channels. Keep personal uploads client-side where practical. No spam or unauthorized messaging.
- Keep referrals separate from government jobs; real affiliate links only from owner; clear disclosures. AdSense only with owner authorization and applicable eligibility/policies; no fake clicks, traffic or misleading apply buttons.

## Reporting and execution
Give short Hindi reports with completed changes, commit/PR links, exact tests, real live verification, unresolved blockers and only necessary owner actions. Do not ask the owner to paste repeated prompts or execute routine terminal commands. A coding task ends when the agent session ends; continuous work belongs to explicitly configured scheduled jobs, not promises of background activity.
