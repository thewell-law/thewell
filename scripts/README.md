# Scripts

Operational and build tooling for The Well. Managed with [uv](https://docs.astral.sh/uv/).

## Setup

From the repo root:

```bash
cd scripts
uv sync
```

## Linter: judge YAML

`lint-judge-yaml.py` validates every `data/judges/**/*.yaml` against `data/schema/judge.schema.json` and cross-checks `data/schema/fields.yaml` against the schema for enum consistency.

Default behavior: fails on any schema violation or enum drift.
`--strict`: also fails on warnings (missing sources for set procedural fields; standing orders not referenced by any source of type `standing_order`).

```bash
# Lint every judge YAML under data/judges/
cd scripts && uv run python lint-judge-yaml.py

# Lint a single file
cd scripts && uv run python lint-judge-yaml.py --path ../data/judges/casd/example-judge.yaml

# Strict mode — fail on warnings too. This is what CI runs.
cd scripts && uv run python lint-judge-yaml.py --strict
```

Exit code `0` on success, `1` on any failure.
