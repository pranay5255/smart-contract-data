# Scraper Questions and Manual Tasks

## Questions
- What is the required output schema for scraped items (fields + required vs optional)?
Answer - scaped items must get all text content from js pages especially markdown. This will be different for every different data soucr or url.
- Should scrapers download PDFs/attachments or only store links?
Answer - Scrapers must download pdfs if avaiable to download and then store them neatly in a a separate folder. 
- Do we need to persist raw HTML/JSON responses for traceability?
Answer -  Yes store HTML/JSON so that if we are wrong about the post-procssing then we can use the raw data easily. 
- For JS-heavy sites (Sherlock, CodeHawks, Solodit, Immunefi), should Playwright or Selenium be the default engine?
Use playwright and focus on ease of use and code compaction.
- Are there stricter rate limits/robots.txt constraints we must honor beyond the defaults?
Answer - Not required for now.
- Should items be deduplicated across sources, and if so what keys should drive dedupe (url, title, hash)?
Answer - We will do dedup and other post-procssing of raw data later. Right now the objective is to gather as much data and token. 
- Do you want incremental scraping (only new items), and how should state be stored?
incremental scarping is not required. We will run the scripts and collect a version 1 of the data before introducing code complexity with 
## Manual Tasks
- Verify DOM selectors on each target site and confirm if heuristics need updates.
- Install headless browser dependencies for JS scrapers (e.g., `playwright install` or Selenium driver).
- Provide any auth cookies/API keys if required to access reports.
- Confirm endpoints and pagination rules for each source.
- Validate sample outputs from each scraper against the expected format.

### How to approach each manual task
- Verify DOM selectors and heuristics: Load a few representative pages per source, open devtools, and confirm selectors still locate titles, authors, dates, content, attachments, and tags. Test any heuristic-based fallbacks (e.g., class name patterns) against at least 3–5 pages including edge cases (archived posts, paginated lists, detail views). Record any selector drifts and update scraper constants accordingly.
- Install headless browser deps: For Playwright, run `playwright install --with-deps` in the project venv to fetch browsers and OS packages; for Selenium, ensure the matching driver (e.g., ChromeDriver/GeckoDriver) is installed and on PATH. Validate by running a minimal smoke script that loads a JS-heavy target and confirms content render.
- Provide auth cookies/API keys: Identify sources that need auth (private portals, rate-limited APIs). Obtain cookies/keys with proper scope, store them in env vars or a `.env` excluded from VCS, and wire scrapers to read from env. Add a short note on rotation/expiry and avoid hard-coding secrets.
- Confirm endpoints and pagination: For each source, map list and detail endpoints plus query params controlling page, size, sorting, and filters. Test pagination until termination to detect last-page signals (empty results, `has_next`, HTTP 204). Capture any anti-scraping headers or tokens required per request.
- Validate sample outputs: Run each scraper on a small page set and compare emitted JSON to the expected schema (required vs optional fields, markdown/text completeness, attachment handling). Spot-check against raw HTML/JSON saved alongside outputs to ensure parsing fidelity. Flag missing fields or normalization issues before large-scale runs.
