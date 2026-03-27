"""
Unit tests for the config_loader module.
"""
import pytest
from pathlib import Path

from src.config_loader import load_pricing, load_quotas

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadPricing:
    def test_ec2_rates_loaded(self, pricing_catalogue):
        cat = pricing_catalogue
        assert "t3.medium" in cat.ec2_rates
        assert "c5.2xlarge" in cat.ec2_rates

    def test_ec2_rate_values(self, pricing_catalogue):
        rate = pricing_catalogue.ec2_rates["t3.medium"]
        assert rate.vcpu == 2
        assert rate.memory_gb == 4
        assert rate.rate_per_minute == pytest.approx(0.0030)

    def test_mac_mini_rate_loaded(self, pricing_catalogue):
        mmr = pricing_catalogue.mac_mini_rate
        assert mmr.dedicated_slot_annual == pytest.approx(2400.0)
        assert mmr.shared_rate_per_minute == pytest.approx(0.0080)

    def test_commitment_tiers_sorted(self, pricing_catalogue):
        tiers = pricing_catalogue.commitment_tiers
        assert tiers[0].name == "bronze"
        assert tiers[-1].name == "platinum"
        for a, b in zip(tiers, tiers[1:]):
            assert a.min_annual_usd <= b.min_annual_usd

    def test_tier_lookup(self, pricing_catalogue):
        tier = pricing_catalogue.tier_for("gold")
        assert tier.discount_pct == 10

    def test_unknown_tier_raises(self, pricing_catalogue):
        with pytest.raises(ValueError, match="Unknown commitment tier"):
            pricing_catalogue.tier_for("diamond")

    def test_overage_multiplier(self, pricing_catalogue):
        assert pricing_catalogue.overage_multiplier == pytest.approx(1.20)


class TestLoadQuotas:
    def test_teams_loaded(self, quota_file):
        assert len(quota_file.teams) == 5

    def test_billing_year(self, quota_file):
        assert quota_file.billing_year == 2025

    def test_team_lookup(self, quota_file):
        team = quota_file.team("platform")
        assert team.commitment_tier == "gold"

    def test_team_ec2_quotas(self, quota_file):
        team = quota_file.team("platform")
        assert len(team.ec2_quotas) == 2
        itype_map = {q.instance_type: q.annual_minutes for q in team.ec2_quotas}
        assert itype_map["c5.2xlarge"] == 50000

    def test_mac_mini_dedicated_slots(self, quota_file):
        team = quota_file.team("platform")
        assert team.mac_mini_quota.dedicated_slots == 1
        assert team.mac_mini_quota.shared_annual_minutes == 0

    def test_unknown_team_raises(self, quota_file):
        with pytest.raises(KeyError):
            quota_file.team("nonexistent-team")
