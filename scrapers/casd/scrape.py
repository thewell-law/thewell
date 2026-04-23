"""Scraper for the U.S. District Court for the Southern District of California.

Source website structure
------------------------
The CASD site (https://www.casd.uscourts.gov) is an ASP.NET Web Forms
application. Navigation between the judges index and individual judge
detail pages uses __VIEWSTATE + __doPostBack, not RESTful URLs, which
makes per-judge detail pages awkward to fetch directly.

We work around this by relying on three observations:

1.  The judges index at https://www.casd.uscourts.gov/Judges.aspx lists
    every active judge. The page contains anchors of the form::

        <a ... class="p_JudgeList"
           title="Hon. {Full Name}">Hon. {Full Name}</a>

    grouped under repeater IDs that distinguish District, Magistrate,
    and Visiting judges (``FullTopWidth_rptrDistrictJudge1_...``,
    ``FullTopWidth_rptrDMagistrateJudge1_...``, ``rptrVisitingJudge``).

2.  Each judge's chambers rules, standing orders, and other procedures
    live under a conventional URL path::

        https://www.casd.uscourts.gov/judges/{lastname_slug}/docs/*.pdf

    confirmed from both Judge Battaglia's detail page (``battaglia/docs/...``)
    and Judge Bashant's standing order link.

3.  A consolidated chambers-rules page at
    ``/judges/chambers-rules.aspx`` lists every judge's standing orders
    with direct PDF links. A proposed-orders-email page at
    ``/judges/proposed-emails.aspx`` lists per-judge e-file addresses.
    Both are rendered server-side once and do not require postbacks to
    view the data we need.

The scraper therefore:

  1. GETs /Judges.aspx and parses the list of judges + their role.
  2. GETs /judges/chambers-rules.aspx and maps each judge to the PDFs
     linked under their name.
  3. GETs /judges/proposed-emails.aspx and maps each judge to their
     efile@casd.uscourts.gov address.
  4. For every judge, derives the directory slug from their last name,
     downloads each linked PDF (via the local cache), extracts text,
     and runs the Tier-1 extractors.
  5. Emits data/judges/casd/{slug}.yaml per judge, validated against
     data/schema/judge.schema.json before writing.

robots.txt
----------
The CASD robots.txt disallows ``/Judges/`` (capital J, as a directory)
for ``User-agent: *``. The index page ``/Judges.aspx`` is a file, not a
directory match, and the per-judge PDFs live under ``/judges/`` (lowercase)
which is not in the Disallow list. robotparser handles this correctly;
the :class:`scrapers.common.http.PoliteClient` checks every URL before
fetching.
"""

from __future__ import annotations

import dataclasses
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from bs4 import BeautifulSoup

from scrapers.common.audit import log_scrape_event
from scrapers.common.cache import Cache
from scrapers.common.extractors import EXTRACTORS, ExtractionResult
from scrapers.common.http import PoliteClient
from scrapers.common.models import (
    JudgeCard,
    Procedural,
    Source,
    StandingOrder,
    now_iso,
)
from scrapers.common.normalize import lastname_slug, parse_judge_name
from scrapers.common.pdf import extract_text as pdf_extract_text
from scrapers.common.pdf import get_pdf_hash

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "judge.schema.json"
OUTPUT_DIR = REPO_ROOT / "data" / "judges" / "casd"
JURISDICTION_DIR = Path(__file__).resolve().parent

ENUM_FIELDS_WITH_SOURCE_TYPE_STANDING_ORDER = {
    "msj_page_limit",
    "msj_reply_page_limit",
    "motion_page_limit",
    "motion_reply_page_limit",
    "courtesy_copies_required",
    "courtesy_copy_format",
    "courtesy_copy_timing",
    "chambers_direct_contact",
    "telephonic_appearance",
    "electronic_exhibits_at_trial",
    "enforces_meet_and_confer",
    "junior_attorney_argument",
    "oral_argument_default",
    "zoom_hearings",
    "proposed_order_email",
    "chambers_email",
}


@dataclass
class JudgeStub:
    name: str
    status: str

    @property
    def slug(self) -> str:
        return lastname_slug(self.name)


