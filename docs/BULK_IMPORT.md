# Bulk import system

Discovery scans nine category URLs on the reference website, checks robots.txt, extracts candidate URLs and at most 20 articles' outgoing official-link candidates per scheduled run. It does not copy article prose or publish discovered claims. Source failures are reported; zero results are not treated as success. GitHub Actions runs every two hours, on importer changes, or manually. Download the review queue artifact from Actions.

Review each notice against the issuing authority and check the actual official application link in a browser; domain allowlisting is not verification of content or availability. The initial domain allowlist is deliberately limited. Extend only after confirming authority ownership. Create original factual summaries and rows, then place approved records in data/import_approved.json. The schema example is in data/import_schema.example.json; never publish the fixture.

Manual publication: Actions > Sarkari Alert Bulk Import > Run workflow > publish_approved. It generates static article pages, adds links to existing homepage/category lists, updates data and sitemap in one commit. Existing posts remain intact. Jobs require an explicit open status, future offset-aware deadline, official HTTPS application link and review attestation. Schemes may not have application links. Duplicate ID, title, notice ID and discovery URL checks are exact matches; reviewers must check semantic duplicates. An optional fine-grained GitHub token restricted to this repo, Contents write only, stored as repository Actions secret PUBLISH_TOKEN, is needed for the workflow to push a commit that triggers branch-source Pages. Without it, discovery runs and reviewed publication can be performed via an authorized local git push or connector. Never paste a token into chat, source files or logs. No token has been configured by this change.

Local dry run: python scripts/bulk_import/publish.py
Local apply: python scripts/bulk_import/publish.py --write
Run tests: python -m unittest discover -s scripts/bulk_import -p 'test_*.py'

Publication does not independently certify link health or official facts; a reviewer must do that. It does not delete historical records or automatically scrape content; existing deadline handling remains. Verify Pages deployment after push.
