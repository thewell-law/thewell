"""Command-line entry for the CASD scraper."""

from __future__ import annotations

import logging
import sys

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from scrapers.casd.scrape import CasdScraper, ScrapeReport


def _print_report(report: ScrapeReport, console: Console) -> None:
    summary = Table(title="S.D. Cal. scrape report", show_lines=False)
    summary.add_column("metric")
    summary.add_column("value", justify="right")
    summary.add_row("judges found", str(report.judges_found))
    summary.add_row("cards written", str(report.cards_written))
    summary.add_row("cards skipped", str(report.judges_found - report.cards_written))
    console.print(summary)

    if report.per_field_hits:
        hits = Table(title="Extractor hit rates (field -> # judges)")
        hits.add_column("field_key")
        hits.add_column("hits", justify="right")
        hits.add_column("coverage", justify="right")
        denom = max(report.judges_found, 1)
        for key, count in sorted(report.per_field_hits.items(), key=lambda kv: -kv[1]):
            hits.add_row(key, str(count), f"{count / denom:.0%}")
        console.print(hits)

    failed = [pj for pj in report.per_judge if pj.skip_reason]
    if failed:
        fail = Table(title="Skipped / failed judges")
        fail.add_column("slug")
        fail.add_column("name")
        fail.add_column("reason")
        fail.add_column("errors")
        for pj in failed:
            fail.add_row(
                pj.slug,
                pj.name,
                pj.skip_reason or "",
                ("; ".join(pj.validation_errors))[:300],
            )
        console.print(fail)


@click.command()
@click.option("--dry-run", is_flag=True, help="Run the scraper but do not write any YAMLs.")
@click.option("--rebuild-cache", is_flag=True, help="Ignore the local PDF cache and refetch everything.")
@click.option("--judge", "judge_slug", default=None, help="Only scrape this judge (match on slug).")
@click.option("--verbose", "-v", is_flag=True, help="Log every fetch and extractor firing.")
def main(dry_run: bool, rebuild_cache: bool, judge_slug: str | None, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_time=True, show_path=False)],
    )
    console = Console()

    scraper = CasdScraper(
        dry_run=dry_run,
        rebuild_cache=rebuild_cache,
        only_slug=judge_slug,
    )
    try:
        report = scraper.run()
    except Exception:
        console.print_exception()
        sys.exit(1)

    _print_report(report, console)
    if report.cards_written == 0 and report.judges_found > 0 and not dry_run:
        console.print("[yellow]warning: no cards were written.[/yellow]")


if __name__ == "__main__":
    main()
