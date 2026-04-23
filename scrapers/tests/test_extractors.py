"""Unit tests for every registered extractor.

Positive cases check that realistic standing-order language fires the
extractor with the expected value. Negative cases guard against
over-eager regexes. Fixtures in tests/fixtures/extractor_samples/ are
kept in plain text so we can assert against value semantics rather than
PDF parsing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scrapers.common import extractors

FIXTURES = Path(__file__).parent / "fixtures" / "extractor_samples"
BASHANT = (Path(__file__).parent / "fixtures" / "casd" / "bashant_standing_order_civil.txt").read_text()


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


class TestPageLimits:
    def test_msj_positive(self):
        r = extractors.extract_msj_page_limit(_load("msj_page_limit_positive.txt"))
        assert r is not None and r.value == 25

    def test_msj_positive_variant(self):
        r = extractors.extract_msj_page_limit(_load("msj_page_limit_variant.txt"))
        assert r is not None and r.value == 30

    def test_msj_negative(self):
        assert extractors.extract_msj_page_limit(_load("msj_negative.txt")) is None

    def test_msj_reply_from_fixture(self):
        r = extractors.extract_msj_reply_page_limit(_load("msj_page_limit_positive.txt"))
        assert r is not None and r.value == 15

    def test_motion_page_limit(self):
        r = extractors.extract_motion_page_limit(_load("motion_page_limits.txt"))
        assert r is not None and r.value == 20

    def test_motion_reply(self):
        r = extractors.extract_motion_reply_page_limit(_load("motion_page_limits.txt"))
        assert r is not None and r.value == 10


class TestCourtesyCopies:
    def test_none_required(self):
        r = extractors.extract_courtesy_copies_required(_load("courtesy_copies_none.txt"))
        assert r is not None and r.value == "no"

    def test_on_request(self):
        r = extractors.extract_courtesy_copies_required(_load("courtesy_copies_on_request.txt"))
        assert r is not None and r.value == "on_request"

    def test_format_pdf_email(self):
        r = extractors.extract_courtesy_copy_format(_load("courtesy_copies_on_request.txt"))
        assert r is not None and r.value == "pdf_email"

    def test_format_na_when_not_required(self):
        r = extractors.extract_courtesy_copy_format(_load("courtesy_copies_none.txt"))
        assert r is not None and r.value == "na"

    def test_timing_next_business_day(self):
        r = extractors.extract_courtesy_copy_timing(_load("courtesy_copies_on_request.txt"))
        assert r is not None and r.value == "next_business_day"

    def test_no_timing_when_not_required(self):
        assert extractors.extract_courtesy_copy_timing(_load("courtesy_copies_none.txt")) is None


class TestChambersAndTelephonic:
    def test_chambers_procedural_only(self):
        r = extractors.extract_chambers_direct_contact(_load("chambers_procedural.txt"))
        assert r is not None and r.value in {"procedural_only", "permitted_via_ja"}

    def test_telephonic_emergency_mapped_case_by_case(self):
        r = extractors.extract_telephonic_appearance(_load("telephonic_emergency.txt"))
        assert r is not None and r.value == "case_by_case"

    def test_telephonic_permitted_with_notice(self):
        r = extractors.extract_telephonic_appearance(_load("telephonic_permitted.txt"))
        assert r is not None and r.value == "permitted_with_notice"


class TestOralArgument:
    def test_submitted_by_default(self):
        r = extractors.extract_oral_argument_default(_load("oral_argument_submitted.txt"))
        assert r is not None and r.value == "submitted_by_default"

    def test_heard_by_default(self):
        r = extractors.extract_oral_argument_default(_load("oral_argument_heard.txt"))
        assert r is not None and r.value == "heard_by_default"


class TestJuniorAttorney:
    def test_encouraged(self):
        r = extractors.extract_junior_attorney_argument(_load("junior_attorney_encouraged.txt"))
        assert r is not None and r.value in {"permits_when_requested", "encourages_via_standing_order"}


class TestEmail:
    def test_proposed_order_email(self):
        r = extractors.extract_proposed_order_email(_load("email_only.txt"))
        assert r is not None and r.value == "efile_bashant@casd.uscourts.gov"


class TestAgainstRealBashantStandingOrder:
    """End-to-end: run the registry against Judge Bashant's actual text
    and assert the fields we expect to extract come out correctly. This
    is the scraper's real-world smoke test.
    """

    def test_courtesy_copies_no(self):
        r = extractors.extract_courtesy_copies_required(BASHANT)
        assert r is not None and r.value == "no"

    def test_oral_argument_submitted_by_default(self):
        r = extractors.extract_oral_argument_default(BASHANT)
        assert r is not None and r.value == "submitted_by_default"

    def test_chambers_contact_procedural(self):
        r = extractors.extract_chambers_direct_contact(BASHANT)
        assert r is not None and r.value in {"procedural_only", "permitted_via_ja"}

    def test_telephonic_emergency(self):
        r = extractors.extract_telephonic_appearance(BASHANT)
        assert r is not None and r.value == "case_by_case"

    def test_proposed_order_email(self):
        r = extractors.extract_proposed_order_email(BASHANT)
        assert r is not None and r.value == "efile_bashant@casd.uscourts.gov"

    def test_bashant_has_no_msj_page_limit(self):
        """Bashant's standing order does not set an MSJ page limit - she
        relies on Civil Local Rule 7.1. Make sure we don't invent one.
        """
        r = extractors.extract_msj_page_limit(BASHANT)
        assert r is None

    def test_registry_produces_dict(self):
        results = extractors.run_all(BASHANT)
        populated = {k for k, v in results.items() if v is not None}
        assert {
            "courtesy_copies_required",
            "oral_argument_default",
            "chambers_direct_contact",
            "telephonic_appearance",
            "proposed_order_email",
        } <= populated


class TestExtractionResult:
    def test_excerpt_is_trimmed_to_200_chars(self):
        text = "Summary judgment motions are limited to 25 pages. " + ("x" * 1000)
        r = extractors.extract_msj_page_limit(text)
        assert r is not None
        assert len(r.matched_excerpt) <= 200
