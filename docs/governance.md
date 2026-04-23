# Governance

This document describes who can change what in The Well, how
decisions get made, and what the operational policies are.

## Who can push to `main`

Two actors are allowed to push to the `main` branch of
`thewell-law/thewell`:

1.  **Project maintainers**, via reviewed pull requests. The default
    flow is: branch -> PR -> review -> merge. Branch-protection
    rules on `main` require a passing CI run and one maintainer
    approval before merge.
2.  **`github-actions[bot]`**, direct push, *only* via the
    scrape-weekly workflow (`.github/workflows/scrape-weekly.yml`).
    This is the only automation allowed to bypass the PR flow.

The weekly-scrape bypass exists because the scraper's output is a
mechanical transformation of public court data, not human authorship:
rules-based extraction, fully reproducible, committed with a
diff-reviewable message. Requiring a PR for every weekly update would
add review overhead without adding safety - a bad commit is just as
revertable either way, and the per-commit audit trail stays intact.

The bypass is narrow: it applies to
`github-actions[bot]` *only*, *only* for pushes from the
scrape-weekly workflow, *only* to `data/judges/**`. Any attempt to
push code changes, workflow changes, or schema changes from that
workflow will fail the lint + test jobs on CI (which run on every
commit to `main`).

### Configuring the bypass

On GitHub: Settings -> Branches -> `main` -> Branch protection rule
-> "Allow specified actors to bypass required pull requests" -> add
`github-actions[bot]`. Leave all other protections (required checks,
required review for human contributors) in place.

The weekly workflow also needs `permissions: contents: write` in its
job definition so the Actions token can push; this is already set in
`.github/workflows/scrape-weekly.yml`.

## Cadence

- **Code changes**: any time, by PR.
- **Schema or taxonomy changes**: by PR, requires a maintainer
  review. See the "Adding or changing a field" section below.
- **Data refreshes**: weekly, Sundays 03:00 UTC, via the
  scrape-weekly workflow. Dispatched manually from the Actions tab
  when a maintainer needs an immediate refresh.

## What happens if the weekly scrape breaks

1.  The workflow run fails on the Actions dashboard. GitHub's default
    email on failed Actions will hit the maintainers.
2.  The scraper does **not** commit partial results. Either every
    reachable judge validates against the schema and the commit goes
    through, or no commit is made. A single broken standing order
    doesn't block the whole run - that judge is skipped and logged
    in the audit trail, but other judges still update.
3.  The most common failure modes, in order of likelihood:
    - Court website moved a PDF (link rot). Fix: update the
      chambers-rules parser or add a redirect fallback.
    - ASP.NET VIEWSTATE rotated and an inner page stopped parsing.
      The scraper avoids VIEWSTATE by design, but if the
      chambers-rules or proposed-emails pages ever move behind
      postbacks, the scraper will need an adjustment. Fix: extend
      the scraper.
    - robots.txt tightened and the scraper is now denied. Fix:
      contact the court's clerk office.
    - The court's HTML restructured. Fix: update the selectors in
      `scrapers/casd/scrape.py` and the fixtures in
      `scrapers/tests/fixtures/casd/`.
4.  A maintainer patches the scraper, tests land in
    `scrapers/tests/`, and the next scheduled run picks up the fix.
    Emergency manual runs are dispatched from the Actions tab.

## Requesting a field addition or taxonomy change

Fields and enum values are source-of-truth in two files:

- `data/schema/judge.schema.json` - presence, type, enum values.
- `data/schema/fields.yaml` - labels, descriptions, contributor
  prompts, tier classification.

Both are validated against each other by
`scripts/lint-judge-yaml.py`. Drift fails CI.

To propose a change:

1.  File a **jurisdiction request** or a plain feature-request
    issue. Explain the proposed field: what it captures, which tier,
    an example standing order that makes it unambiguous.
2.  If the field is Tier 1, propose the regex patterns too. A Tier 1
    field that the scraper can't populate is a contribution-only
    field, which makes it Tier 3.
3.  A maintainer (or you, with a maintainer's OK) opens a PR that:
    - updates the schema
    - updates `fields.yaml`
    - updates `docs/schema.md`
    - adds or updates an extractor in `scrapers/common/extractors.py`
    - adds unit tests for the extractor
    - updates `data/judges/casd/example-judge.yaml` to include the
      new field
    - runs `scripts/lint-judge-yaml.py` locally and verifies it
      passes
4.  CI re-verifies, maintainer reviews, PR merges.

## Maintainers

Currently a single maintainer operates the project. Criteria and
process for adding additional maintainers will be documented here
before the second maintainer is added; placeholder until then.

## Conflict-of-interest policy

Maintainers who are litigants, employees, or relatives of a judge
listed in The Well recuse themselves from data-correction decisions
involving that judge. Recusals are tracked by a note in the
correction issue ("recused: @handle").

## Moderation appeals

Not yet relevant - no community contributions yet. When the
contribution flow opens (Stage 5+), an appeals process will be added
here. Draft: rejected contributors can request a re-review from a
different maintainer; two maintainer rejections are final.
