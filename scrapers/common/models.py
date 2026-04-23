"""Pydantic v2 models that mirror data/schema/judge.schema.json.

Each model's `.to_schema_dict()` produces a dict ready for YAML dump and
JSON-Schema validation. We intentionally keep the Python field names the
same as the YAML keys, so model_dump() is a direct round-trip.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

Jurisdiction = Literal["cacd", "casd", "ca9", "lasc", "sdsc"]
CourtType = Literal["federal_district", "federal_appellate", "state_superior"]
JudgeStatus = Literal["active", "senior", "magistrate", "retired"]
Confidence = Literal["auto_extracted", "verified", "community_aggregated"]
SourceType = Literal[
    "standing_order",
    "local_rule",
    "court_website",
    "pacer_derived",
    "editor_verified",
    "community_aggregated",
]

StandingOrderTopic = Literal[
    "discovery_disputes",
    "page_limits",
    "courtesy_copies",
    "pretrial",
    "oral_argument",
    "settlement",
    "patent",
    "trial",
    "technology",
    "junior_attorney",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class StandingOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    effective_date: Optional[str] = None
    url: HttpUrl
    topics: Optional[list[StandingOrderTopic]] = None
    last_fetched_at: str

    def model_dump_yaml_ready(self) -> dict[str, Any]:
        d = self.model_dump(exclude_none=True)
        d["url"] = str(self.url)
        return d


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_key: str
    source_type: SourceType
    source_url: Optional[HttpUrl] = None
    source_excerpt: Optional[str] = None
    confidence: Confidence
    last_verified_at: str

    def model_dump_yaml_ready(self) -> dict[str, Any]:
        d = self.model_dump(exclude_none=True)
        if self.source_url is not None:
            d["source_url"] = str(self.source_url)
        return d


class Procedural(BaseModel):
    model_config = ConfigDict(extra="forbid")

    msj_page_limit: Optional[int] = Field(default=None, ge=0)
    msj_reply_page_limit: Optional[int] = Field(default=None, ge=0)
    motion_page_limit: Optional[int] = Field(default=None, ge=0)
    motion_reply_page_limit: Optional[int] = Field(default=None, ge=0)
    motion_ruling_cadence_median_days: Optional[int] = Field(default=None, ge=0)
    rules_from_bench_pct: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    courtesy_copies_required: Optional[Literal["yes", "no", "on_request", "case_type_dependent"]] = None
    courtesy_copy_format: Optional[Literal["paper", "pdf_email", "both_required", "na"]] = None
    courtesy_copy_timing: Optional[
        Literal["within_24hr", "within_48hr", "next_business_day", "same_day_as_filing", "not_specified"]
    ] = None
    chambers_direct_contact: Optional[
        Literal[
            "prohibited_except_emergencies",
            "procedural_only",
            "permitted_via_law_clerk",
            "permitted_via_ja",
            "case_by_case",
        ]
    ] = None
    zoom_hearings: Optional[
        Literal[
            "default_remote",
            "default_in_person",
            "status_conf_only_remote",
            "hybrid_by_request",
            "rarely_permits",
            "in_person_only",
        ]
    ] = None
    telephonic_appearance: Optional[
        Literal["permitted_with_notice", "case_by_case", "discouraged", "not_permitted"]
    ] = None
    electronic_exhibits_at_trial: Optional[Literal["required", "preferred", "permitted", "not_permitted"]] = None
    motion_ruling_cadence: Optional[
        Literal["under_30_days", "30_60_days", "60_90_days", "90_plus_days", "highly_variable"]
    ] = None
    rules_from_bench: Optional[Literal["frequently", "occasionally", "rarely", "never"]] = None
    page_limit_strictness: Optional[
        Literal[
            "strict_no_exceptions",
            "strict_with_leave",
            "lenient_with_good_cause",
            "generally_flexible",
        ]
    ] = None
    enforces_meet_and_confer: Optional[
        Literal["strictly_enforced", "moderately_enforced", "loosely_enforced"]
    ] = None
    oral_argument_default: Optional[
        Literal["heard_by_default", "submitted_by_default", "judge_discretion"]
    ] = None
    oral_argument_time_typical: Optional[
        Literal["under_15_min", "15_to_30_min", "30_to_60_min", "60_plus_min"]
    ] = None
    time_limit_strictness: Optional[Literal["strict_cutoff", "moderate", "lenient"]] = None
    bench_engagement: Optional[
        Literal["hot_bench_expect_questions", "moderate_questioning", "cold_bench_let_argue"]
    ] = None
    junior_attorney_argument: Optional[
        Literal["encourages_via_standing_order", "permits_when_requested", "silent", "discourages"]
    ] = None
    courtroom_tech_available: Optional[
        list[Literal["elmo", "projector", "podium_mic", "realtime_transcript", "jury_monitors", "hdmi", "vga"]]
    ] = None


class JudgeCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    slug: str
    name: str
    honorific: Optional[str] = "Hon."
    jurisdiction: Jurisdiction
    court_name: str
    court_type: CourtType
    status: JudgeStatus
    chambers_location: Optional[str] = None
    courtroom: Optional[str] = None
    appointed_by: Optional[str] = None
    appointed_year: Optional[int] = None
    prior_practice: Optional[list[str]] = None
    law_school: Optional[str] = None
    undergrad: Optional[str] = None
    chambers_email: Optional[EmailStr] = None
    proposed_order_email: Optional[EmailStr] = None
    bio_notes: Optional[str] = None
    created_at: str
    updated_at: str
    last_editor_review_at: Optional[str] = None

    standing_orders: list[StandingOrder]
    procedural: Procedural
    sources: list[Source]

    def to_schema_dict(self) -> dict[str, Any]:
        """Dump to a dict ready for YAML serialization and schema validation."""
        data = self.model_dump(exclude_none=True)
        data["standing_orders"] = [so.model_dump_yaml_ready() for so in self.standing_orders]
        data["sources"] = [s.model_dump_yaml_ready() for s in self.sources]
        data["procedural"] = self.procedural.model_dump(exclude_none=True)
        return data

    def validate_against_schema(self, schema_path: Path) -> list[str]:
        schema = json.loads(Path(schema_path).read_text())
        validator = Draft202012Validator(schema)
        errors = []
        for err in sorted(validator.iter_errors(self.to_schema_dict()), key=lambda e: list(e.absolute_path)):
            loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append(f"{loc}: {err.message}")
        return errors


def now_iso() -> str:
    return _iso_now()
