# Bulk Import, Verification & Monitoring System

## Automated Schedule (Every 2 Hours)
GitHub Actions workflow `.github/workflows/bulk-import.yml` runs every two hours (`17 */2 * * *`), on pushes to `main` touching data/scripts, and via manual `workflow_dispatch`:
1. Runs all unit tests and site integrity checks (`scripts/bulk_import/test_import.py`).
2. Scans reference categories (`scripts/bulk_import/discover.py`) respecting `robots.txt` without copying third-party article prose, and extracts official `.gov.in` / `.nic.in` / `.ac.in` / allowlisted links.
3. Monitors **UP RTE 25% School Admission 2027-28** (`https://rte25.upsdc.gov.in/`) and checks for expired deadlines in `data/posts.json`.
4. Uploads `import-output/` artifacts (`discovery.json`, `publish-report.json`) for admin review.

## Admin Approval & Authorized Auto-Publishing
- Place reviewed, official-source-verified records into `data/import_approved.json` (`approved: true`, `officialFactsChecked: true`). See `data/import_schema.example.json`.
- `publish.py` enforces:
  - Approved official HTTPS domains only.
  - Strict duplicate rejection (ID, normalized title, department+noticeId, discovery URL).
  - Strict expiry rejection (`deadline <= now`) and automatic expiry cleanup (`--prune-expired`).
  - Prohibition of separate Apply buttons/links on `yojana` schemes.
- Configure repository Actions secret `PUBLISH_TOKEN` (fine-grained PAT with `Contents: Read and write` for this repo) to authorize the `publish` job to commit and push directly to `main` (triggering GitHub Pages deployment).

## Local Commands
- Rebuild static site: `python scripts/bulk_import/build_site.py`
- Dry-run approved publish: `python scripts/bulk_import/publish.py --prune-expired`
- Apply approved publish: `python scripts/bulk_import/publish.py --write --prune-expired`
- Run all tests: `python -m unittest discover -s scripts/bulk_import -p 'test_*.py'`
