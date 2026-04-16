# Site

The Well's public site. Astro, pre-rendered at build time from YAML under `../data/`, served from Cloudflare's edge.

This directory is a stub. Expected stack: Astro, TypeScript, Tailwind. Built and deployed via GitHub Actions; see `../.github/workflows/deploy.yml` once wired up.

Public reads never touch a database. See [../docs/architecture.md](../docs/architecture.md).
