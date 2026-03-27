"""
Report renderer: formats annual billing reports as plain text or CSV.
"""
from __future__ import annotations

import csv
import io
import textwrap
from typing import IO, Optional

from .models import AnnualBillingReport, TeamBillingReport


# ---------------------------------------------------------------------------
# Plain-text renderer
# ---------------------------------------------------------------------------

_SEP = "─" * 80


def render_text(report: AnnualBillingReport, out: IO[str]) -> None:
    """Write a human-readable billing summary to *out*."""
    out.write(f"\n{'Jenkins SaaS Annual Billing Report':^80}\n")
    out.write(f"{'Year: ' + str(report.billing_year):^80}\n")
    out.write(f"{'Generated: ' + str(report.generated_on):^80}\n")
    out.write(_SEP + "\n\n")

    for tr in report.team_reports:
        _render_team_text(tr, out)
        out.write("\n")

    out.write(_SEP + "\n")
    out.write(f"GRAND TOTAL (all teams)  :  ${report.grand_total:>12,.2f}\n")
    out.write(_SEP + "\n")


def _render_team_text(tr: TeamBillingReport, out: IO[str]) -> None:
    out.write(f"Team : {tr.team_name}\n")
    out.write(f"Tier : {tr.commitment_tier}  ({tr.discount_pct:.0f}% discount)\n")
    out.write(_SEP + "\n")
    out.write(
        f"{'Description':<48} {'Quota min':>10} {'Actual min':>10}"
        f" {'Rate':>8} {'Amount':>10} {'Disc':>6} {'Net':>10}\n"
    )
    out.write(_SEP + "\n")

    for li in tr.line_items:
        quota_str = f"{li.quota_minutes:>10,.0f}" if li.quota_minutes is not None else f"{'—':>10}"
        actual_str = (
            f"{li.actual_minutes:>10,.1f}" if li.actual_minutes is not None else f"{'—':>10}"
        )
        rate_str = f"{li.unit_rate:>8.4f}" if li.unit_rate is not None else f"{'fixed':>8}"
        desc = textwrap.shorten(li.description, width=48, placeholder="…")

        out.write(
            f"{desc:<48} {quota_str} {actual_str} {rate_str}"
            f" ${li.pre_discount_amount:>9,.2f}"
            f" {li.discount_pct:>5.0f}%"
            f" ${li.net_amount:>9,.2f}\n"
        )
        if li.overage_minutes > 0:
            out.write(
                f"  {'↳ Overage':46} {li.overage_minutes:>10,.1f}"
                f" {'':>10} {'':>8}"
                f" {'':>10} {'':>6}"
                f" ${li.overage_amount:>9,.2f}\n"
            )

    out.write(_SEP + "\n")
    out.write(
        f"{'Sub-total (pre-discount)':>76} ${tr.total_pre_discount:>9,.2f}\n"
    )
    out.write(
        f"{'Commitment discount':>76} ${tr.total_discount:>9,.2f}\n"
    )
    if tr.total_overage:
        out.write(
            f"{'Overage charges':>76} ${tr.total_overage:>9,.2f}\n"
        )
    out.write(
        f"{'TOTAL DUE':>76} ${tr.total_net:>9,.2f}\n"
    )
    out.write(_SEP + "\n")


# ---------------------------------------------------------------------------
# CSV renderer
# ---------------------------------------------------------------------------

CSV_HEADERS = [
    "billing_year",
    "team",
    "commitment_tier",
    "discount_pct",
    "description",
    "quota_minutes",
    "actual_minutes",
    "unit_rate",
    "pre_discount_amount",
    "discount_amount",
    "net_amount",
    "overage_minutes",
    "overage_amount",
    "line_total",
]


def render_csv(report: AnnualBillingReport, out: IO[str]) -> None:
    """Write a machine-readable CSV of all line items to *out*."""
    writer = csv.DictWriter(out, fieldnames=CSV_HEADERS, lineterminator="\n")
    writer.writeheader()

    for tr in report.team_reports:
        for li in tr.line_items:
            writer.writerow(
                {
                    "billing_year": report.billing_year,
                    "team": tr.team_name,
                    "commitment_tier": tr.commitment_tier,
                    "discount_pct": tr.discount_pct,
                    "description": li.description,
                    "quota_minutes": li.quota_minutes if li.quota_minutes is not None else "",
                    "actual_minutes": li.actual_minutes if li.actual_minutes is not None else "",
                    "unit_rate": li.unit_rate if li.unit_rate is not None else "",
                    "pre_discount_amount": li.pre_discount_amount,
                    "discount_amount": li.discount_amount,
                    "net_amount": li.net_amount,
                    "overage_minutes": li.overage_minutes,
                    "overage_amount": li.overage_amount,
                    "line_total": round(li.net_amount + li.overage_amount, 4),
                }
            )
