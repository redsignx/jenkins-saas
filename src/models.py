"""
Data models for the Jenkins SaaS billing system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Pricing catalogue
# ---------------------------------------------------------------------------

@dataclass
class EC2Rate:
    """Per-minute billing rate for one EC2 instance type."""
    instance_type: str
    vcpu: int
    memory_gb: float
    rate_per_minute: float  # USD


@dataclass
class MacMiniRate:
    """Pricing parameters for on-prem Mac Mini agents."""
    dedicated_slot_annual: float    # USD/year per reserved slot
    shared_rate_per_minute: float   # USD/minute for shared pool usage


@dataclass
class CommitmentTier:
    """Annual commitment discount tier."""
    name: str                       # bronze | silver | gold | platinum
    min_annual_usd: float
    discount_pct: float             # 0–100


@dataclass
class PricingCatalogue:
    """Complete pricing configuration for one billing year."""
    schema_version: str
    ec2_rates: Dict[str, EC2Rate]           # keyed by instance_type
    mac_mini_rate: MacMiniRate
    commitment_tiers: List[CommitmentTier]  # sorted ascending by min_annual_usd
    overage_multiplier: float = 1.20

    def tier_for(self, name: str) -> CommitmentTier:
        for t in self.commitment_tiers:
            if t.name == name:
                return t
        raise ValueError(f"Unknown commitment tier: {name!r}")


# ---------------------------------------------------------------------------
# Team quotas (pre-committed at year-end)
# ---------------------------------------------------------------------------

@dataclass
class EC2Quota:
    """Pre-committed build-minutes for one EC2 instance type."""
    instance_type: str
    annual_minutes: int


@dataclass
class MacMiniQuota:
    """Pre-committed Mac Mini usage for a team."""
    dedicated_slots: int        # reserved physical slots (annual fixed charge)
    shared_annual_minutes: int  # shared pool minutes


@dataclass
class TeamQuota:
    """All pre-committed resources for a single team in a given billing year."""
    name: str
    commitment_tier: str
    ec2_quotas: List[EC2Quota] = field(default_factory=list)
    mac_mini_quota: MacMiniQuota = field(default_factory=lambda: MacMiniQuota(0, 0))


@dataclass
class AnnualQuotaFile:
    """Parsed contents of a quotas_<year>.yaml file."""
    schema_version: str
    billing_year: int
    teams: List[TeamQuota]

    def team(self, name: str) -> TeamQuota:
        for t in self.teams:
            if t.name == name:
                return t
        raise KeyError(f"Team {name!r} not found in quota file")


# ---------------------------------------------------------------------------
# Actual usage records (collected from Jenkins)
# ---------------------------------------------------------------------------

@dataclass
class EC2UsageRecord:
    """Actual build-minutes consumed by one team on one EC2 instance type."""
    team: str
    instance_type: str
    actual_minutes: float


@dataclass
class MacMiniUsageRecord:
    """Actual Mac Mini build-minutes consumed by a team (shared pool)."""
    team: str
    actual_minutes: float


# ---------------------------------------------------------------------------
# Billing line items and reports
# ---------------------------------------------------------------------------

@dataclass
class BillingLineItem:
    description: str
    quota_minutes: Optional[float]      # None for fixed charges
    actual_minutes: Optional[float]     # None for fixed charges
    unit_rate: Optional[float]          # USD/minute; None for fixed charges
    pre_discount_amount: float          # USD, before commitment discount
    discount_pct: float
    discount_amount: float              # USD
    net_amount: float                   # USD, after discount
    overage_minutes: float = 0.0
    overage_amount: float = 0.0


@dataclass
class TeamBillingReport:
    """Full billing breakdown for one team in one year."""
    billing_year: int
    team_name: str
    commitment_tier: str
    discount_pct: float
    line_items: List[BillingLineItem] = field(default_factory=list)

    @property
    def total_pre_discount(self) -> float:
        return sum(li.pre_discount_amount for li in self.line_items)

    @property
    def total_discount(self) -> float:
        return sum(li.discount_amount for li in self.line_items)

    @property
    def total_overage(self) -> float:
        return sum(li.overage_amount for li in self.line_items)

    @property
    def total_net(self) -> float:
        return sum(li.net_amount + li.overage_amount for li in self.line_items)


@dataclass
class AnnualBillingReport:
    """Billing report for all teams in one year."""
    billing_year: int
    generated_on: date
    team_reports: List[TeamBillingReport] = field(default_factory=list)

    @property
    def grand_total(self) -> float:
        return sum(r.total_net for r in self.team_reports)
