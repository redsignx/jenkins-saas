"""
Pricing engine: calculates annual quotes and team billing reports.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Sequence

from .models import (
    AnnualBillingReport,
    AnnualQuotaFile,
    BillingLineItem,
    CommitmentTier,
    EC2UsageRecord,
    MacMiniUsageRecord,
    PricingCatalogue,
    TeamBillingReport,
    TeamQuota,
)


def _apply_discount(amount: float, discount_pct: float) -> tuple[float, float]:
    """Return (discount_amount, net_amount) for a given pre-discount amount."""
    discount = round(amount * discount_pct / 100, 4)
    net = round(amount - discount, 4)
    return discount, net


class PricingEngine:
    """
    Calculates annual billing for each team.

    Usage workflow
    ──────────────
    1. **Annual quote** (year-end planning):
       Call :meth:`annual_quote` with the quota file and pricing catalogue
       to produce a pro-forma invoice for every team, based solely on their
       pre-committed quotas.  No actual usage data is needed.

    2. **Year-end true-up** (after the year ends):
       Call :meth:`annual_billing` with the quota file, pricing catalogue,
       and actual usage records.  The engine charges the committed amounts
       plus any overage at the penalty rate.
    """

    def __init__(self, catalogue: PricingCatalogue) -> None:
        self.catalogue = catalogue

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def annual_quote(self, quotas: AnnualQuotaFile) -> AnnualBillingReport:
        """
        Generate a pro-forma annual billing report based purely on committed
        quotas (no actual usage required).  Used for year-end budget planning.
        """
        team_reports = [
            self._quote_team(tq, quotas.billing_year)
            for tq in quotas.teams
        ]
        return AnnualBillingReport(
            billing_year=quotas.billing_year,
            generated_on=date.today(),
            team_reports=team_reports,
        )

    def annual_billing(
        self,
        quotas: AnnualQuotaFile,
        ec2_usage: Sequence[EC2UsageRecord],
        mac_usage: Sequence[MacMiniUsageRecord],
    ) -> AnnualBillingReport:
        """
        Generate the final annual billing report with actual usage.
        Overage charges are added for any usage beyond committed quotas.
        """
        # Index usage by team
        ec2_by_team: Dict[str, Dict[str, float]] = {}
        for rec in ec2_usage:
            ec2_by_team.setdefault(rec.team, {})[rec.instance_type] = (
                ec2_by_team.get(rec.team, {}).get(rec.instance_type, 0.0)
                + rec.actual_minutes
            )

        mac_by_team: Dict[str, float] = {}
        for rec in mac_usage:
            mac_by_team[rec.team] = mac_by_team.get(rec.team, 0.0) + rec.actual_minutes

        team_reports = [
            self._bill_team(
                tq,
                quotas.billing_year,
                ec2_by_team.get(tq.name, {}),
                mac_by_team.get(tq.name, 0.0),
            )
            for tq in quotas.teams
        ]
        return AnnualBillingReport(
            billing_year=quotas.billing_year,
            generated_on=date.today(),
            team_reports=team_reports,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_tier(self, tier_name: str) -> CommitmentTier:
        return self.catalogue.tier_for(tier_name)

    def _quote_team(self, tq: TeamQuota, billing_year: int) -> TeamBillingReport:
        """Build a pro-forma report based on committed quotas only."""
        tier = self._resolve_tier(tq.commitment_tier)
        line_items = []

        # EC2 lines
        for eq in tq.ec2_quotas:
            rate = self.catalogue.ec2_rates.get(eq.instance_type)
            if rate is None:
                raise ValueError(
                    f"No pricing found for EC2 instance type {eq.instance_type!r}"
                )
            pre = round(eq.annual_minutes * rate.rate_per_minute, 4)
            disc, net = _apply_discount(pre, tier.discount_pct)
            line_items.append(
                BillingLineItem(
                    description=f"EC2 {eq.instance_type} – pre-committed {eq.annual_minutes:,} min",
                    quota_minutes=float(eq.annual_minutes),
                    actual_minutes=None,
                    unit_rate=rate.rate_per_minute,
                    pre_discount_amount=pre,
                    discount_pct=tier.discount_pct,
                    discount_amount=disc,
                    net_amount=net,
                )
            )

        # Mac Mini dedicated slots
        mm_quota = tq.mac_mini_quota
        mmr = self.catalogue.mac_mini_rate
        if mm_quota.dedicated_slots > 0:
            pre = round(mm_quota.dedicated_slots * mmr.dedicated_slot_annual, 4)
            disc, net = _apply_discount(pre, tier.discount_pct)
            line_items.append(
                BillingLineItem(
                    description=f"Mac Mini – {mm_quota.dedicated_slots} dedicated slot(s) (annual)",
                    quota_minutes=None,
                    actual_minutes=None,
                    unit_rate=None,
                    pre_discount_amount=pre,
                    discount_pct=tier.discount_pct,
                    discount_amount=disc,
                    net_amount=net,
                )
            )

        # Mac Mini shared pool minutes
        if mm_quota.shared_annual_minutes > 0:
            pre = round(mm_quota.shared_annual_minutes * mmr.shared_rate_per_minute, 4)
            disc, net = _apply_discount(pre, tier.discount_pct)
            line_items.append(
                BillingLineItem(
                    description=f"Mac Mini shared – pre-committed {mm_quota.shared_annual_minutes:,} min",
                    quota_minutes=float(mm_quota.shared_annual_minutes),
                    actual_minutes=None,
                    unit_rate=mmr.shared_rate_per_minute,
                    pre_discount_amount=pre,
                    discount_pct=tier.discount_pct,
                    discount_amount=disc,
                    net_amount=net,
                )
            )

        return TeamBillingReport(
            billing_year=billing_year,
            team_name=tq.name,
            commitment_tier=tq.commitment_tier,
            discount_pct=tier.discount_pct,
            line_items=line_items,
        )

    def _bill_team(
        self,
        tq: TeamQuota,
        billing_year: int,
        ec2_actual: Dict[str, float],
        mac_actual_minutes: float,
    ) -> TeamBillingReport:
        """Build the final report combining committed quotas with actual usage."""
        tier = self._resolve_tier(tq.commitment_tier)
        line_items = []
        cat = self.catalogue

        # EC2 lines
        # Collect all instance types mentioned in quota OR actual usage
        all_instance_types = set(eq.instance_type for eq in tq.ec2_quotas) | set(ec2_actual.keys())
        quota_map = {eq.instance_type: eq.annual_minutes for eq in tq.ec2_quotas}

        for itype in sorted(all_instance_types):
            rate = cat.ec2_rates.get(itype)
            if rate is None:
                raise ValueError(f"No pricing found for EC2 instance type {itype!r}")

            committed_min = float(quota_map.get(itype, 0))
            actual_min = ec2_actual.get(itype, 0.0)
            overage_min = max(0.0, actual_min - committed_min)

            pre = round(committed_min * rate.rate_per_minute, 4)
            disc, net = _apply_discount(pre, tier.discount_pct)
            overage_amt = round(
                overage_min * rate.rate_per_minute * cat.overage_multiplier, 4
            )

            label = f"EC2 {itype} – committed {committed_min:,.0f} min / actual {actual_min:,.1f} min"
            line_items.append(
                BillingLineItem(
                    description=label,
                    quota_minutes=committed_min,
                    actual_minutes=actual_min,
                    unit_rate=rate.rate_per_minute,
                    pre_discount_amount=pre,
                    discount_pct=tier.discount_pct,
                    discount_amount=disc,
                    net_amount=net,
                    overage_minutes=overage_min,
                    overage_amount=overage_amt,
                )
            )

        # Mac Mini dedicated slots (fixed annual; no overage concept)
        mm_quota = tq.mac_mini_quota
        mmr = cat.mac_mini_rate
        if mm_quota.dedicated_slots > 0:
            pre = round(mm_quota.dedicated_slots * mmr.dedicated_slot_annual, 4)
            disc, net = _apply_discount(pre, tier.discount_pct)
            line_items.append(
                BillingLineItem(
                    description=f"Mac Mini – {mm_quota.dedicated_slots} dedicated slot(s) (annual)",
                    quota_minutes=None,
                    actual_minutes=None,
                    unit_rate=None,
                    pre_discount_amount=pre,
                    discount_pct=tier.discount_pct,
                    discount_amount=disc,
                    net_amount=net,
                )
            )

        # Mac Mini shared pool
        committed_mm_shared = float(mm_quota.shared_annual_minutes)
        overage_mm = max(0.0, mac_actual_minutes - committed_mm_shared)

        if committed_mm_shared > 0 or mac_actual_minutes > 0:
            pre = round(committed_mm_shared * mmr.shared_rate_per_minute, 4)
            disc, net = _apply_discount(pre, tier.discount_pct)
            overage_amt = round(
                overage_mm * mmr.shared_rate_per_minute * cat.overage_multiplier, 4
            )
            line_items.append(
                BillingLineItem(
                    description=(
                        f"Mac Mini shared – committed {committed_mm_shared:,.0f} min"
                        f" / actual {mac_actual_minutes:,.1f} min"
                    ),
                    quota_minutes=committed_mm_shared,
                    actual_minutes=mac_actual_minutes,
                    unit_rate=mmr.shared_rate_per_minute,
                    pre_discount_amount=pre,
                    discount_pct=tier.discount_pct,
                    discount_amount=disc,
                    net_amount=net,
                    overage_minutes=overage_mm,
                    overage_amount=overage_amt,
                )
            )

        return TeamBillingReport(
            billing_year=billing_year,
            team_name=tq.name,
            commitment_tier=tq.commitment_tier,
            discount_pct=tier.discount_pct,
            line_items=line_items,
        )
