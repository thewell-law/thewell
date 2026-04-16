# Data

This directory contains the structured judicial procedure records that The Well publishes.

## License

Everything in this directory — YAML files, CSVs, JSON, derived datasets — is licensed under [CC-BY-SA 4.0](../LICENSE-DATA).

This is different from the rest of the repository, which is licensed under AGPL-3.0. The data license applies only to content under this directory and to datasets explicitly marked as derived from it.

Summary of what CC-BY-SA 4.0 means in practice:

- **You can** copy, redistribute, adapt, and build on the data, including commercially.
- **You must** give attribution ("The Well, https://thewell.example, CC-BY-SA 4.0").
- **You must** license your derived data under the same terms.
- **You cannot** impose technical protection measures that restrict what recipients can do.

Read the full text at [LICENSE-DATA](../LICENSE-DATA).

## Structure

The schema is documented in [docs/schema.md](../docs/schema.md). Brief summary:

- One file per judge, keyed by a stable slug.
- Every fact is accompanied by a citation.
- Timestamps are ISO 8601, UTC.
- All text is UTF-8.

## Contributing data

See [CONTRIBUTING.md](../CONTRIBUTING.md). Every change to files in this directory must include citations; primary sources are strongly preferred.
