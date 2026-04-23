# Methodology

This document describes how data enters The Well and how it gets
published.

## Data pipeline

```
Court website         Scraper              Review gate       Static site
┌────────────┐   PDF+ ┌──────────┐  YAML   ┌──────────┐      ┌──────────┐
│ casd.usc.. │ ──────▶│ regex    │ ──────▶ │ linter + │ ───▶ │ Astro    │
│  (or other)│  HTML  │ extract  │         │ schema + │      │ build    │
└────────────┘        └──────────┘         │ PR review│      └──────────┘
                                           └──────────┘
```

1.  **Scrapers** (in `scrapers/`) fetch the judge index, standing
    orders, and chambers-rules pages from court websites. They run
    rules-based extractors (regex + structural HTML parsing) against
    the text of each standing order.
2.  **YAML** files are written to `data/judges/{jurisdiction}/`.
    Every procedural field is accompanied by a `source` entry with
    the originating URL and a short excerpt of the matched text.
3.  **Validation** is the gate. `scripts/lint-judge-yaml.py` enforces
    the JSON Schema at `data/schema/judge.schema.json` and cross-checks
    it against `data/schema/fields.yaml`. CI fails on any schema error.
4.  **Review**: the weekly scraper workflow commits directly to
    `main` (see `docs/governance.md` for the bypass rationale).
    Maintainers watch the commit diff and roll back anomalies. Any
    scraper regression surfaces as a Git commit, not a silent
    publication.
5.  **Publication**: Astro rebuilds the static site from the updated
    YAML and ships to Cloudflare.

## Extractor transparency

Every procedural field extracted automatically carries three pieces
of context that let anyone reproduce the result:

- `confidence`: one of `auto_extracted`, `verified`,
  `community_aggregated`.
- `source_url`: the standing order, local rule, or court web page
  that contains the fact.
- `source_excerpt`: a short span of the matched text (capped at 200
  characters) so a reader can verify the extraction without opening
  the PDF.

We use regex, not LLMs. This is a deliberate hard rule (see
[`CONTRIBUTING.md`](../CONTRIBUTING.md#hard-rule-no-ailllm-in-the-extraction-path)):
it keeps the extraction deterministic, auditable, and free of
hallucinated citations. When a regex is ambiguous or a standing
order doesn't discuss a field, the scraper leaves the field null
rather than guess. Null means "not yet extracted" - not "zero" or
"none".

## Data tiers

From `data/schema/fields.yaml`:

- **Tier 1** - objective facts extractable from standing orders or
  court websites by the scraper. Example: `msj_page_limit`,
  `courtesy_copies_required`, `proposed_order_email`.
- **Tier 2** - derivable from PACER or other public court data by
  computation. Example: `motion_ruling_cadence_median_days`,
  `rules_from_bench_pct`. Not yet populated; will land in Stage 6+.
- **Tier 3** - community-contributed observations from verified
  attorneys. Example: `page_limit_strictness`, `bench_engagement`,
  `oral_argument_time_typical`. Not yet accepting submissions; see
  the contribution-flow plan for Stage 5.

## Conflicting sources

A single field can appear in the `sources` array more than once if
the scraper finds it in both a standing order and a court website
page, or if a community observation contradicts an extracted fact.
When that happens:

- The `procedural.{field}` value always reflects the
  highest-confidence source (`verified` > `auto_extracted` >
  `community_aggregated`).
- The `sources` array preserves every observation so readers can see
  the disagreement.
- Maintainers may override the value by bumping a source's
  `confidence` to `verified` and referencing it with
  `source_type: editor_verified`.

## Source tracking requirements

The linter (`scripts/lint-judge-yaml.py --strict`) warns when:

- a procedural field is set but has no entry in `sources[]`
- a standing order is listed but no source references it

These are warnings by default and failures under `--strict`. The CI
data-lint job runs in strict mode; no card is accepted that doesn't
cite its sources.

## Community contribution flow

Not yet operational. The full design:

1.  Reader clicks "contribute an observation" on a judge page.
2.  They sign in via Clerk and pick a field from the Tier-3 list.
3.  Their observation is stored in the public-side D1 database,
    disconnected from their identity (see `docs/anonymity.md`).
4.  Moderators review, reconcile multiple observations, and merge
    accepted ones into the YAML via a generated PR.
5.  Merged observations appear on the judge page with
    `source_type: community_aggregated` and
    `confidence: community_aggregated`.

Maintainer-verified observations may be re-tagged as
`source_type: editor_verified`, `confidence: verified`. Those outrank
all other sources on the same field.

## Dispute resolution

If a scraped value is wrong - typically because a standing order
changed, or an edge case confused a regex - the path to correction is:

1.  File a **data correction** issue at
    https://github.com/thewell-law/thewell/issues/new/choose with
    the judge slug, the field, the extracted value, and the correct
    value + citation.
2.  A maintainer either edits the YAML directly (citing the
    correction issue) or adjusts the extractor and re-runs the
    scraper.
3.  If the issue is an extractor bug (wrong regex, broken parser),
    file an **extractor bug** issue instead. That attracts test
    cases and regression coverage.
4.  Standing-order links break sometimes. If a court website moves a
    PDF, the weekly scraper will notice the 404, skip the judge
    card, and log the broken link to the audit trail. A maintainer
    then patches the extractor's link discovery.

All disputes are resolved publicly. There is no private appeals
channel. See `docs/governance.md`.
