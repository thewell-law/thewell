# Scrapers

Rules-based scrapers that turn publicly available court data into YAML
for The Well. No LLMs, no AI: pure regex and structural parsing so
every extracted field can be traced back to the matching pattern and
source excerpt.

## Architecture

```
scrapers/
├── common/                    # shared library
│   ├── http.py                # polite httpx client + robots.txt check
│   ├── pdf.py                 # pypdf text extraction + SHA-256 hashing
│   ├── cache.py               # filesystem cache for fetched PDFs
│   ├── extractors.py          # the regex library (one fn per Tier-1 field)
│   ├── audit.py               # JSONL scrape-event log
│   ├── models.py              # Pydantic v2 mirror of data/schema/judge.schema.json
│   └── normalize.py           # name parsing, slugification, whitespace
├── casd/                      # first jurisdiction: S.D. Cal.
│   ├── scrape.py              # orchestrator + HTML parsers
│   ├── cli.py                 # `python -m scrapers.casd` entry point
│   └── .cache/                # per-jurisdiction PDF cache (gitignored)
└── tests/
    ├── test_extractors.py     # every extractor, positive + negative
    ├── test_casd_integration.py  # end-to-end with mocked HTTP
    ├── test_schema_compat.py  # example YAML round-trips through the models
    └── fixtures/
        ├── casd/              # real judges-index HTML, detail HTML, Bashant standing-order text
        └── extractor_samples/ # per-field plain-text fixtures
```

## Running locally

```sh
cd scrapers/
uv sync --extra test                 # install runtime + test deps
uv run pytest                        # run all tests
uv run python -m scrapers.casd --help
uv run python -m scrapers.casd --dry-run   # fetch + parse, don't write
uv run python -m scrapers.casd             # full scrape; writes data/judges/casd/*.yaml
uv run python -m scrapers.casd --judge bashant
uv run python -m scrapers.casd --rebuild-cache
```

The CLI prints a rich table at the end with judge counts and
extractor hit rates per field.

## Adding a new jurisdiction

1.  Copy `scrapers/casd/` to `scrapers/{jurisdiction}/`. Rename the
    module and update constants in `scrape.py`:
    - `JURISDICTION` - the schema enum value (`cacd`, `ca9`, ...)
    - `BASE_URL`, `JUDGES_INDEX`, and per-page parsers
    - `COURT_NAME`, `COURT_TYPE`
2.  Add `data/judges/{jurisdiction}/` and let the scraper create the
    first YAMLs.
3.  The shared extractor registry in `scrapers/common/extractors.py`
    works across jurisdictions - but if the new court uses different
    standing-order phrasings, add patterns there and cover them with
    tests.
4.  Add a job to `.github/workflows/scrape-weekly.yml` mirroring the
    CASD job.

## Cache layout

`scrapers/{jurisdiction}/.cache/`:

- `{sha256}.pdf` - raw fetched PDFs, keyed by content hash.
- `metadata.json` - maps URL -> `{sha256, fetched_at, content_type, size}`.

Entries expire after 7 days (configurable). `--rebuild-cache` clears
the directory and forces a fresh fetch. The cache is gitignored; it
exists so local iteration doesn't hammer the court's website.

## Audit trail

Every scrape event appends a JSON line to
`scrapers/{jurisdiction}/.audit/{YYYY-MM-DD}.jsonl` with:

- timestamp
- judge name + slug
- standing orders fetched
- which extractors fired (by field_key)
- validation errors, if any
- `skip_reason` if the card was not written

The `.audit/` directory is gitignored; it's a local troubleshooting
aid, not a published artifact.

## Testing strategy

- **Unit tests (`test_extractors.py`)**: one test class per field
  group. Positive cases use realistic standing-order language.
  Negative cases guard against regexes that over-match. Fixtures are
  plain text so we assert on semantics, not PDF parsing.
- **Real-world smoke test**: a subset of tests runs the full
  extractor registry against Judge Bashant's actual standing-order
  text (in `tests/fixtures/casd/bashant_standing_order_civil.txt`)
  and asserts the fields we expect come out correctly.
- **Integration test (`test_casd_integration.py`)**: uses
  `pytest-httpx` to serve captured fixture HTML for the judges
  index, chambers-rules page, and proposed-emails page, plus a
  stubbed PDF parser that returns the Bashant text. Covers the
  orchestration end-to-end without hitting the real site.
- **Schema compatibility (`test_schema_compat.py`)**: the reference
  `data/judges/casd/example-judge.yaml` round-trips through
  `jsonschema`. Catches drift between the schema and the example,
  and between the Pydantic Literal types and the schema enums.

## Behavioral rules

- No LLMs. No AI libraries. No telemetry.
- Respect `robots.txt`. `PoliteClient` checks every URL before
  fetching; a disallowed URL raises `RobotsDisallowed`.
- 1-second minimum delay between requests to the same host.
- User-Agent: `The Well Scraper (https://thewell.law; contact@thewell.law)`.
- Ambiguous extractions leave the field null. Null means "contribute
  or extract later" - never a guess.
