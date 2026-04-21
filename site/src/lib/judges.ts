/**
 * Stage 2 stub.
 *
 * Stage 3 will reimplement this loader against the canonical schema at
 * ../../../data/schema/judge.schema.json. Until then getAllJudges()
 * returns [] so the Astro build stays green while Stage 3 is in flight.
 *
 * TODO(stage-3): parse every YAML under data/judges/, validate each
 * record against the JSON Schema, and return typed Judge records
 * consistent with the canonical taxonomy in data/schema/fields.yaml.
 */

export interface Judge {
  slug: string;
  jurisdiction: string;
  name: string;
}

export interface JurisdictionSummary {
  slug: string;
  name: string;
  count: number;
}

export function getAllJudges(): Judge[] {
  return [];
}

export function getJudge(_jurisdiction: string, _slug: string): Judge | undefined {
  return undefined;
}

export function getJurisdictions(): JurisdictionSummary[] {
  return [];
}

export function jurisdictionName(slug: string): string {
  return slug.toUpperCase();
}
