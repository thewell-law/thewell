"""Rules-based extractors for Tier 1 procedural fields.

Each public `extract_*` function takes normalized text from a standing
order or procedures page and returns an ExtractionResult on a match, or
None. The ExtractionResult records the regex pattern and a short matched
excerpt so the field's `source.source_excerpt` is traceable.

Conventions:
- Integer fields (page limits): return int in .value
- Enum fields: return the exact schema enum string in .value
- Pattern match is case-insensitive unless noted
- For enum fields with multiple candidate phrasings, the first matching
  pattern wins
- All patterns are written so a sentence hit anywhere in the text wins;
  PDFs come back with unreliable line breaks
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional

Confidence = Literal["auto_extracted", "verified", "community_aggregated"]


@dataclass
class ExtractionResult:
    value: Any
    confidence: Confidence
    matched_pattern: str
    matched_excerpt: str

    @staticmethod
    def auto(value: Any, pattern: str, excerpt: str) -> "ExtractionResult":
        return ExtractionResult(
            value=value,
            confidence="auto_extracted",
            matched_pattern=pattern,
            matched_excerpt=excerpt[:200],
        )


EXTRACTORS: dict[str, Callable[[str], Optional[ExtractionResult]]] = {}


def extractor(field_key: str) -> Callable:
    def decorator(fn: Callable[[str], Optional[ExtractionResult]]):
        EXTRACTORS[field_key] = fn
        fn.field_key = field_key
        return fn
    return decorator


def _first_match(text: str, patterns: list[str]) -> Optional[tuple[re.Match, str]]:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m, pat
    return None


def _enum_hit(text: str, mapping: list[tuple[str, str]]) -> Optional[ExtractionResult]:
    """mapping: list of (regex, enum_value). First match wins."""
    for pat, value in mapping:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return ExtractionResult.auto(value, pat, m.group(0))
    return None


# ============================================================
# Integer extractors - page limits
# ============================================================

@extractor("msj_page_limit")
def extract_msj_page_limit(text: str) -> Optional[ExtractionResult]:
    patterns = [
        r"memorand(?:um|a)\s+in\s+support\s+of\s+(?:motions?\s+for\s+)?summary\s+judgment[^.]{0,120}?(?:shall\s+not\s+exceed|limited\s+to|no\s+longer\s+than|must\s+not\s+exceed)\s+(\d{1,3})\s+pages?",
        r"motions?\s+for\s+summary\s+judgment[^.]{0,120}?(?:shall\s+not\s+exceed|limited\s+to|no\s+longer\s+than|must\s+not\s+exceed)\s+(\d{1,3})\s+pages?",
        r"summary\s+judgment\s+motions?[^.]{0,120}?(?:are\s+)?(?:limited\s+to|shall\s+not\s+exceed|no\s+longer\s+than)\s+(\d{1,3})\s+pages?",
    ]
    hit = _first_match(text, patterns)
    if hit:
        m, pat = hit
        return ExtractionResult.auto(int(m.group(1)), pat, m.group(0))
    return None


@extractor("msj_reply_page_limit")
def extract_msj_reply_page_limit(text: str) -> Optional[ExtractionResult]:
    patterns = [
        r"reply\s+briefs?\s+on\s+motions?\s+for\s+summary\s+judgment[^.]{0,120}?(?:shall\s+not\s+exceed|limited\s+to|no\s+longer\s+than|must\s+not\s+exceed)\s+(\d{1,3})\s+pages?",
        r"summary\s+judgment\s+repl(?:y|ies)[^.]{0,120}?(?:shall\s+not\s+exceed|limited\s+to|no\s+longer\s+than)\s+(\d{1,3})\s+pages?",
    ]
    hit = _first_match(text, patterns)
    if hit:
        m, pat = hit
        return ExtractionResult.auto(int(m.group(1)), pat, m.group(0))
    return None


@extractor("motion_page_limit")
def extract_motion_page_limit(text: str) -> Optional[ExtractionResult]:
    patterns = [
        r"opening\s+memoranda\s+for\s+non-dispositive\s+motions[^.]{0,120}?(?:shall\s+not\s+exceed|limited\s+to|no\s+longer\s+than)\s+(\d{1,3})\s+pages?",
        r"non-dispositive\s+motions?[^.]{0,120}?(?:shall\s+not\s+exceed|limited\s+to|no\s+longer\s+than)\s+(\d{1,3})\s+pages?",
    ]
    hit = _first_match(text, patterns)
    if hit:
        m, pat = hit
        return ExtractionResult.auto(int(m.group(1)), pat, m.group(0))
    return None


@extractor("motion_reply_page_limit")
def extract_motion_reply_page_limit(text: str) -> Optional[ExtractionResult]:
    patterns = [
        r"reply\s+memoranda\s+on\s+non-dispositive\s+motions[^.]{0,120}?(?:shall\s+not\s+exceed|limited\s+to|no\s+longer\s+than)\s+(\d{1,3})\s+pages?",
        r"reply\s+briefs?\s+on\s+non-dispositive\s+motions[^.]{0,120}?(?:shall\s+not\s+exceed|limited\s+to|no\s+longer\s+than)\s+(\d{1,3})\s+pages?",
    ]
    hit = _first_match(text, patterns)
    if hit:
        m, pat = hit
        return ExtractionResult.auto(int(m.group(1)), pat, m.group(0))
    return None


# ============================================================
# Enum extractors - courtesy copies
# ============================================================

@extractor("courtesy_copies_required")
def extract_courtesy_copies_required(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"no\s+courtesy\s+cop(?:y|ies)\s+(?:are\s+)?(?:necessary|required)", "no"),
        (r"courtesy\s+cop(?:y|ies)\s+(?:are\s+)?not\s+required", "no"),
        (r"does\s+not\s+require\s+courtesy\s+cop(?:y|ies)\s+except\s+upon\s+request", "on_request"),
        (r"courtesy\s+cop(?:y|ies)\s+(?:are\s+)?(?:only\s+)?required\s+(?:only\s+)?upon\s+request", "on_request"),
        (r"courtesy\s+cop(?:y|ies)\s+(?:are\s+)?required\s+for\s+(?:patent|class\s+action|complex)", "case_type_dependent"),
        (r"(?:parties|counsel|litigants)\s+(?:must|shall)\s+(?:deliver|provide|submit)\s+(?:a\s+)?courtesy\s+cop(?:y|ies)", "yes"),
        (r"courtesy\s+cop(?:y|ies)\s+(?:are\s+)?required", "yes"),
    ]
    return _enum_hit(text, mapping)


@extractor("courtesy_copy_format")
def extract_courtesy_copy_format(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"courtesy\s+cop(?:y|ies)\s+shall\s+be\s+(?:emailed|e-mailed|submitted)\s+as\s+(?:a\s+)?(?:single\s+)?(?:bookmarked\s+)?pdf", "pdf_email"),
        (r"(?:email|e-mail)\s+(?:a\s+)?pdf\s+courtesy\s+cop(?:y|ies)", "pdf_email"),
        (r"both\s+(?:a\s+)?paper\s+(?:copy|cop(?:y|ies))\s+and\s+(?:a\s+)?pdf", "both_required"),
        (r"paper\s+courtesy\s+cop(?:y|ies)", "paper"),
        (r"no\s+courtesy\s+cop(?:y|ies)\s+(?:are\s+)?(?:necessary|required)", "na"),
    ]
    return _enum_hit(text, mapping)


@extractor("courtesy_copy_timing")
def extract_courtesy_copy_timing(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"courtesy\s+cop(?:y|ies)[^.]{0,80}?next\s+business\s+day", "next_business_day"),
        (r"courtesy\s+cop(?:y|ies)[^.]{0,80}?same\s+day\s+as\s+filing", "same_day_as_filing"),
        (r"courtesy\s+cop(?:y|ies)[^.]{0,80}?within\s+(?:24|twenty-four)\s+hours?", "within_24hr"),
        (r"courtesy\s+cop(?:y|ies)[^.]{0,80}?within\s+(?:48|forty-eight)\s+hours?", "within_48hr"),
    ]
    return _enum_hit(text, mapping)


# ============================================================
# Enum extractors - chambers / communication
# ============================================================

@extractor("chambers_direct_contact")
def extract_chambers_direct_contact(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"chambers.{0,40}(?:only\s+in\s+emergencies|emergenc(?:y|ies)\s+only|prohibited\s+except)", "prohibited_except_emergencies"),
        (r"contact\s+chambers\s+only\s+regarding\s+scheduling\s+and\s+procedural", "procedural_only"),
        (r"(?:emails|e-mails|letters)\s+(?:to|to\s+the)\s+chambers\s+(?:are\s+)?prohibited", "procedural_only"),
        (r"address.{0,40}communications\s+to\s+the\s+courtroom\s+deputy", "permitted_via_ja"),
        (r"contact\s+chambers\s+through\s+(?:the\s+)?law\s+clerk", "permitted_via_law_clerk"),
        (r"direct\s+(?:contact\s+with|communications\s+with)\s+chambers\s+(?:is\s+)?permitted", "case_by_case"),
    ]
    return _enum_hit(text, mapping)


@extractor("telephonic_appearance")
def extract_telephonic_appearance(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"telephonic\s+appearances?\s+are\s+not\s+permitted", "not_permitted"),
        (r"telephonic\s+appearances?\s+(?:will\s+be\s+)?permitted\s+only\s+in\s+emergency", "case_by_case"),
        (r"telephonic\s+appearances?\s+are\s+discouraged", "discouraged"),
        (r"telephonic\s+appearances?\s+are\s+permitted[^.]{0,80}?(?:with\s+)?(?:at\s+least\s+)?(?:\d+\s+hours?'?\s+)?(?:advance\s+)?notice", "permitted_with_notice"),
        (r"telephonic\s+appearances?\s+(?:are\s+)?permitted", "permitted_with_notice"),
    ]
    return _enum_hit(text, mapping)


# ============================================================
# Enum extractors - trial / technology / argument
# ============================================================

@extractor("electronic_exhibits_at_trial")
def extract_electronic_exhibits_at_trial(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"electronic\s+(?:presentation\s+of\s+)?exhibits?\s+(?:at\s+trial\s+)?(?:are\s+|is\s+)?required", "required"),
        (r"(?:the\s+court|court)\s+prefers\s+electronic\s+(?:presentation\s+of\s+)?exhibits?", "preferred"),
        (r"(?:parties|counsel)\s+must\s+submit[^.]{0,80}?trial\s+exhibits[^.]{0,80}?electronic", "required"),
        (r"electronic\s+(?:presentation\s+of\s+)?exhibits?\s+(?:are\s+|is\s+)?permitted", "permitted"),
        (r"electronic\s+(?:presentation\s+of\s+)?exhibits?\s+(?:are\s+|is\s+)?not\s+permitted", "not_permitted"),
    ]
    return _enum_hit(text, mapping)


@extractor("zoom_hearings")
def extract_zoom_hearings(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"(?:zoom|video|remote)\s+hearings?\s+are\s+the\s+default", "default_remote"),
        (r"(?:in-person|in\s+person)\s+(?:is\s+the\s+)?default", "default_in_person"),
        (r"hybrid\s+hearings?\s+(?:are\s+)?(?:offered\s+)?by\s+request", "hybrid_by_request"),
        (r"(?:zoom|video|remote)\s+hearings?[^.]{0,80}?status\s+conferences?\s+only", "status_conf_only_remote"),
        (r"(?:zoom|video|remote)\s+hearings?\s+(?:are\s+)?rarely\s+permitted", "rarely_permits"),
        (r"(?:all\s+hearings?\s+are\s+)?in-person\s+only", "in_person_only"),
    ]
    return _enum_hit(text, mapping)


@extractor("junior_attorney_argument")
def extract_junior_attorney_argument(text: str) -> Optional[ExtractionResult]:
    # Note: numbers of years are often spelled out (e.g. "five") in standing
    # orders; accept both digit and word forms.
    _num = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
    mapping = [
        (r"(?:encourage[sd]?|will\s+reserve\s+time\s+for)[^.]{0,80}?(?:junior|newer|less\s+experienced|second-?chair)\s+(?:counsel|attorneys?|lawyers?)", "encourages_via_standing_order"),
        (r"(?:junior|newer|second-?chair)\s+(?:counsel|attorneys?|lawyers?)[^.]{0,80}?(?:are\s+)?encouraged", "encourages_via_standing_order"),
        (rf"(?:court\s+will\s+)?(?:hear|hold)\s+oral\s+argument[^.]{{0,120}}?(?:handled\s+by|argued\s+by)\s+(?:an?\s+)?attorneys?\s+with\s+(?:no\s+)?more\s+than\s+{_num}\s+years", "permits_when_requested"),
        (rf"attorneys?\s+with\s+(?:no\s+)?(?:more\s+than|fewer\s+than|less\s+than)\s+{_num}\s+years\s+of\s+experience", "permits_when_requested"),
        (r"(?:junior|newer)\s+(?:counsel|attorneys?)[^.]{0,60}?(?:are\s+)?(?:permitted|allowed)\s+(?:to\s+argue\s+)?(?:upon\s+|on\s+)?request", "permits_when_requested"),
        (r"(?:junior|newer)\s+(?:counsel|attorneys?)[^.]{0,60}?discouraged", "discourages"),
    ]
    return _enum_hit(text, mapping)


@extractor("enforces_meet_and_confer")
def extract_enforces_meet_and_confer(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"(?:must|shall)\s+first\s+contact\s+opposing\s+counsel[^.]{0,200}?(?:must|shall)\s+(?:also\s+)?include[^.]{0,80}?conference\s+of\s+counsel", "strictly_enforced"),
        (r"strict(?:ly)?\s+enforce(?:d|s|ment)[^.]{0,80}?meet[- ]and[- ]confer", "strictly_enforced"),
        (r"meet[- ]and[- ]confer[^.]{0,80}?strict(?:ly)?\s+enforce", "strictly_enforced"),
        (r"meet[- ]and[- ]confer[^.]{0,80}?loose(?:ly)?\s+enforce", "loosely_enforced"),
    ]
    return _enum_hit(text, mapping)


@extractor("oral_argument_default")
def extract_oral_argument_default(text: str) -> Optional[ExtractionResult]:
    mapping = [
        (r"(?:the\s+court\s+)?hears\s+(?:oral\s+)?argument\s+on\s+all\s+(?:fully\s+briefed\s+)?(?:dispositive\s+)?motions", "heard_by_default"),
        (r"no\s+oral\s+argument\s+unless\s+ordered\s+by\s+the\s+court", "submitted_by_default"),
        (r"(?:may\s+)?resolve\s+motions\s+on\s+the\s+papers", "submitted_by_default"),
        (r"oral\s+argument\s+is\s+at\s+the\s+court'?s?\s+discretion", "judge_discretion"),
    ]
    return _enum_hit(text, mapping)


# ============================================================
# String extractors - emails
# ============================================================

_EMAIL_RE = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"


@extractor("proposed_order_email")
def extract_proposed_order_email(text: str) -> Optional[ExtractionResult]:
    patterns = [
        rf"proposed\s+orders?[^.]{{0,160}}?({_EMAIL_RE})",
        rf"e[- ]?file[_-][a-z]+@casd\.uscourts\.gov",
        rf"({_EMAIL_RE})[^.]{{0,80}}?proposed\s+orders?",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            email = m.group(1) if m.groups() else m.group(0)
            return ExtractionResult.auto(email.strip(), pat, m.group(0))
    return None


@extractor("chambers_email")
def extract_chambers_email(text: str) -> Optional[ExtractionResult]:
    patterns = [
        rf"chambers[^.]{{0,100}}?({_EMAIL_RE})",
        rf"({_EMAIL_RE})[^.]{{0,80}}?chambers",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            email = m.group(1)
            # Don't accept the e-file address as the chambers address.
            if email.lower().startswith("efile"):
                continue
            return ExtractionResult.auto(email.strip(), pat, m.group(0))
    return None


def run_all(text: str) -> dict[str, Optional[ExtractionResult]]:
    """Run every registered extractor. Returns {field_key: result_or_None}."""
    return {key: fn(text) for key, fn in EXTRACTORS.items()}