@dataclass
class StandingOrderRaw:
    url: str
    title: str
    content: bytes
    text: str
    sha256: str


@dataclass
class ExtractorOutcome:
    extracted: dict[str, Optional[ExtractionResult]] = field(default_factory=dict)

    def hit_keys(self) -> list[str]:
        return [k for k, v in self.extracted.items() if v is not None]


@dataclass
class JudgeReport:
    slug: str
    name: str
    status: str
    written: bool
    extractor_hits: list[str]
    standing_orders_found: int
    validation_errors: list[str] = field(default_factory=list)
    skip_reason: Optional[str] = None


@dataclass
class ScrapeReport:
    judges_found: int = 0
    cards_written: int = 0
    per_judge: list[JudgeReport] = field(default_factory=list)
    per_field_hits: dict[str, int] = field(default_factory=dict)


class CasdScraper:
    JURISDICTION = "casd"
    BASE_URL = "https://www.casd.uscourts.gov"
    JUDGES_INDEX = "/Judges.aspx"
    CHAMBERS_RULES = "/judges/chambers-rules.aspx"
    PROPOSED_EMAILS = "/judges/proposed-emails.aspx"

    COURT_NAME = "U.S. District Court, Southern District of California"
    COURT_TYPE = "federal_district"

    def __init__(
        self,
        dry_run: bool = False,
        rebuild_cache: bool = False,
        only_slug: Optional[str] = None,
        client: Optional[PoliteClient] = None,
    ) -> None:
        self.dry_run = dry_run
        self.only_slug = only_slug
        self.client = client or PoliteClient()
        self.cache = Cache(JURISDICTION_DIR / ".cache")
        if rebuild_cache:
            self.cache.clear()

    def parse_judge_index(self, html: str) -> list[JudgeStub]:
        soup = BeautifulSoup(html, "html.parser")
        stubs: list[JudgeStub] = []
        seen: set[str] = set()

        def _add(name: str, status: str) -> None:
            if name in seen:
                return
            seen.add(name)
            stubs.append(JudgeStub(name=name, status=status))

        for a in soup.select("a.p_JudgeList"):
            anchor_id = a.get("id", "") or ""
            title = a.get("title", "") or a.get_text(strip=True)
            parsed = parse_judge_name(title)
            name = parsed["name"]
            if not name:
                continue
            if "rptrDistrictJudge" in anchor_id:
                _add(name, "active")
            elif "rptrDMagistrateJudge" in anchor_id:
                _add(name, "magistrate")

        return stubs

    def get_judge_index(self) -> list[JudgeStub]:
        url = self.BASE_URL + self.JUDGES_INDEX
        text = self.client.fetch_text(url)
        if text is None:
            raise RuntimeError(f"index page returned 404: {url}")
        return self.parse_judge_index(text)

    def parse_chambers_rules(self, html: str) -> dict[str, list[tuple[str, str]]]:
        soup = BeautifulSoup(html, "html.parser")
        by_slug: dict[str, list[tuple[str, str]]] = {}
        pattern = re.compile(r"(?:^|/)judges/([a-z0-9-]+)/docs/", re.IGNORECASE)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = pattern.search(href)
            if not m:
                continue
            slug = m.group(1).lower()
            title = a.get_text(strip=True) or href.rsplit("/", 1)[-1]
            abs_url = self._absolutize(href)
            by_slug.setdefault(slug, []).append((title, abs_url))
        return by_slug

    def _absolutize(self, href: str) -> str:
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            return self.BASE_URL + href
        return f"{self.BASE_URL}/judges/{href.lstrip('./')}"

    def fetch_chambers_rules(self) -> dict[str, list[tuple[str, str]]]:
        url = self.BASE_URL + self.CHAMBERS_RULES
        text = self.client.fetch_text(url)
        if text is None:
            log.warning("chambers-rules page returned 404: %s", url)
            return {}
        return self.parse_chambers_rules(text)

    _EMAIL_RE = re.compile(r"efile[_-]?([a-z0-9.]+)@casd\.uscourts\.gov", re.IGNORECASE)

    def parse_proposed_emails(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        by_slug: dict[str, str] = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = self._EMAIL_RE.search(href) or self._EMAIL_RE.search(a.get_text() or "")
            if not m:
                continue
            candidate = m.group(1).lower()
            email_text = m.group(0).lower()
            email = email_text.split(":", 1)[-1] if ":" in email_text else email_text
            by_slug[candidate] = email
        return by_slug

    def fetch_proposed_emails(self) -> dict[str, str]:
        url = self.BASE_URL + self.PROPOSED_EMAILS
        text = self.client.fetch_text(url)
        if text is None:
            log.warning("proposed-emails page returned 404: %s", url)
            return {}
        return self.parse_proposed_emails(text)

    def fetch_standing_orders(self, pdf_urls: list[tuple[str, str]]) -> list[StandingOrderRaw]:
        out: list[StandingOrderRaw] = []
        for title, url in pdf_urls:
            content = self.cache.get(url)
            if content is None:
                result = self.client.fetch(url)
                if result is None:
                    log.warning("standing order 404: %s", url)
                    continue
                content = result.content
                self.cache.put(url, content, content_type=result.content_type)
            text = pdf_extract_text(content)
            out.append(
                StandingOrderRaw(
                    url=url,
                    title=title,
                    content=content,
                    text=text,
                    sha256=get_pdf_hash(content),
                )
            )
        return out

    def _topics_for(self, title: str, text: str) -> list[str]:
        t = (title + " " + text[:500]).lower()
        topics: list[str] = []
        if "patent" in t:
            topics.append("patent")
        if "civil" in t or "motion" in t or "summary judgment" in t:
            topics.append("page_limits")
        if "courtesy" in t:
            topics.append("courtesy_copies")
        if "oral argument" in t or "hearing" in t:
            topics.append("oral_argument")
        if "discovery" in t or "meet and confer" in t or "meet-and-confer" in t:
            topics.append("discovery_disputes")
        if "pretrial" in t or "pre-trial" in t:
            topics.append("pretrial")
        if "trial" in t and "pretrial" not in t:
            topics.append("trial")
        if "technology" in t or "elmo" in t or "courtroom technology" in t:
            topics.append("technology")
        if "junior" in t or "newer attorney" in t:
            topics.append("junior_attorney")
        if "settlement" in t:
            topics.append("settlement")
        return sorted(set(topics))

    def build_judge_card(
        self,
        stub: JudgeStub,
        standing_orders: list[StandingOrderRaw],
        proposed_email: Optional[str],
    ) -> tuple[Optional[JudgeCard], ExtractorOutcome]:
        outcome = ExtractorOutcome()
        procedural_kwargs: dict[str, object] = {}
        sources: list[Source] = []
        now = now_iso()

        extracted_email = None
        for so in standing_orders:
            res = EXTRACTORS["proposed_order_email"](so.text)
            if res is not None:
                extracted_email = res
                break

        email_to_use = proposed_email or (
            extracted_email.value if extracted_email is not None else None
        )

        for field_key, fn in EXTRACTORS.items():
            if field_key in {"proposed_order_email", "chambers_email"}:
                continue
            result: Optional[ExtractionResult] = None
            matching_so: Optional[StandingOrderRaw] = None
            for so in standing_orders:
                result = fn(so.text)
                if result is not None:
                    matching_so = so
                    break
            outcome.extracted[field_key] = result
            if result is None:
                continue
            procedural_kwargs[field_key] = result.value
            sources.append(
                Source(
                    field_key=field_key,
                    source_type="standing_order",
                    source_url=matching_so.url if matching_so else None,
                    source_excerpt=result.matched_excerpt,
                    confidence=result.confidence,
                    last_verified_at=now,
                )
            )

        if email_to_use:
            sources.append(
                Source(
                    field_key="proposed_order_email",
                    source_type=(
                        "court_website" if proposed_email else "standing_order"
                    ),
                    source_url=(
                        self.BASE_URL + self.PROPOSED_EMAILS
                        if proposed_email
                        else (extracted_email.matched_excerpt if extracted_email else None)
                    ),
                    source_excerpt=(
                        f"Proposed-orders email listed for {stub.name}"
                        if proposed_email
                        else (extracted_email.matched_excerpt if extracted_email else "")
                    ),
                    confidence="verified" if proposed_email else "auto_extracted",
                    last_verified_at=now,
                )
            )

        parsed = parse_judge_name(stub.name)

        so_models: list[StandingOrder] = []
        for so in standing_orders:
            so_models.append(
                StandingOrder(
                    title=so.title,
                    url=so.url,
                    topics=self._topics_for(so.title, so.text) or None,
                    last_fetched_at=now,
                )
            )

        try:
            card = JudgeCard(
                id=f"{self.JURISDICTION}-{stub.slug}",
                slug=stub.slug,
                name=parsed["name"],
                honorific=parsed["honorific"] or "Hon.",
                jurisdiction=self.JURISDICTION,
                court_name=self.COURT_NAME,
                court_type=self.COURT_TYPE,
                status=stub.status,
                proposed_order_email=email_to_use,
                created_at=now,
                updated_at=now,
                standing_orders=so_models,
                procedural=Procedural(**procedural_kwargs),
                sources=sources,
            )
        except Exception as e:
            log.error("could not build card for %s: %s", stub.name, e)
            return None, outcome

        return card, outcome

    def run(self) -> ScrapeReport:
        report = ScrapeReport()
        log.info("fetching judges index")
        stubs = self.get_judge_index()
        if self.only_slug:
            stubs = [s for s in stubs if s.slug == self.only_slug]
        report.judges_found = len(stubs)

        log.info("fetching chambers-rules page")
        chambers_rules = self.fetch_chambers_rules()
        log.info("fetching proposed-orders emails page")
        proposed_emails = self.fetch_proposed_emails()

        if not self.dry_run:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        for stub in stubs:
            log.info("scraping %s", stub.name)
            pdf_links = chambers_rules.get(stub.slug, [])
            standing_orders = self.fetch_standing_orders(pdf_links)
            card, outcome = self.build_judge_card(
                stub, standing_orders, proposed_email=proposed_emails.get(stub.slug)
            )

            per_judge = JudgeReport(
                slug=stub.slug,
                name=stub.name,
                status=stub.status,
                written=False,
                extractor_hits=outcome.hit_keys(),
                standing_orders_found=len(standing_orders),
            )

            if card is None:
                per_judge.skip_reason = "card construction failed"
                report.per_judge.append(per_judge)
                log_scrape_event(
                    JURISDICTION_DIR,
                    {
                        "judge": stub.name,
                        "slug": stub.slug,
                        "standing_orders": len(standing_orders),
                        "skip_reason": "card_construction_failed",
                    },
                )
                continue

            errors = card.validate_against_schema(SCHEMA_PATH)
            if errors:
                per_judge.validation_errors = errors
                per_judge.skip_reason = "schema validation failed"
                log.warning("validation failed for %s: %s", stub.name, errors)
                log_scrape_event(
                    JURISDICTION_DIR,
                    {
                        "judge": stub.name,
                        "slug": stub.slug,
                        "standing_orders": len(standing_orders),
                        "validation_errors": errors,
                        "skip_reason": "schema_validation_failed",
                    },
                )
                report.per_judge.append(per_judge)
                continue

            if not self.dry_run:
                out_path = OUTPUT_DIR / f"{stub.slug}.yaml"
                out_path.write_text(_dump_yaml(card.to_schema_dict()))
                per_judge.written = True
                report.cards_written += 1

            log_scrape_event(
                JURISDICTION_DIR,
                {
                    "judge": stub.name,
                    "slug": stub.slug,
                    "standing_orders": len(standing_orders),
                    "extractor_hits": outcome.hit_keys(),
                    "written": per_judge.written,
                },
            )
            report.per_judge.append(per_judge)

        for pj in report.per_judge:
            for key in pj.extractor_hits:
                report.per_field_hits[key] = report.per_field_hits.get(key, 0) + 1

        return report


def _dump_yaml(data: dict) -> str:
    class _IndentDumper(yaml.SafeDumper):
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)

    return yaml.dump(
        data,
        Dumper=_IndentDumper,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )
