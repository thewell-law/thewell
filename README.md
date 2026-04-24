# The Well

**Open-source infrastructure for judicial procedure.**

The Well is a free-to-read database of how federal and California state judges run their courtrooms — their standing orders, filing preferences, motion practice cadence, and oral argument tendencies. The data is maintained by verified California-barred attorneys who contribute observations anonymously.

Read the site: [thewell.law](https://the-well-8ch.pages.dev) *(coming soon)*

## Why

Every senior litigator keeps a mental file on each judge they appear before: page-limit strictness, whether chambers takes phone calls, how long oral argument really runs. Junior attorneys walk into those same courtrooms blind.

The information is public. Standing orders are published on court websites. Local rules are free. But finding, reading, and cross-referencing those documents for 150 judges takes a week of work nobody has time to do. So the knowledge stays locked in senior partners' heads and gets passed down by oral tradition.

The Well changes that. Every published standing order is aggregated, parsed, and linked. Every field is sourced. Verified attorneys contribute their observations anonymously, and aggregated results appear on the public site.

## What's in this repo

- `data/judges/` — the judge cards. YAML, CC-BY-SA 4.0.
- `scrapers/` — one scraper per jurisdiction. AGPL-3.0.
- `site/` — the Astro site that renders `data/` into a browsable reference.
- `docs/` — architecture, threat model, methodology, governance.

What's *not* in this repo: the operational infrastructure that handles contributor identity (private repo), any secrets, or any code path that could re-identify a contributor.

## Licenses

- **Code:** [AGPL-3.0](./LICENSE). If you run a modified version as a web service, you must publish your modifications under the same license.
- **Data & schema:** [CC-BY-SA 4.0](./LICENSE-DATA). Attribute The Well and share derivative datasets under the same license.

## Contributing

Four ways to help:

1. **Add a jurisdiction.** See [CONTRIBUTING.md](./CONTRIBUTING.md).
2. **Improve an extractor.** Open a PR against `scrapers/common/extractors.py`.
3. **Correct a judge card.** File an issue with the `data:correction` label or open a PR against the YAML.
4. **Contribute as an attorney.** California-barred attorneys can apply at [thewell.law/contribute](https://thewell.law/contribute) (coming soon). Applications are manually reviewed.

## What we don't do

- We do not publish subjective opinions about judges.
- We do not log IP addresses on contributor-facing endpoints.
- We do not run analytics or session replay on those pages.
- We do not link specific contributions to specific contributors, architecturally. See [docs/anonymity.md](./docs/anonymity.md).

## Security

Please report security issues per [SECURITY.md](./SECURITY.md). We run a bug bounty with cash rewards for legitimate findings.

## Warrant canary

See [CANARY.md](./CANARY.md). Updated weekly.

## About

The Well is maintained by Zack Pearson and the open-source community. It is operated by The Well Legal Inc., a Delaware C-corporation separate from any other entity.
