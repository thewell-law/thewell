# Threat Model

Adversaries The Well is built to resist, the trust boundaries it accepts, and the mitigations in place. Read alongside [`architecture.md`](./architecture.md) and [`anonymity.md`](./anonymity.md).

## Adversaries

### 1. Compelled legal process (subpoena, warrant, NSL)

**Who.** Law enforcement, civil litigants seeking contributor identity, foreign governments reaching Cloudflare or Clerk.

**What they want.** The identity of a specific contributor, or the full set of contributors to a specific judge's record.

**What they get under the current design.**

- From `PUBLIC_DB`: a contribution and a `contribution_key_hash`. Nothing that resolves to a person.
- From `IDENTITY_DB`: the mapping from `contribution_key_hash` to Clerk user ID (if the hash is known).
- From Clerk: email, 2FA method, session history.
- From Cloudflare edge logs (retained 24h, scrubbed thereafter): nothing persistently useful past the retention window.

**What they do not get.**

- IP addresses beyond 24 hours.
- Device fingerprints.
- Browsing history on The Well.
- Correlations across unrelated contributions if the contributor used distinct accounts.

**Mitigations.** Data minimization, separation of identity and content, short retention windows, warrant canary (`CANARY.md`), commitment to challenge overbroad process.

### 2. Database breach

**Who.** An attacker with read access to one of the D1 databases — through Cloudflare misconfiguration, credential leak, or a dependency vulnerability.

**What they get.**

- `PUBLIC_DB` alone: contributions tied to `contribution_key_hash`. Useless for deanonymization.
- `IDENTITY_DB` alone: hash-to-Clerk-ID mappings with no contribution content attached.
- Both plus Clerk: identity linked to contributions. This is the worst case.

**Mitigations.** Separate credentials for the two databases. Clerk configured so that bulk export requires MFA from the account owner. Audit logging on Clerk and Cloudflare. Database content is the minimum needed; there is little to steal.

### 3. Insider threat

**Who.** A current or former maintainer.

**What they can do.** Read both databases, push code, rotate keys, modify the site.

**Mitigations.**

- Two-person rule for production secrets; no single maintainer holds every key.
- Signed commits required on `main`.
- Warrant canary signed by at least two maintainers (once established).
- Public audit log of admin actions (in progress).
- Moderation decisions are reviewable.

We do not try to protect against a majority of maintainers going rogue. A governance compromise is a governance problem, not a technical one. See [`governance.md`](./governance.md).

### 4. Correlation attack

**Who.** A researcher, journalist, adversary with time, or ML pipeline comparing contributions on The Well to other public writing by the same person.

**What they can do.**

- Stylometric analysis of contribution text.
- Inference from specificity ("only three people were in that courtroom on that date").
- Cross-referencing submission timestamps with other public activity.

**Mitigations.** These are structural risks of any disclosure platform. We mitigate by:

- Warning contributors clearly ([`anonymity.md`](./anonymity.md)).
- Not publishing submission timestamps at sub-day granularity.
- Encouraging contributors to generalize ("scheduling orders in this division tend to..." rather than "on 2026-03-14 in Courtroom 5B, the judge said..."), and offering guidance in the submission UI.
- Offering the option to pool contributions into a single maintainer-authored summary rather than publishing them verbatim.
- Suppressing aggregate display below three contributors for any given (judge, field, value) combination.

### 5. Account takeover of a contributor

**Who.** An attacker who obtains an approved contributor's email plus credentials, or steals a live session token.

**What they want.** The ability to submit contributions under the victim's `contribution_key_hash`, corrupting the data and damaging the victim's standing in the contributor community.

**Mitigations.**

- 2FA required for every contributor account, with passkeys as the primary factor and TOTP accepted (see [`auth.md`](./auth.md)).
- Step-up re-authentication required before contribution submission when the session is older than one hour.
- Short session TTLs (12h max, 2h idle) cap the usefulness of any single leaked token.
- Contributions enter a moderation queue before publication; obvious abuse is caught before it reaches `data/`.
- Contributors can report a compromised account and request review and removal of contributions made during the compromise window.

## Trust boundaries

We trust, and cannot operate without trusting:

### Cloudflare

Hosts the site, runs Workers, hosts D1, operates the edge. A Cloudflare compromise or a Cloudflare-directed legal order we are not party to is outside our control. We rely on Cloudflare's published transparency practices and the separation between Cloudflare-held data (edge logs, D1 contents) and Clerk-held data (identity).

### Clerk

Handles authentication. A Clerk compromise would expose email addresses and session metadata for contributors. Clerk does not hold contribution content. See [`auth.md`](./auth.md).

### GitHub

Hosts source code, issues, and PRs. A GitHub compromise would let an adversary push malicious code. Mitigated with signed commits, required reviews, and deploy-time artifact verification.

### DNS registrar

Registrar compromise would let an adversary point `thewell.law` at infrastructure they control. Mitigated with registrar 2FA and registry lock.

## Out of scope

- Nation-state adversaries with global passive-adversary capability. Tor is the recommended defense; we cannot provide one.
- Adversaries who compromise a contributor's device. Not a boundary we can defend.
- Social engineering of individual contributors. Not a boundary we can defend.
- Legal regimes that prohibit publication of the data itself. We will comply with binding law in the jurisdictions we operate in, and be transparent when we do.

## Review

This threat model is reviewed at least every six months and after any incident. Last reviewed: 2026-04-16.
