"""
Unit tests for the usage collector.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from src.usage_collector import (
    EC2_LABEL_PREFIX,
    MAC_MINI_LABEL,
    _ms_to_minutes,
    _build_date,
    collect_usage,
)


class TestHelpers:
    def test_ms_to_minutes(self):
        assert _ms_to_minutes(60_000) == pytest.approx(1.0)
        assert _ms_to_minutes(0) == pytest.approx(0.0)
        assert _ms_to_minutes(90_000) == pytest.approx(1.5)

    def test_build_date(self):
        # 2025-06-15 12:00 UTC in milliseconds
        ts = 1750003200000
        d = _build_date(ts)
        assert isinstance(d, date)


class TestCollectUsage:
    """Tests for the collect_usage function using a mock JenkinsClient."""

    def _mock_client(self, jobs, builds_per_job):
        client = MagicMock()
        client.iter_top_level_jobs.return_value = iter(jobs)
        client.iter_builds_for_job.side_effect = lambda url: iter(builds_per_job.get(url, []))
        return client

    def _ts_for_date(self, d: date) -> int:
        """Return a millisecond timestamp for noon UTC on the given date."""
        from datetime import datetime, timezone
        dt = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)

    def test_ec2_usage_aggregated(self):
        in_range_ts = self._ts_for_date(date(2025, 6, 15))
        jobs = [{"name": "platform", "url": "http://jenkins/job/platform/"}]
        builds = {
            "http://jenkins/job/platform/": [
                {"number": 1, "result": "SUCCESS", "duration": 120_000,
                 "timestamp": in_range_ts, "builtOn": "ec2-c5.2xlarge"},
                {"number": 2, "result": "SUCCESS", "duration": 60_000,
                 "timestamp": in_range_ts, "builtOn": "ec2-c5.2xlarge"},
            ]
        }
        client = self._mock_client(jobs, builds)
        ec2, mac = collect_usage(client, ["platform"], date(2025, 1, 1), date(2025, 12, 31))

        assert len(ec2) == 1
        assert ec2[0].team == "platform"
        assert ec2[0].instance_type == "c5.2xlarge"
        assert ec2[0].actual_minutes == pytest.approx(3.0)
        assert mac == []

    def test_mac_mini_usage_aggregated(self):
        ts = self._ts_for_date(date(2025, 3, 1))
        jobs = [{"name": "mobile-ios", "url": "http://jenkins/job/mobile-ios/"}]
        builds = {
            "http://jenkins/job/mobile-ios/": [
                {"number": 10, "result": "SUCCESS", "duration": 300_000,
                 "timestamp": ts, "builtOn": MAC_MINI_LABEL},
            ]
        }
        client = self._mock_client(jobs, builds)
        ec2, mac = collect_usage(client, ["mobile-ios"], date(2025, 1, 1), date(2025, 12, 31))

        assert ec2 == []
        assert len(mac) == 1
        assert mac[0].team == "mobile-ios"
        assert mac[0].actual_minutes == pytest.approx(5.0)

    def test_builds_outside_range_excluded(self):
        in_range_ts = self._ts_for_date(date(2025, 6, 1))
        out_range_ts = self._ts_for_date(date(2024, 12, 31))  # prior year
        jobs = [{"name": "backend", "url": "http://jenkins/job/backend/"}]
        builds = {
            "http://jenkins/job/backend/": [
                {"number": 1, "result": "SUCCESS", "duration": 60_000,
                 "timestamp": in_range_ts, "builtOn": "ec2-t3.xlarge"},
                {"number": 2, "result": "SUCCESS", "duration": 60_000,
                 "timestamp": out_range_ts, "builtOn": "ec2-t3.xlarge"},
            ]
        }
        client = self._mock_client(jobs, builds)
        ec2, _ = collect_usage(client, ["backend"], date(2025, 1, 1), date(2025, 12, 31))
        assert ec2[0].actual_minutes == pytest.approx(1.0)  # only the in-range build

    def test_unknown_team_skipped(self):
        jobs = [{"name": "some-other-team", "url": "http://jenkins/job/other/"}]
        client = self._mock_client(jobs, {})
        ec2, mac = collect_usage(client, ["platform"], date(2025, 1, 1), date(2025, 12, 31))
        assert ec2 == []
        assert mac == []

    def test_in_progress_builds_excluded(self):
        ts = self._ts_for_date(date(2025, 6, 1))
        jobs = [{"name": "frontend", "url": "http://jenkins/job/frontend/"}]
        builds = {
            "http://jenkins/job/frontend/": [
                # result=None means still running
                {"number": 99, "result": None, "duration": 999_000,
                 "timestamp": ts, "builtOn": "ec2-t3.medium"},
            ]
        }
        client = self._mock_client(jobs, builds)
        ec2, _ = collect_usage(client, ["frontend"], date(2025, 1, 1), date(2025, 12, 31))
        assert ec2 == []
