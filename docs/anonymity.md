# Anonymity Architecture

The Well guarantees that **individual contributions cannot be linked
to individual contributors without a deliberate administrative action
that is logged and auditable.** This document explains how.

## Threat model

We design against:

1. **Subpoena for contributor identity.** A judge, litigant, or bar
   association demands to know who contributed a specific
   observation.
2. **Database breach.** An attacker obtains a dump of one or both
   databases.
3. **Insider threat.** An operator (including the founder) attempts
   to re-identify a contributor outside sanctioned flows.
4. **Correlation attacks.** An adversary observes public aggregates
   over time and attempts to de-anonymize small sets.
5. **Account takeover.** An attacker compromises an approved
   contributor's credentials and submits false contributions.

## Architectural separation

Identity and contributions are stored in two different Cloudflare D1
databases, with different Worker bindings and different access
patterns.

- **Identity database** holds applicant names, bar numbers, firms,
  approval status, and a per-contributor `contribution_key_hash`.
- **Public database** holds judge data, standing orders, and
  contributions. Contributions are tagged with the same
  `contribution_key_hash` and nothing else that identifies the
  contributor.

Joining these requires access to both databases plus the server-side
pepper held in Cloudflare Worker environment variables. Compromise of
either database alone does not reveal the link.

## The unlinkable-key mechanism

When a contributor is approved:

1. A random 256-bit key is generated.
2. The key is hashed with a server-side pepper held in Cloudflare
   Worker environment variables (not in any database).
3. The resulting hash is stored in `applicants.contribution_key_hash`
   in the identity database, and as a private claim on the user's
   Clerk metadata.
4. The raw key is never stored server-side. It is derived at
   contribution time from the authenticated session plus the pepper.

When the contributor submits an observation:

1. The contribution-time derivation reconstructs the key from the
   user's Clerk session.
2. The key is hashed with the pepper.
3. The resulting hash is attached to the contribution row in the
   public database.
4. No user ID, IP address, user-agent, or session ID is logged with
   the contribution.

To re-identify a specific contribution, an operator must:

1. Invoke the administrative `link_contribution` tool.
2. Compute the contribution-key-hash for every approved applicant
   (O(n) operation).
3. Look for a matching hash.

Every invocation of this tool is logged to `identity_access_log`
with a stated reason. Sanctioned reasons are enumerated in our
operational runbook: legal compulsion under a court order we could
not quash, documented abuse investigation initiated by an approved
process, and pepper rotation.

## What a subpoena reveals

A hostile subpoena compelling us to cooperate can obtain:

- The contents of the identity database (names, bar numbers, firms)
- The contents of the public database (contributions and hashes)
- The output of a `link_contribution` operation run against a
  specified contribution, revealing the corresponding contributor's
  identity

A subpoena cannot obtain:

- IP addresses of contributors — we do not log them on contribution
  endpoints
- User-agents of contributors — we do not log them on contribution
  endpoints
- Session histories — sessions are short-lived and not retained
  beyond their TTL
- The pepper — held only in Cloudflare Worker environment
  variables; disclosure triggers immediate pepper rotation,
  severing all prior link capability

Our policy is to fight, to the extent legally permissible, any
subpoena targeting contributor identity, using all available
mechanisms including motions to quash, sealing, and — where not
prohibited by the court — notice to the affected contributor.

## Pepper rotation

The server-side pepper is rotated on:

- Any disclosure event or suspected breach
- Annually, as a matter of operational hygiene

Rotation invalidates prior contribution-key hashes. After rotation,
historical link operations can no longer be run against
pre-rotation contributions. This is forward-secrecy-adjacent but
not true forward secrecy: a pepper compromise combined with
retained ciphertext would re-expose prior linkages up to the next
rotation.

## Vendor trust boundaries

The Well relies on three vendors as part of its trusted computing
base:

- **Cloudflare** — hosts the site, the Worker API, the D1
  databases, and environment variables including the pepper.
- **Clerk** — handles authentication. Holds each contributor's
  email address, authentication events, and the
  `contribution_key_hash` as a private metadata field. Clerk does
  not hold the contributor's legal name, bar number, firm, or any
  contribution content.
- **GitHub** — hosts the public source repository and the CI/CD
  pipeline. Holds public judge data, public documentation, and
  audit-committed configuration.

Each of these vendors is a potential subject of legal process or
breach. We minimize what each one holds and separate sensitive data
across them architecturally. Any vendor that proves untrustworthy
triggers a rotation plan documented in our operational runbook.

## Known limitations

- **Small-sample correlation.** Aggregates computed over small
  contributor sets (e.g., a judge with only two contributors) are
  theoretically susceptible to correlation attacks. We mitigate by
  suppressing aggregate display below three contributors for any
  given (judge, field, value) combination.
- **Timing correlation.** An adversary with both application
  approval timestamps and contribution timestamps could attempt
  temporal correlation. We add jitter to contribution timestamps
  (random offset up to 5 minutes) to reduce precision of
  correlation.
- **No true forward secrecy.** A pepper compromise paired with
  retained database backups would re-expose link capability for
  contributions made before the next rotation. Rotation frequency
  is the primary mitigation.
- **Trusted vendors.** Compromise of Cloudflare, Clerk, or GitHub
  at a deep level would affect our guarantees. We cannot defend
  against vendor-level adversaries with our current architecture;
  we can only choose reputable vendors and minimize exposure.

## Independent verification

The open-source code implementing this architecture is in this
repository:

- `worker/src/lib/crypto.ts` — contribution key derivation and
  hashing
- `worker/src/routes/contribute.ts` — server-side submission
  handler
- `scripts/audit-contribution-flow.py` — auditable end-to-end test

The administrative `link_contribution` implementation is held in a
private operational repository and is not open-source. This is
deliberate: publishing the exact linking implementation offers
adversaries information without offering defenders a corresponding
benefit. The design — described above — is open; the specific
implementation is not. This follows the operational model used by
other trust-sensitive platforms.

Security researchers are welcome to audit any of this. See
[SECURITY.md](../SECURITY.md) for how to report findings; we pay
bounties for legitimate reports.
