"""
Jenkins API usage collector.

Queries the Jenkins REST API to tally build-minutes consumed by each team
during a given date range.  Teams are identified by the Jenkins *folder* or
*label* that matches a team name in the quota file.

Authentication
──────────────
Set the following environment variables before running:
  JENKINS_URL      – base URL, e.g. https://jenkins.example.com
  JENKINS_USER     – Jenkins username
  JENKINS_API_TOKEN – Jenkins API token (preferred over password)
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Sequence

import requests
from requests.auth import HTTPBasicAuth

from .models import EC2UsageRecord, MacMiniUsageRecord

logger = logging.getLogger(__name__)

# Jenkins label convention used to tag which instance type a build ran on.
# Agents should be labelled like "ec2-t3.large" or "mac-mini".
EC2_LABEL_PREFIX = "ec2-"
MAC_MINI_LABEL = "mac-mini"


class JenkinsClient:
    """Thin wrapper around the Jenkins JSON API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._auth = HTTPBasicAuth(username, api_token)
        self._timeout = timeout
        self._session = requests.Session()
        self._session.auth = self._auth

    @classmethod
    def from_env(cls) -> "JenkinsClient":
        """Construct a client from environment variables."""
        url = os.environ["JENKINS_URL"]
        user = os.environ["JENKINS_USER"]
        token = os.environ["JENKINS_API_TOKEN"]
        return cls(url, user, token)

    def get_json(self, path: str, **params: Any) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}/api/json"
        resp = self._session.get(url, params=params, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    def iter_top_level_jobs(self) -> Iterator[Dict[str, Any]]:
        """Yield each top-level job or folder descriptor."""
        data = self.get_json("/", tree="jobs[name,url,_class]")
        yield from data.get("jobs", [])

    def iter_builds_for_job(self, job_url: str) -> Iterator[Dict[str, Any]]:
        """Yield build descriptors for a given job URL."""
        path = job_url.replace(self.base_url, "").rstrip("/")
        data = self.get_json(
            path,
            tree=(
                "builds[number,result,duration,timestamp,"
                "builtOn,actions[causes[upstreamProject]]]"
            ),
        )
        yield from data.get("builds", [])


def _ms_to_minutes(ms: float) -> float:
    return ms / 60_000.0


def _build_date(timestamp_ms: int) -> date:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date()


def collect_usage(
    client: JenkinsClient,
    team_names: Sequence[str],
    start_date: date,
    end_date: date,
) -> tuple[List[EC2UsageRecord], List[MacMiniUsageRecord]]:
    """
    Walk all Jenkins jobs under each team's top-level folder and aggregate
    build durations into :class:`EC2UsageRecord` and
    :class:`MacMiniUsageRecord` objects.

    The convention assumed here is:
    - Each team owns a *Jenkins Folder* whose name exactly matches the team
      name in the quota file (e.g. ``platform``, ``mobile-ios``).
    - Each agent node is labelled with one of:
        ``ec2-<instance_type>``  (e.g. ``ec2-c5.2xlarge``)
        ``mac-mini``

    Parameters
    ----------
    client      : authenticated Jenkins client
    team_names  : team identifiers to collect usage for
    start_date  : first day of the range (inclusive)
    end_date    : last day of the range (inclusive)

    Returns
    -------
    (ec2_records, mac_records) – one record per (team, instance_type) and
    one record per team with Mac Mini usage.
    """
    ec2_minutes: Dict[str, Dict[str, float]] = {}   # team -> instance_type -> minutes
    mac_minutes: Dict[str, float] = {}               # team -> minutes

    team_set = set(team_names)

    for job in client.iter_top_level_jobs():
        team = job.get("name", "")
        if team not in team_set:
            continue

        try:
            builds = list(client.iter_builds_for_job(job["url"]))
        except Exception as exc:
            logger.warning("Could not retrieve builds for %s: %s", team, exc)
            continue

        for build in builds:
            ts = build.get("timestamp", 0)
            if not ts:
                continue
            build_date = _build_date(ts)
            if not (start_date <= build_date <= end_date):
                continue
            if build.get("result") not in {"SUCCESS", "FAILURE", "UNSTABLE", "ABORTED"}:
                # Skip builds that never finished
                continue

            duration_min = _ms_to_minutes(build.get("duration", 0))
            agent_name: str = build.get("builtOn", "") or ""

            if agent_name.startswith(EC2_LABEL_PREFIX):
                instance_type = agent_name[len(EC2_LABEL_PREFIX):]
                ec2_minutes.setdefault(team, {}).setdefault(instance_type, 0.0)
                ec2_minutes[team][instance_type] += duration_min
            elif agent_name == MAC_MINI_LABEL:
                mac_minutes[team] = mac_minutes.get(team, 0.0) + duration_min
            else:
                logger.debug(
                    "Build %s for team %s ran on unknown agent %r – skipped",
                    build.get("number"),
                    team,
                    agent_name,
                )

    ec2_records: List[EC2UsageRecord] = [
        EC2UsageRecord(team=team, instance_type=itype, actual_minutes=mins)
        for team, itype_map in ec2_minutes.items()
        for itype, mins in itype_map.items()
    ]
    mac_records: List[MacMiniUsageRecord] = [
        MacMiniUsageRecord(team=team, actual_minutes=mins)
        for team, mins in mac_minutes.items()
    ]
    return ec2_records, mac_records
