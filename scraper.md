# Scraper Questions and Manual Tasks

## Questions
- What is the required output schema for scraped items (fields + required vs optional)?
- Should scrapers download PDFs/attachments or only store links?
- Do we need to persist raw HTML/JSON responses for traceability?
- For JS-heavy sites (Sherlock, CodeHawks, Solodit, Immunefi), should Playwright or Selenium be the default engine?
- Are there stricter rate limits/robots.txt constraints we must honor beyond the defaults?
- Should items be deduplicated across sources, and if so what keys should drive dedupe (url, title, hash)?
- Do you want incremental scraping (only new items), and how should state be stored?

## Manual Tasks
- Verify DOM selectors on each target site and confirm if heuristics need updates.
- Install headless browser dependencies for JS scrapers (e.g., `playwright install` or Selenium driver).
- Provide any auth cookies/API keys if required to access reports.
- Confirm endpoints and pagination rules for each source.
- Validate sample outputs from each scraper against the expected format.
