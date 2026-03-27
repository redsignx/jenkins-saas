"""
Shared pytest fixtures for the jenkins-billing test suite.
"""
import pytest
from pathlib import Path

from src.config_loader import load_pricing, load_quotas
from src.pricing import PricingEngine

# Resolve paths relative to the repository root
REPO_ROOT = Path(__file__).parent.parent
PRICING_PATH = REPO_ROOT / "config" / "pricing.yaml"
QUOTAS_PATH = REPO_ROOT / "config" / "quotas_2025.yaml"


@pytest.fixture(scope="session")
def pricing_catalogue():
    return load_pricing(PRICING_PATH)


@pytest.fixture
def quota_file():
    """Return a fresh quota file for each test (mutable)."""
    return load_quotas(QUOTAS_PATH)


@pytest.fixture(scope="session")
def engine(pricing_catalogue):
    return PricingEngine(pricing_catalogue)


@pytest.fixture
def annual_report(engine, quota_file):
    """A pre-generated annual quote report for use in renderer tests."""
    return engine.annual_quote(quota_file)
