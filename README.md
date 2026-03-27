# Jenkins SaaS Billing System

A Python-based annual billing and cost-allocation system for a multi-team Jenkins controller that uses **EC2 Fleet** build agents and **on-prem Mac Mini** iOS build agents.

---

## Problem Statement

You maintain a single Jenkins controller serving many teams. Build agents are:
- **EC2 Fleet** – auto-scaling on-demand agents of various instance types (t3.medium, c5.2xlarge, etc.)
- **Mac Mini (on-prem)** – dedicated iOS build machines shared between teams

Each team needs to be billed annually.  Because team budgets are fixed one year in advance, **teams pre-commit to their resource quotas at the end of the prior year**, and the annual fee is locked in at that point.

---

## Solution Design

### Billing Model

| Concept | Description |
|---|---|
| **Annual pre-commitment** | At year-end, each team declares how many build-minutes they expect to consume per EC2 instance type, and how many Mac Mini slots/minutes they need. |
| **Commitment tier** | The expected annual spend determines a discount tier (Bronze → Silver → Gold → Platinum). Higher tiers unlock larger discounts. |
| **Locked annual fee** | The pre-committed quota × unit rate × (1 − discount) is invoiced as a fixed annual fee, regardless of actual usage. |
| **Overage** | Usage that exceeds the committed quota is billed at `unit_rate × overage_multiplier` (default 1.20×). |
| **Mac Mini dedicated slots** | Teams that need exclusive access reserve a physical slot; this is a fixed annual charge independent of actual usage. |
| **Mac Mini shared pool** | Teams that only occasionally need macOS builds commit to a number of shared build-minutes. |

### Year-end Workflow

```
Year N (October–December)
  │
  ├─ Each team reviews their build usage for year N
  ├─ Team estimates minutes needed for year N+1 per resource type
  ├─ Team selects a commitment tier
  ├─ jenkins-billing quote --quotas config/quotas_{N+1}.yaml
  │    → generates pro-forma invoices for sign-off
  └─ Teams approve and lock their budget

January 1, Year N+1
  └─ Annual fee is invoiced and collected up-front

Year N+1 (ongoing)
  └─ Teams consume their quota; overage is tracked

December 31, Year N+1
  └─ jenkins-billing bill --quotas config/quotas_{N+1}.yaml
       → generates final true-up report (adds overage charges if any)
```

---

## Repository Layout

```
jenkins-saas/
├── config/
│   ├── pricing.yaml          # Unit rates and discount tiers (edit each year)
│   └── quotas_2025.yaml      # Example team commitments for 2025
├── src/
│   ├── models.py             # Dataclasses: PricingCatalogue, TeamQuota, BillingReport, …
│   ├── config_loader.py      # YAML → model parsers
│   ├── pricing.py            # PricingEngine: quote & bill calculations
│   ├── usage_collector.py    # Jenkins REST API usage collector
│   ├── reports.py            # Plain-text and CSV report renderers
│   └── cli.py                # `jenkins-billing` CLI entry point
├── tests/
│   ├── conftest.py           # Shared pytest fixtures
│   ├── test_config_loader.py
│   ├── test_pricing.py
│   ├── test_reports.py
│   └── test_usage_collector.py
├── pyproject.toml
└── README.md
```

---

## Configuration

### `config/pricing.yaml`

Defines unit rates and discount tiers.  Update at year-end before generating quotes.

```yaml
ec2_fleet:
  - instance_type: c5.2xlarge
    vcpu: 8
    memory_gb: 16
    rate_per_minute: 0.0200   # USD/build-minute

mac_mini:
  dedicated_slot_annual: 2400.00   # USD/year per reserved slot
  shared_rate_per_minute: 0.0080   # USD/minute (shared pool)

commitment_tiers:
  - name: bronze
    min_annual_usd: 0
    discount_pct: 0
  - name: silver
    min_annual_usd: 5000
    discount_pct: 5
  - name: gold
    min_annual_usd: 15000
    discount_pct: 10
  - name: platinum
    min_annual_usd: 40000
    discount_pct: 15

overage_multiplier: 1.20
```

### `config/quotas_<year>.yaml`

One file per billing year.  Teams fill this in at year-end.

```yaml
billing_year: 2025

teams:
  - name: mobile-ios
    commitment_tier: platinum
    ec2_quotas:
      - instance_type: t3.medium
        annual_minutes: 20000
    mac_mini_quota:
      dedicated_slots: 2
      shared_annual_minutes: 5000

  - name: backend
    commitment_tier: silver
    ec2_quotas:
      - instance_type: t3.xlarge
        annual_minutes: 40000
    mac_mini_quota:
      dedicated_slots: 0
      shared_annual_minutes: 0
```

---

## Installation

```bash
pip install -e ".[dev]"
```

---

## Usage

### Generate a pro-forma annual quote (year-end planning)

```bash
# All teams
jenkins-billing quote \
  --pricing config/pricing.yaml \
  --quotas  config/quotas_2025.yaml

# Single team, CSV output saved to file
jenkins-billing quote \
  --pricing config/pricing.yaml \
  --quotas  config/quotas_2025.yaml \
  --team    mobile-ios \
  --format  csv \
  --output  reports/mobile-ios-2025-quote.csv
```

### Generate final billing with actual usage (year-end true-up)

Requires the Jenkins REST API to be reachable.  Set these environment variables:

```bash
export JENKINS_URL=https://jenkins.example.com
export JENKINS_USER=my-service-account
export JENKINS_API_TOKEN=11abc...
```

Then:

```bash
jenkins-billing bill \
  --pricing config/pricing.yaml \
  --quotas  config/quotas_2025.yaml
```

**Agent labelling convention** (required for usage collection):
Each Jenkins node must be labelled with one of:
- `ec2-<instance_type>` (e.g. `ec2-c5.2xlarge`, `ec2-t3.large`)
- `mac-mini` (for any Mac Mini node)

And each team must own a **top-level Jenkins Folder** whose name exactly matches the `name` field in the quota file (e.g. a folder called `mobile-ios`).

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Pricing Calculation Examples

### EC2 – no overage

| Input | Value |
|---|---|
| Instance type | `c5.2xlarge` |
| Rate | $0.0200/min |
| Committed minutes | 50,000 |
| Tier | Gold (10% discount) |
| **Annual fee** | 50,000 × $0.02 × 0.90 = **$900.00** |

### Mac Mini – dedicated slot

| Input | Value |
|---|---|
| Slots reserved | 1 |
| Annual slot charge | $2,400 |
| Tier | Gold (10% discount) |
| **Annual fee** | 1 × $2,400 × 0.90 = **$2,160.00** |

### EC2 – overage scenario

| Input | Value |
|---|---|
| Instance type | `t3.xlarge` |
| Rate | $0.0110/min |
| Committed minutes | 40,000 |
| Actual minutes | 50,000 (10,000 over) |
| Overage multiplier | 1.20× |
| Tier | Silver (5% discount) |
| Committed charge | 40,000 × $0.011 × 0.95 = $418.00 |
| Overage charge | 10,000 × $0.011 × 1.20 = $132.00 |
| **Total** | **$550.00** |