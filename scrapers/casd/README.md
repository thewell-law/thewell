# S.D. Cal. scraper

Scraper for the U.S. District Court for the Southern District of
California (https://www.casd.uscourts.gov).

## Source website

The CASD site is an ASP.NET Web Forms application. Navigation between
the judges index and individual judge detail pages uses
`__VIEWSTATE` + `__doPostBack`, not RESTful URLs - so per-judge
"Judge-Info.aspx" pages are awkward to fetch directly.

Three observations make a direct scrape feasible anyway:

1.  `/Judges.aspx` lists every active judge with anchors like
    `<a class="p_JudgeList" title="Hon. {Full Name}">`. Repeater IDs
    (`FullTopWidth_rptrDistrictJudge...`,
    `FullTopWidth_rptrDMagistrateJudge...`, `rptrVisitingJudge`)
    distinguish roles. The scraper ignores visiting judges - they're
    covered by their home court.
2.  Standing-order PDFs live at a conventional path:
    `https://www.casd.uscourts.gov/judges/{lastname_slug}/docs/*.pdf`.
    Confirmed from Battaglia's detail page (`battaglia/docs/...`) and
    Bashant's direct standing-order link.
3.  `/judges/chambers-rules.aspx` and `/judges/proposed-emails.aspx`
    are rendered server-side without postback gymnastics, and list
    per-judge PDFs + proposed-orders emails respectively. These are
    the scraper's primary inputs.

### robots.txt

The court's robots.txt disallows `/Judges/` (capital J, as a
directory) for `User-agent: *`. The index page `/Judges.aspx` is a
file, not under a disallowed directory, and per-judge PDFs live under
`/judges/` (lowercase) which is not in the Disallow list. The
`PoliteClient` uses `urllib.robotparser` to check every URL before
fetching.

## Known extraction limitations

- **MSJ page limits**: several judges (e.g., Bashant) don't state an
  MSJ page limit in their standing order - they defer to Civil Local
  Rule 7.1. The scraper leaves these fields null; the limit is then
  contributed separately if needed.
- **Courtroom technology**: extracted only when the standing order or
  chambers-rules page enumerates specific equipment. Most judges don't
  publish this, so `courtroom_tech_available` is typically null.
- **Tier 2 fields** (`motion_ruling_cadence_median_days`,
  `rules_from_bench_pct`): not extracted by this scraper; they
  require PACER data (Stage 6+).
- **Bio fields** (appointed year, prior practice, etc.): live in the
  Biography panel on the postback-protected detail page. The current
  scraper does not traverse those pages; bio enrichment is a future
  addition.

## Debugging an extraction

1.  Run the scraper in `--dry-run --verbose` to see every fetch and
    every extractor firing:
    ```sh
    cd scrapers/
    uv run python -m scrapers.casd --dry-run -v
    ```
2.  Inspect the per-day audit log at
    `scrapers/casd/.audit/{YYYY-MM-DD}.jsonl`. Each line records which
    fields fired for each judge and any validation errors.
3.  To iterate on a single judge, pass `--judge <slug>`:
    ```sh
    uv run python -m scrapers.casd --dry-run -v --judge bashant
    ```
4.  If an extractor isn't firing on a judge's standing order, drop
    the text into `scrapers/tests/fixtures/extractor_samples/` and
    add a unit test in `test_extractors.py`. The regex library is
    append-only - new patterns shouldn't break existing matches.
5.  The cache at `.cache/` can be stale. Pass `--rebuild-cache` to
    refetch.
