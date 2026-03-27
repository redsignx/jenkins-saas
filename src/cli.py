"""
jenkins_billing – command-line interface.

Commands
────────
  quote   Generate a pro-forma annual invoice from quota commitments alone.
          Use this at year-end to tell each team what they'll owe next year.

  bill    Generate the final annual billing report with actual usage data.
          Use this after the year ends or for a mid-year true-up.

Examples
────────
  # Year-end planning: generate 2025 quotes for all teams
  jenkins-billing quote --pricing config/pricing.yaml --quotas config/quotas_2025.yaml

  # Generate quote for a single team
  jenkins-billing quote --pricing config/pricing.yaml --quotas config/quotas_2025.yaml --team mobile-ios

  # Final billing with actual Jenkins usage (queries live Jenkins API)
  jenkins-billing bill --pricing config/pricing.yaml --quotas config/quotas_2025.yaml

  # Output as CSV instead of plain text
  jenkins-billing quote --pricing config/pricing.yaml --quotas config/quotas_2025.yaml --format csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config_loader import load_pricing, load_quotas
from .models import AnnualQuotaFile, EC2UsageRecord, MacMiniUsageRecord
from .pricing import PricingEngine
from .reports import render_csv, render_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jenkins-billing",
        description="Jenkins SaaS annual billing tool",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--pricing",
        type=Path,
        default=Path("config/pricing.yaml"),
        help="Path to pricing.yaml (default: config/pricing.yaml)",
    )
    shared.add_argument(
        "--quotas",
        type=Path,
        required=True,
        help="Path to quotas_<year>.yaml",
    )
    shared.add_argument(
        "--team",
        default=None,
        help="Restrict output to a single team name",
    )
    shared.add_argument(
        "--format",
        choices=["text", "csv"],
        default="text",
        help="Output format (default: text)",
    )
    shared.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write output to this file instead of stdout",
    )

    # quote sub-command
    sub.add_parser(
        "quote",
        parents=[shared],
        help="Generate a pro-forma annual quote from committed quotas",
    )

    # bill sub-command
    bill_p = sub.add_parser(
        "bill",
        parents=[shared],
        help="Generate final billing report with actual usage from Jenkins",
    )
    bill_p.add_argument(
        "--jenkins-url",
        default=None,
        help="Jenkins base URL (overrides JENKINS_URL env var)",
    )

    return parser


def _filter_teams(report, team_filter: str | None):
    if team_filter:
        report.team_reports = [
            tr for tr in report.team_reports if tr.team_name == team_filter
        ]
    return report


def cmd_quote(args: argparse.Namespace) -> int:
    pricing = load_pricing(args.pricing)
    quotas = load_quotas(args.quotas)
    engine = PricingEngine(pricing)
    report = engine.annual_quote(quotas)
    report = _filter_teams(report, args.team)

    _write_report(report, args.format, args.output)
    return 0


def cmd_bill(args: argparse.Namespace) -> int:
    import os

    pricing = load_pricing(args.pricing)
    quotas = load_quotas(args.quotas)

    # Override JENKINS_URL if provided on command line
    if args.jenkins_url:
        os.environ["JENKINS_URL"] = args.jenkins_url

    from datetime import date

    from .usage_collector import JenkinsClient, collect_usage

    client = JenkinsClient.from_env()
    start = date(quotas.billing_year, 1, 1)
    end = date(quotas.billing_year, 12, 31)
    team_names = [t.name for t in quotas.teams]

    print(f"Collecting Jenkins usage for {quotas.billing_year}…", file=sys.stderr)
    ec2_records, mac_records = collect_usage(client, team_names, start, end)

    engine = PricingEngine(pricing)
    report = engine.annual_billing(quotas, ec2_records, mac_records)
    report = _filter_teams(report, args.team)

    _write_report(report, args.format, args.output)
    return 0


def _write_report(report, fmt: str, output_path: Path | None) -> None:
    import io

    buf = io.StringIO()
    if fmt == "csv":
        render_csv(report, buf)
    else:
        render_text(report, buf)

    content = buf.getvalue()
    if output_path:
        output_path.write_text(content, encoding="utf-8")
        print(f"Report written to {output_path}", file=sys.stderr)
    else:
        sys.stdout.write(content)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "quote":
        return cmd_quote(args)
    if args.command == "bill":
        return cmd_bill(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
