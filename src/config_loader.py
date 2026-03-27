"""
YAML configuration loaders for pricing catalogue and annual quota files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from .models import (
    AnnualQuotaFile,
    CommitmentTier,
    EC2Quota,
    EC2Rate,
    MacMiniQuota,
    MacMiniRate,
    PricingCatalogue,
    TeamQuota,
)


def load_pricing(path: Path) -> PricingCatalogue:
    """Parse a pricing.yaml file into a :class:`PricingCatalogue`."""
    with open(path, encoding="utf-8") as fh:
        data: Dict[str, Any] = yaml.safe_load(fh)

    ec2_rates: Dict[str, EC2Rate] = {}
    for entry in data.get("ec2_fleet", []):
        rate = EC2Rate(
            instance_type=entry["instance_type"],
            vcpu=entry["vcpu"],
            memory_gb=entry["memory_gb"],
            rate_per_minute=entry["rate_per_minute"],
        )
        ec2_rates[rate.instance_type] = rate

    mm_data = data["mac_mini"]
    mac_mini_rate = MacMiniRate(
        dedicated_slot_annual=mm_data["dedicated_slot_annual"],
        shared_rate_per_minute=mm_data["shared_rate_per_minute"],
    )

    tiers: List[CommitmentTier] = []
    for t in data.get("commitment_tiers", []):
        tiers.append(
            CommitmentTier(
                name=t["name"],
                min_annual_usd=t["min_annual_usd"],
                discount_pct=t["discount_pct"],
            )
        )
    tiers.sort(key=lambda x: x.min_annual_usd)

    return PricingCatalogue(
        schema_version=str(data.get("schema_version", "1.0")),
        ec2_rates=ec2_rates,
        mac_mini_rate=mac_mini_rate,
        commitment_tiers=tiers,
        overage_multiplier=data.get("overage_multiplier", 1.20),
    )


def load_quotas(path: Path) -> AnnualQuotaFile:
    """Parse a quotas_<year>.yaml file into an :class:`AnnualQuotaFile`."""
    with open(path, encoding="utf-8") as fh:
        data: Dict[str, Any] = yaml.safe_load(fh)

    teams: List[TeamQuota] = []
    for team_data in data.get("teams", []):
        ec2_quotas: List[EC2Quota] = [
            EC2Quota(
                instance_type=q["instance_type"],
                annual_minutes=int(q["annual_minutes"]),
            )
            for q in team_data.get("ec2_quotas", [])
        ]

        mm = team_data.get("mac_mini_quota", {})
        mac_mini_quota = MacMiniQuota(
            dedicated_slots=int(mm.get("dedicated_slots", 0)),
            shared_annual_minutes=int(mm.get("shared_annual_minutes", 0)),
        )

        teams.append(
            TeamQuota(
                name=team_data["name"],
                commitment_tier=team_data["commitment_tier"],
                ec2_quotas=ec2_quotas,
                mac_mini_quota=mac_mini_quota,
            )
        )

    return AnnualQuotaFile(
        schema_version=str(data.get("schema_version", "1.0")),
        billing_year=int(data["billing_year"]),
        teams=teams,
    )
