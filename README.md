# The Well

<p align="center">
  <strong>Know your judge before you walk into the courtroom.</strong>
</p>

<p align="center">
  <a href="https://thewell.law"><img src="https://img.shields.io/badge/thewell.law-visit-0A0A0A?style=flat-square&logo=google-chrome&logoColor=white" alt="Website" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/code-AGPL--3.0-blue?style=flat-square" alt="AGPL-3.0" /></a>
  <a href="LICENSE-DATA"><img src="https://img.shields.io/badge/data-CC--BY--SA--4.0-green?style=flat-square" alt="CC-BY-SA-4.0" /></a>
  <a href="CANARY.md"><img src="https://img.shields.io/badge/warrant_canary-active-brightgreen?style=flat-square" alt="Warrant Canary" /></a>
  <a href="https://github.com/sponsors/zackpearson"><img src="https://img.shields.io/badge/sponsor-GitHub-ea4aaa?style=flat-square&logo=github-sponsors&logoColor=white" alt="Sponsor" /></a>
</p>

---

**The Well** is an open-source database of how federal and California state judges actually run their courtrooms — standing orders, filing preferences, motion practice cadence, oral argument tendencies, and procedural quirks. Sourced from public records and anonymous attorney observations.

Free to read. Free to use. Free to build on.

---

## The Problem

Every senior litigator keeps a mental file on each judge they appear before: page-limit strictness, whether chambers takes phone calls, how long oral argument really runs.

**Junior attorneys walk into those same courtrooms blind.**

The information is public. Standing orders are on court websites. Local rules are free. But finding, reading, and cross-referencing those documents for 150+ judges takes a week of work nobody has time to do. So the knowledge stays locked in senior partners' heads and gets passed down by oral tradition.

The Well changes that.

---

## What's Inside

<table>
<tr>
<td width="50%">

**Public Record Data**

Every published standing order aggregated, parsed, and linked. Every field sourced. Structured YAML cards for each judge.

- Standing orders and local rules
- Filing preferences and page limits
- Motion practice procedures
- Calendar and scheduling patterns
- Contact and chambers information

</td>
<td width="50%">

**Attorney Observations**

Verified California-barred attorneys contribute anonymously. Contributions are architecturally unlinkable to contributor identity.

- Oral argument tendencies
- Courtroom procedures in practice
- Procedural quirks not in written rules
- All observations aggregated and anonymized

</td>
</tr>
</table>

---

## What's in This Repo

```
data/judges/       Judge cards (YAML, CC-BY-SA 4.0)
scrapers/           One scraper per jurisdiction (AGPL-3.0)
site/               Astro site that renders data/ into a browsable reference
docs/               Architecture, threat model, methodology, governance
```

What's **not** in this repo: the operational infrastructure that handles contributor identity (private repo), any secrets, or any code path that could re-identify a contributor.

---

## Privacy Commitments

This is not a typical open-source project. Attorney contributors take professional risk. We take that seriously.

- We do **not** publish subjective opinions about judges
- We do **not** log IP addresses on contributor-facing endpoints
- We do **not** run analytics or session replay on those pages
- We do **not** link specific contributions to specific contributors — [architecturally](./docs/anonymity.md)
- We do **not** use AI in the data pipeline — extractors are regex + parsing
- We maintain a [warrant canary](./CANARY.md) updated weekly
- We run a [bug bounty](./SECURITY.md) with cash rewards

---

## Contributing

| How | What |
|-----|------|
| **Add a jurisdiction** | Create scrapers and YAML data for a new court. See [CONTRIBUTING.md](./CONTRIBUTING.md). |
| **Improve an extractor** | PR against `scrapers/common/extractors.py`. Tests required. |
| **Correct a judge card** | File an issue with `data-correction` label or PR the YAML with a citation. |
| **Contribute as an attorney** | California-barred attorneys can apply at [thewell.law/contribute](https://thewell.law/contribute). Manually reviewed. |

Every fact needs a citation. Corrections without sources are indistinguishable from rumors.

---

## Licenses

- **Code:** [AGPL-3.0](./LICENSE) — if you run a modified version as a web service, publish your modifications under the same license
- **Data & schema:** [CC-BY-SA 4.0](./LICENSE-DATA) — attribute The Well, share derivatives under the same license

---

## Documentation

| Document | What it covers |
|----------|---------------|
| [Architecture](./docs/architecture.md) | System design and component overview |
| [Anonymity](./docs/anonymity.md) | How contributor identity is protected |
| [Threat Model](./docs/threat-model.md) | What we defend against and what we don't |
| [Methodology](./docs/methodology.md) | How data is collected, validated, and published |
| [Governance](./docs/governance.md) | Project governance and decision-making |
| [Schema](./docs/schema.md) | Judge card YAML schema reference |
| [Auth](./docs/auth.md) | Authentication architecture |

---

## About

The Well is maintained by Zachary Brenner and the open-source community. It is operated solely by Zachary Brenner.

<p align="center">
  <a href="https://thewell.law"><strong>thewell.law</strong></a>
</p>
