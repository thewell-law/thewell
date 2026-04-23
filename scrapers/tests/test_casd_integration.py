"""Integration test for the CASD scraper with mocked HTTP responses.

Uses pytest-httpx to serve the judges index, a minimal chambers-rules
page, a stub proposed-emails page, robots.txt, and the Bashant standing
order (as a thin PDF wrapper - we mock the PDF parser to return the
fixture text directly).

This is the realistic end-to-end check: the scraper's selectors and
its orchestration match the real site's structure captured in the HTML
fixtures.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_httpx import HTTPXMock

from scrapers.casd.scrape import CasdScraper
from scrapers.common.http import PoliteClient

FIXTURES = Path(__file__).parent / "fixtures" / "casd"
JUDGES_INDEX_HTML = (FIXTURES / "judges_index_excerpt.html").read_text()
JUDGE_DETAIL_HTML = (FIXTURES / "judge_detail_battaglia_excerpt.html").read_text()
BASHANT_TEXT = (FIXTURES / "bashant_standing_order_civil.txt").read_text()
ROBOTS_TXT = (FIXTURES / "robots.txt").read_text()


@pytest.fixture
def mocked_network(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://www.casd.uscourts.gov/robots.txt", text=ROBOTS_TXT)
    httpx_mock.add_response(url="https://www.casd.uscourts.gov/Judges.aspx", text=JUDGES_INDEX_HTML)

    chambers_rules_html = """
    <html><body>
    <h3>Hon. Cynthia A. Bashant</h3>
    <ul>
      <li><a href="/judges/bashant/docs/Bashant%20Standing%20Order%20for%20Civil%20Cases.pdf">Standing Order for Civil Cases</a></li>
    </ul>
    <h3>Hon. Anthony J. Battaglia</h3>
    <ul>
      <li><a href="/judges/battaglia/docs/Battaglia%20Civil%20Procedures.pdf">Civil Procedures</a></li>
    </ul>
    </body></html>
    """
    httpx_mock.add_response(
        url="https://www.casd.uscourts.gov/judges/chambers-rules.aspx",
        text=chambers_rules_html,
    )

    proposed_emails_html = """
    <html><body>
    <a href="mailto:efile_bashant@casd.uscourts.gov">efile_bashant@casd.uscourts.gov</a>
    <a href="mailto:efile_battaglia@casd.uscourts.gov">efile_battaglia@casd.uscourts.gov</a>
    </body></html>
    """
    httpx_mock.add_response(
        url="https://www.casd.uscourts.gov/judges/proposed-emails.aspx",
        text=proposed_emails_html,
    )

    httpx_mock.add_response(
        url="https://www.casd.uscourts.gov/judges/bashant/docs/Bashant%20Standing%20Order%20for%20Civil%20Cases.pdf",
        content=b"%PDF-1.4 bashant stub",
    )
    httpx_mock.add_response(
        url="https://www.casd.uscourts.gov/judges/battaglia/docs/Battaglia%20Civil%20Procedures.pdf",
        content=b"%PDF-1.4 battaglia stub",
    )

    yield httpx_mock


def _extract_text_stub(pdf_bytes: bytes) -> str:
    if b"bashant" in pdf_bytes:
        return BASHANT_TEXT
    if b"battaglia" in pdf_bytes:
        return BASHANT_TEXT
    return ""


def test_full_scrape_dry_run(tmp_path: Path, mocked_network, monkeypatch):
    monkeypatch.chdir(tmp_path)

    client = PoliteClient(min_delay=0.0)
    scraper = CasdScraper(dry_run=True, client=client)

    from scrapers.casd import scrape as scrape_mod

    monkeypatch.setattr(scrape_mod, "JURISDICTION_DIR", tmp_path / "casd")
    (tmp_path / "casd").mkdir()
    monkeypatch.setattr(scrape_mod, "OUTPUT_DIR", tmp_path / "out")
    scraper.cache = scrape_mod.Cache(tmp_path / "casd" / ".cache")

    with patch("scrapers.casd.scrape.pdf_extract_text", side_effect=_extract_text_stub):
        report = scraper.run()

    # Fixture has 3 District Judges + 1 Magistrate = 4.
    assert report.judges_found == 4
    scraped = {pj.slug: pj for pj in report.per_judge}
    assert scraped["bashant"].standing_orders_found == 1
    assert scraped["battaglia"].standing_orders_found == 1
    assert scraped["robinson"].standing_orders_found == 0
    assert scraped["goddard"].standing_orders_found == 0
    assert "courtesy_copies_required" in scraped["bashant"].extractor_hits
    assert "oral_argument_default" in scraped["bashant"].extractor_hits
    assert report.cards_written == 0
    for pj in report.per_judge:
        if pj.skip_reason:
            pytest.fail(f"{pj.slug} skipped: {pj.skip_reason}: {pj.validation_errors}")


def test_judge_index_parser_handles_district_magistrate_visiting():
    client = PoliteClient(min_delay=0.0)
    scraper = CasdScraper(client=client)
    stubs = scraper.parse_judge_index(JUDGES_INDEX_HTML)
    by_name = {s.name: s for s in stubs}
    assert "Cynthia A. Bashant" in by_name and by_name["Cynthia A. Bashant"].status == "active"
    assert "Anthony J. Battaglia" in by_name and by_name["Anthony J. Battaglia"].status == "active"
    assert "Todd W. Robinson" in by_name and by_name["Todd W. Robinson"].status == "active"
    assert "Allison H. Goddard" in by_name and by_name["Allison H. Goddard"].status == "magistrate"
    assert "Clinton E. Averitte" not in by_name


def test_chambers_rules_parser_buckets_pdfs_by_slug():
    client = PoliteClient(min_delay=0.0)
    scraper = CasdScraper(client=client)
    html = """
    <a href="/judges/bashant/docs/Civil.pdf">Civil</a>
    <a href="/judges/battaglia/docs/Criminal.pdf">Criminal</a>
    <a href="/somewhere/else.pdf">not a judge doc</a>
    """
    result = scraper.parse_chambers_rules(html)
    assert set(result) == {"bashant", "battaglia"}
    assert result["bashant"][0][0] == "Civil"
    assert result["battaglia"][0][1] == "https://www.casd.uscourts.gov/judges/battaglia/docs/Criminal.pdf"


def test_proposed_emails_parser_picks_out_efile_addresses():
    client = PoliteClient(min_delay=0.0)
    scraper = CasdScraper(client=client)
    html = """
    <a href="mailto:efile_bashant@casd.uscourts.gov">Bashant</a>
    <a href="mailto:efile_battaglia@casd.uscourts.gov">Battaglia</a>
    <a href="mailto:random@example.com">noise</a>
    """
    result = scraper.parse_proposed_emails(html)
    assert result == {
        "bashant": "efile_bashant@casd.uscourts.gov",
        "battaglia": "efile_battaglia@casd.uscourts.gov",
    }
