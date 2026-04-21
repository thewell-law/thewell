# Authentication

The Well uses [Clerk](https://clerk.com) for authentication. This document describes why, what Clerk holds, what it does not, and the configuration that follows from the threat model.

## Why Clerk

Three reasons, in order:

1. **Operational familiarity.** The team running The Well has operated Clerk at scale in prior projects. Familiarity reduces the rate of configuration mistakes, and authentication is an area where configuration mistakes are catastrophic.
2. **Sane defaults.** Clerk's defaults — argon2id for passwords where still used, short-lived JWTs, rotation on refresh — match what we would implement ourselves.
3. **Good primitives.** Clerk exposes the building blocks we need (private metadata on the user, JWT templates, per-event webhook subscriptions) without forcing us to accept features we do not want.

Clerk is a trust boundary. See [`threat-model.md`](./threat-model.md) and [`anonymity.md`](./anonymity.md).

## What Clerk holds

- Email address.
- Clerk user ID.
- Authentication events (sign-in, sign-out, 2FA enrolment and removal, passkey registration).
- Private metadata pointing to our own records: `application_id` (row in `IDENTITY_DB`) and `contribution_key_hash` (the hash used to tag contributions, derived at approval time from a random key plus a server-side pepper).

## What Clerk does not hold

- Legal name.
- Bar number.
- Firm affiliation.
- Any contribution content.
- IP logs for contributions. (Clerk retains a coarse "session created from" IP for its own auth-session table; the contribution Worker does not read or join that field, and contribution endpoints do not log IP at all.)

## Auth methods enabled

- **Email + passkey.** Passkeys (WebAuthn) are the primary credential. Contributors enrol a platform or roaming authenticator at sign-up; the email is a recovery address, not a login factor on its own.

## Auth methods disabled

- **Social login.** Disabled. Linking a Well account to a Google, GitHub, or Apple account re-introduces a third-party correlation vector that we worked to eliminate on the contribution side. There is no legitimate need for social login on this system.
- **Magic links.** Disabled. Email-link authentication collapses account security to "whoever currently reads this inbox" and leaves a durable auth artifact in email archives that sits outside our control.
- **SMS 2FA.** Disabled. SIM-swap attacks are within reach of motivated civil adversaries, and carrier logs of authentication events are reachable by subpoena.

## 2FA

- **Required for every contributor account.** Enrolment happens at first sign-in and cannot be skipped.
- **TOTP preferred** (Authy, Aegis, 1Password, Google Authenticator). TOTP is universal and requires no specific hardware.
- **WebAuthn security keys supported** and recommended for maintainer accounts.
- **SMS 2FA disabled**, as noted above.

## Session TTLs

- **Maximum session lifetime: 12 hours.** After 12h of wall-clock time from authentication, the session expires regardless of activity.
- **Idle timeout: 2 hours.** A session with no interaction for 2h requires re-authentication.

Short TTLs mean a leaked token is useful only briefly, and compelled disclosure of session state reveals at most the current half-day.

## Step-up authentication

Contribution submission requires a session less than **1 hour old**. If the session is older than 1 hour at the time of submission, Clerk's step-up flow prompts for the second factor again before the contribution is accepted.

This limits the blast radius of a stolen-but-unattended session: the attacker has to pass 2FA again to submit anything, not just to read pages.

## Webhook events subscribed

The contribution Worker subscribes to exactly two Clerk webhook events:

- `user.created`
- `user.deleted`

Explicitly not subscribed:

- `session.created`
- `session.ended`, `session.revoked`, `session.removed`
- Every other event Clerk exposes.

Session-lifecycle events are not subscribed because they would create a log of when contributors sign in and out, which is exactly the kind of correlatable signal the anonymity architecture exists to avoid. The Worker has no operational need for that signal, so we do not receive it.

## Account deletion

Users can delete their account from account settings. Deletion:

1. Marks the `IDENTITY_DB` row as tombstoned (retained 30 days for abuse investigation, then purged).
2. Severs the link between Clerk user ID and `contribution_key_hash`.
3. Triggers Clerk's user-deletion flow, which deletes credentials, passkey registrations, and session records.
4. Via the `user.deleted` webhook, the contribution Worker marks all contributions from that hash as `revoked`. The Worker does not hard-delete them — contributions merged into `data/` belong to the public record, and revocation lets moderators decide whether to carry the fact forward under a different attribution.

## Operational controls

- Maintainer sessions require WebAuthn for any action that reads personally identifying data from `IDENTITY_DB`.
- Clerk admin-dashboard access is limited to two maintainers, each holding a hardware key.
- Admin actions are logged to `identity_access_log` (append-only).

## Open questions

- Whether to support a Tor-friendly self-hosted IdP as an alternative to Clerk for the highest-risk contributors. Tracked in [`governance.md`](./governance.md).
