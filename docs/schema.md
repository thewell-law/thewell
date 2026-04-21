# Data Schema

Every judge record in The Well is a YAML file under `data/judges/<jurisdiction>/<slug>.yaml`. This document explains how those records are structured, where the authoritative sources live, and how to add a field.

## What the schema is

The canonical schema is a [JSON Schema](https://json-schema.org/) draft 2020-12 document at [`data/schema/judge.schema.json`](../data/schema/judge.schema.json). It declares:

- Required top-level fields (`id`, `slug`, `name`, `jurisdiction`, `court_name`, `court_type`, `status`, `created_at`, `updated_at`, `standing_orders`, `procedural`, `sources`).
- Optional top-level fields (`honorific`, `chambers_location`, `courtroom`, `appointed_by`, `appointed_year`, `prior_practice`, `law_school`, `undergrad`, `chambers_email`, `proposed_order_email`, `bio_notes`, `last_editor_review_at`).
- A typed `procedural` object with `additionalProperties: false`. Unknown procedural fields are rejected — this is deliberate, to prevent silent schema drift.
- Nested schemas for `standing_order` objects and `source` objects.
- Enum lists for every categorical procedural field.

The schema is strict: it validates YAML records byte-for-byte on every PR via `.github/workflows/test.yml`.

## Where the authoritative sources live

Two files, in the order you should think about them:

1. **[`data/schema/judge.schema.json`](../data/schema/judge.schema.json)** — the structural contract. Field presence, types, enums, formats.
2. **[`data/schema/fields.yaml`](../data/schema/fields.yaml)** — the taxonomy. For each procedural field, it declares the display label, the contributor-facing prompt (for Tier 3 fields), the human-readable value labels, the category (filing, communication, motion_practice, oral_argument, technology), and the tier.

The JSON Schema is consumed by the linter and — in Stage 3 — by the site. The taxonomy is consumed by the submission UI and by the renderer that turns a judge card into a page.

The two files must stay in sync on enum values. The linter (`scripts/lint-judge-yaml.py`) enforces this bidirectionally.

## Data tiers

Every procedural field has a tier that describes where its values come from and how much trust you can place in them.

- **Tier 1 — objective, extracted.** Values come from a rules-based scraper reading a standing order or a court website. The source object's `confidence` is `auto_extracted` or `verified`. Example: `msj_page_limit: 25`, sourced from a civil standing order.
- **Tier 2 — derived from PACER.** Values computed from public court data (docket entries, minute orders). Example: `motion_ruling_cadence_median_days: 45`, computed as the median days from submission to order across contested motions.
- **Tier 3 — community-contributed.** Values come from verified California-barred attorneys submitting observations. Aggregated, suppressed below three contributors. The source object's `confidence` is `community_aggregated`. Example: `bench_engagement: moderate_questioning`.

A single judge card mixes tiers freely. The reader should always be able to trace any fact to its tier via the matching `sources[]` entry.

## Example

See [`data/judges/casd/example-judge.yaml`](../data/judges/casd/example-judge.yaml). It is a fictional judge used as a template: every field is populated, every procedural field has a matching source, and both standing orders are referenced. Scrapers target this shape.

## Adding a new field

The steps, in order:

1. **Update `data/schema/fields.yaml`.** Add an entry keyed by the new field_key with `field_type`, `display_label`, `description`, `category`, `tier`, and — for enum/multi_select fields — `values` and `value_labels`. Tier 3 fields also need `contributor_prompt`.
2. **Update `data/schema/judge.schema.json`.** Add the field under `$defs.procedural.properties` with matching type, and — for enum/multi_select — the matching enum list.
3. **Update this document.** Add the new field to the relevant tier example in the Data tiers section, if it illustrates something new.
4. **If Tier 1:** add or update the scraper under `scrapers/<jurisdiction>/` to extract the field. If Tier 3: confirm that `contributor_prompt` is set so the submission UI can render the question.
5. **Run the linter locally.** `cd scripts && uv run python lint-judge-yaml.py --strict`. It must pass.
6. **Update `data/judges/casd/example-judge.yaml`.** Add the new field to the reference card so it remains a complete example, and add a matching entry under `sources[]`.
7. **Record the change in `CHANGELOG.md`** under `[Unreleased]`. Schema changes are versioned; downstream consumers rely on the record.
8. **Open the PR.** CI runs the linter on every change; your PR cannot merge red.

## Running the linter

```bash
cd scripts
uv sync
uv run python lint-judge-yaml.py             # lint the full tree
uv run python lint-judge-yaml.py --strict    # also fail on warnings
uv run python lint-judge-yaml.py --path ../data/judges/casd/example-judge.yaml
```

What the linter checks:

- Every `data/judges/**/*.yaml` validates against `data/schema/judge.schema.json`.
- Every enum in the schema has a matching `values` list in `fields.yaml`, and vice versa.
- Every procedural key in `fields.yaml` corresponds to a procedural property in the schema.
- **(strict)** Every set procedural field has at least one entry in `sources[]`.
- **(strict)** Every standing order is referenced by at least one `sources[]` entry with `source_type: standing_order`.

See [`scripts/README.md`](../scripts/README.md) for setup details.

## Commitment

Schema changes go through PR review like any other change. Every schema change lands as its own commit (or set of commits) and is recorded in [`CHANGELOG.md`](../CHANGELOG.md) under the appropriate `Added` / `Changed` / `Removed` section. Enum changes are not retroactive: if we rename or drop an enum value, existing data is migrated in the same PR and the old value stops validating.
