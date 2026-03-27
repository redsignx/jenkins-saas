"""
Unit tests for the PricingEngine.
"""
import pytest
from src.models import EC2UsageRecord, MacMiniUsageRecord
from src.pricing import PricingEngine


class TestAnnualQuote:
    """Pro-forma quotes based purely on committed quotas."""

    def test_quote_produces_report_for_each_team(self, engine, quota_file):
        report = engine.annual_quote(quota_file)
        assert len(report.team_reports) == len(quota_file.teams)

    def test_quote_billing_year(self, engine, quota_file):
        report = engine.annual_quote(quota_file)
        assert report.billing_year == 2025

    def test_platform_ec2_charge(self, engine, quota_file):
        """platform team has 50 000 min c5.2xlarge @ $0.02/min + gold 10% disc"""
        report = engine.annual_quote(quota_file)
        tr = next(r for r in report.team_reports if r.team_name == "platform")
        # Find the c5.2xlarge line
        line = next(li for li in tr.line_items if "c5.2xlarge" in li.description)
        assert line.pre_discount_amount == pytest.approx(50_000 * 0.0200)
        assert line.discount_pct == 10
        assert line.net_amount == pytest.approx(50_000 * 0.0200 * 0.90)

    def test_platform_mac_mini_dedicated(self, engine, quota_file):
        """platform team reserved 1 dedicated Mac Mini slot"""
        report = engine.annual_quote(quota_file)
        tr = next(r for r in report.team_reports if r.team_name == "platform")
        line = next(li for li in tr.line_items if "dedicated slot" in li.description)
        assert line.pre_discount_amount == pytest.approx(2400.0)

    def test_frontend_no_mac_mini_dedicated(self, engine, quota_file):
        """frontend team has no dedicated Mac Mini slots."""
        report = engine.annual_quote(quota_file)
        tr = next(r for r in report.team_reports if r.team_name == "frontend")
        dedicated_lines = [li for li in tr.line_items if "dedicated slot" in li.description]
        assert dedicated_lines == []

    def test_frontend_shared_mac_mini(self, engine, quota_file):
        """frontend team has 2 000 shared Mac Mini min @ $0.008/min, bronze 0% disc."""
        report = engine.annual_quote(quota_file)
        tr = next(r for r in report.team_reports if r.team_name == "frontend")
        line = next(li for li in tr.line_items if "Mac Mini shared" in li.description)
        assert line.pre_discount_amount == pytest.approx(2_000 * 0.0080)
        assert line.discount_pct == 0
        assert line.net_amount == pytest.approx(2_000 * 0.0080)

    def test_mobile_ios_platinum_discount(self, engine, quota_file):
        """mobile-ios is on platinum tier (15% discount)."""
        report = engine.annual_quote(quota_file)
        tr = next(r for r in report.team_reports if r.team_name == "mobile-ios")
        assert tr.discount_pct == 15
        for li in tr.line_items:
            assert li.discount_pct == 15

    def test_unknown_instance_type_raises(self, engine, quota_file):
        """An EC2 quota referencing an unknown instance type must fail."""
        from src.models import EC2Quota, TeamQuota
        bad_quota = quota_file
        bad_quota.teams[0].ec2_quotas.append(
            EC2Quota(instance_type="z9.superlarge", annual_minutes=1000)
        )
        with pytest.raises(ValueError, match="z9.superlarge"):
            engine.annual_quote(bad_quota)


class TestAnnualBilling:
    """Final billing with actual usage data."""

    def test_no_overage_when_usage_within_quota(self, engine, quota_file):
        """When actual == committed, there should be zero overage."""
        ec2_usage = [
            EC2UsageRecord(team="backend", instance_type="t3.xlarge", actual_minutes=40_000),
        ]
        report = engine.annual_billing(quota_file, ec2_usage, [])
        tr = next(r for r in report.team_reports if r.team_name == "backend")
        line = next(li for li in tr.line_items if "t3.xlarge" in li.description)
        assert line.overage_minutes == pytest.approx(0.0)
        assert line.overage_amount == pytest.approx(0.0)

    def test_overage_charged_at_multiplier(self, engine, quota_file):
        """10 000 extra minutes should attract a 1.2× penalty."""
        # backend committed 40 000 min t3.xlarge
        extra = 10_000
        ec2_usage = [
            EC2UsageRecord(team="backend", instance_type="t3.xlarge", actual_minutes=50_000),
        ]
        report = engine.annual_billing(quota_file, ec2_usage, [])
        tr = next(r for r in report.team_reports if r.team_name == "backend")
        line = next(li for li in tr.line_items if "t3.xlarge" in li.description)
        expected_overage = extra * 0.0110 * 1.20
        assert line.overage_minutes == pytest.approx(10_000)
        assert line.overage_amount == pytest.approx(expected_overage)

    def test_mac_mini_shared_overage(self, engine, quota_file):
        """frontend team committed 2 000 shared min; actual 3 000 → 1 000 min overage."""
        mac_usage = [MacMiniUsageRecord(team="frontend", actual_minutes=3_000)]
        report = engine.annual_billing(quota_file, [], mac_usage)
        tr = next(r for r in report.team_reports if r.team_name == "frontend")
        line = next(li for li in tr.line_items if "Mac Mini shared" in li.description)
        assert line.overage_minutes == pytest.approx(1_000)
        assert line.overage_amount == pytest.approx(1_000 * 0.0080 * 1.20)

    def test_team_with_no_actual_usage_pays_commitment(self, engine, quota_file):
        """A team that ran zero builds still pays for what they committed."""
        report = engine.annual_billing(quota_file, [], [])
        tr = next(r for r in report.team_reports if r.team_name == "data-engineering")
        assert tr.total_net > 0

    def test_unplanned_instance_type_in_usage(self, engine, quota_file):
        """Usage on an instance type not in the quota should generate an overage-only line."""
        ec2_usage = [
            EC2UsageRecord(team="frontend", instance_type="c5.2xlarge", actual_minutes=500),
        ]
        report = engine.annual_billing(quota_file, ec2_usage, [])
        tr = next(r for r in report.team_reports if r.team_name == "frontend")
        line = next(li for li in tr.line_items if "c5.2xlarge" in li.description)
        # Committed 0 min → all 500 min are overage
        assert line.quota_minutes == pytest.approx(0.0)
        assert line.overage_minutes == pytest.approx(500.0)

    def test_total_net_is_sum_of_lines(self, engine, quota_file):
        report = engine.annual_quote(quota_file)
        for tr in report.team_reports:
            expected = sum(li.net_amount + li.overage_amount for li in tr.line_items)
            assert tr.total_net == pytest.approx(expected)


class TestDiscountCalculation:
    def test_zero_discount_bronze(self, engine, quota_file):
        report = engine.annual_quote(quota_file)
        tr = next(r for r in report.team_reports if r.team_name == "frontend")
        assert tr.discount_pct == 0
        for li in tr.line_items:
            assert li.discount_amount == pytest.approx(0.0)
            assert li.net_amount == pytest.approx(li.pre_discount_amount)

    def test_silver_5pct_discount(self, engine, quota_file):
        report = engine.annual_quote(quota_file)
        tr = next(r for r in report.team_reports if r.team_name == "backend")
        assert tr.discount_pct == 5
        for li in tr.line_items:
            assert li.net_amount == pytest.approx(li.pre_discount_amount * 0.95, rel=1e-4)
