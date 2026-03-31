# Dashboard 设计

## 1. Dashboard 整体布局设计

Dashboard 分为两个层级：

1. **全局 Dashboard**（平台团队使用）：所有团队的聚合视图
2. **团队 Dashboard**（各团队自助查看）：仅本团队的详细用量和费用

### 团队 Dashboard 布局（1920×1080 标准分辨率）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  [团队名称] Jenkins Build Dashboard    2024-01-01 ~ 2024-01-31    [月份选择器]    │
├────────────────┬────────────────┬────────────────┬────────────────┬─────────────┤
│  本月总费用      │  EC2 用量      │  Mac Mini 用量  │   构建次数      │  平均等待时间  │
│  $2,213.81     │ 2,847 / 2,000  │  623 / 500 min │  1,134 / 1,000 │  3.2 min    │
│  +$413 超额     │  [■■■■■■□□ 142%]│ [■■■■■□□□ 125%] │ [■■■■■■□□ 113%]│  ✅ SLA OK   │
├────────────────┴────────────────┴────────────────┴────────────────┴─────────────┤
│  构建分钟趋势（30天）                                                               │
│  ████░░░████░░░████░░░████░░░████░░░ ← EC2 分钟                                  │
│  ██░░░░░██░░░░░██░░░░░██░░░░░██░░░░░ ← Mac Mini 分钟                             │
│                                                                                 │
├───────────────────────────────┬─────────────────────────────────────────────────┤
│  资源使用分布                   │  费用分布（饼图）                                   │
│  EC2 Small    ██░░░░░   18%   │       基础费 $1,800 (81%)                        │
│  EC2 Medium   ████████  65%   │     超额费 $413 (19%)                            │
│  EC2 Large    ██░░░░░   17%   │                                                 │
│  Mac Mini M1  ██░░░░░   15%   │                                                 │
│  Mac Mini M2  █████████ 85%   │                                                 │
├───────────────────────────────┴─────────────────────────────────────────────────┤
│  Top 10 构建 Job（按时长排序）                                                       │
│  Job 名称                          构建次数   总时长    平均时长   预估费用              │
│  app-release/main                  234        876 min   3.74 min  $35.04          │
│  app-release/feature-login         189        523 min   2.77 min  $20.92          │
│  ...                                                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  构建成功率分析                 │  队列等待时间分布                                     │
│  SUCCESS  ████████████ 87.3% │  < 1 min   ████████████ 72%                      │
│  FAILURE  ██░░░░░░░░░░  9.2% │  1-5 min   ████░░░░░░░░ 24%                      │
│  UNSTABLE █░░░░░░░░░░░  2.1% │  5-15 min  ░░░░░░░░░░░░  3%                      │
│  ABORTED  ░░░░░░░░░░░░  1.4% │  > 15 min  ░░░░░░░░░░░░  1%                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│  💡 优化建议                                                                       │
│  • 你的 app-release/main 平均构建时长 3.74 min，启用 Gradle 远程缓存可节省约 40% (1.5 min)  │
│  • 本月超额 847 min EC2，升级到 Tier 3 可节省 $47/月                                  │
│  • 12 个 ABORTED 构建发生在工作日晚间，考虑优化 Cron 触发器                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 各面板详细说明

### 2.1 团队月度总览面板（KPI Cards）

共 5 个 Stat 面板，横排展示：

| 面板 | 指标 | 阈值颜色 |
|------|------|---------|
| 本月总费用 | `total_fee` | 绿(<预算80%) → 黄(80-100%) → 红(>预算) |
| EC2 用量 | `ec2_minutes_used / ec2_minutes_quota × 100%` | 绿(<80%) → 黄(80-99%) → 红(≥100%) |
| Mac Mini 用量 | `mac_mini_minutes_used / mac_mini_minutes_quota × 100%` | 同上 |
| 构建次数 | `build_count / build_count_quota × 100%` | 同上 |
| 平均排队等待 | `avg_queue_wait_seconds / 60` | 绿(<SLA) → 红(>SLA) |

**Grafana 面板配置**：
```json
{
  "type": "stat",
  "title": "本月 EC2 使用率",
  "fieldConfig": {
    "defaults": {
      "unit": "percentunit",
      "thresholds": {
        "steps": [
          { "color": "green", "value": 0 },
          { "color": "yellow", "value": 0.8 },
          { "color": "red", "value": 1.0 }
        ]
      }
    }
  },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"] },
    "orientation": "auto",
    "textMode": "auto",
    "colorMode": "background"
  }
}
```

### 2.2 构建分钟趋势图

**展示内容**：
- X 轴：日期（过去 30 天）
- Y 轴：构建分钟数
- 系列 1（蓝色）：EC2 构建分钟
- 系列 2（橙色）：Mac Mini 构建分钟
- 参考线（红色虚线）：月度 EC2 配额（折算到每日）
- 参考线（紫色虚线）：月度 Mac Mini 配额（折算到每日）

**PromQL 查询示例（基于 CloudWatch Metrics 或 Prometheus）**：
```
# EC2 每日构建分钟（基于 CloudWatch）
SELECT SUM(build_duration_minutes)
FROM build_events
WHERE team_id = '$team_id'
  AND node_type LIKE 'ec2-%'
  AND DATE(build_started_at) = date_trunc('day', NOW())
GROUP BY DATE(build_started_at)
```

### 2.3 资源使用分布（Pie / Bar Chart）

两张图并排：

**图 1：按节点类型分布（分钟数）**
- EC2 Small / EC2 Medium / EC2 Large / Mac Mini M1 / Mac Mini M2

**图 2：按 Job 分布（Top 5 + 其他）**
- 展示最消耗资源的 5 个 Job，剩余归为 "Other"

### 2.4 Tier 配额使用进度

使用 **Gauge 仪表盘** 展示：

```
EC2 配额使用率   [███████░░░] 70%  1,400 / 2,000 min
Mac Mini 配额    [████████░░] 80%  400 / 500 min    ⚠️ 即将超额
构建次数配额     [█████░░░░░] 50%  500 / 1,000 次
存储配额         [███░░░░░░░] 30%  15 / 50 GB
```

**告警颜色**：
- 0-79%：绿色
- 80-99%：黄色 + ⚠️ 图标
- ≥100%：红色 + 🚨 图标

### 2.5 超额预警面板

当任何维度达到配额 80% 时，此面板显示：

```
┌────────────────────────────────────────────────────────┐
│  ⚠️  超额预警                                            │
│                                                        │
│  Mac Mini 用量已达配额 80%（400/500 min）                │
│  按当前使用趋势，预计在 2024-01-22 达到配额上限             │
│  预计超额费用：$36（按剩余 9 天估算）                      │
│                                                        │
│  [立即升级 Tier]  [查看 Mac Mini 使用详情]                │
└────────────────────────────────────────────────────────┘
```

**实现逻辑**：
```python
def calculate_overage_prediction(team_id: str):
    """基于前15天趋势预测本月超额"""
    today = datetime.now()
    days_elapsed = today.day
    days_in_month = 31  # 或通过 calendar 获取

    # 前 15 天的平均每日用量
    daily_avg = get_daily_avg_usage(team_id, days=15)

    # 预测全月用量
    predicted_monthly = daily_avg * days_in_month

    # 预测超额
    config = get_team_config(team_id)
    predicted_overage = max(0, predicted_monthly - config['ec2_quota'])

    # 预计达到上限的日期
    if daily_avg > 0:
        days_until_quota = (config['ec2_quota'] - get_current_usage(team_id)) / daily_avg
        quota_exhaustion_date = today + timedelta(days=days_until_quota)
    else:
        quota_exhaustion_date = None

    return {
        'predicted_monthly': predicted_monthly,
        'predicted_overage': predicted_overage,
        'quota_exhaustion_date': quota_exhaustion_date
    }
```

### 2.6 队列等待时间分析

**面板 1：等待时间分布（Histogram）**
- Bucket：<1min, 1-2min, 2-5min, 5-10min, 10-15min, >15min
- 目标：展示 SLA 达标率

**面板 2：等待时间趋势（Time Series）**
- X 轴：每小时
- Y 轴：P50 / P90 / P99 等待时间
- 参考线：SLA 阈值（Tier 2 = 5 min）

**面板 3：等待时间热图（Heatmap）**
- X 轴：星期几（Mon-Sun）
- Y 轴：小时（0-23）
- 颜色：平均等待时间（绿→黄→红）
- 用于发现峰值时段，指导团队优化构建时间

### 2.7 构建成功率分析

**面板 1：成功率趋势（Time Series，7 天）**
- 展示每日成功率，目标 >90%

**面板 2：失败原因分布（如数据可采集）**
- OOM Error / Network Error / Test Failure / Timeout / Other

**面板 3：失败 Job 排行（Table）**
- Job 名 / 失败次数 / 失败率 / 最近失败时间

### 2.8 成本趋势和预测

**面板 1：月度成本趋势（Bar Chart，过去 12 个月）**
- 堆叠柱状图：基础费（蓝）+ 超额费（橙）+ Add-on（绿）

**面板 2：成本预测（本月剩余）**
- 已花费：$XXX
- 预测本月总费用：$XXX
- 预测置信区间（基于过去 15 天趋势）

---

## 3. Grafana Dashboard JSON 配置示例

```json
{
  "uid": "jenkins-billing-team",
  "title": "Jenkins Build Billing - Team Dashboard",
  "tags": ["jenkins", "billing", "internal"],
  "timezone": "browser",
  "refresh": "5m",
  "time": { "from": "now/M", "to": "now/M" },

  "templating": {
    "list": [
      {
        "name": "team_id",
        "type": "query",
        "label": "Team",
        "datasource": "CloudWatch",
        "query": "SELECT DISTINCT team_id FROM monthly_usage",
        "current": { "value": "${USER_TEAM_ID}" }
      },
      {
        "name": "billing_period",
        "type": "interval",
        "label": "Billing Period",
        "options": ["2024-01", "2024-02", "2024-03"]
      }
    ]
  },

  "panels": [
    {
      "id": 1,
      "gridPos": { "x": 0, "y": 0, "w": 4, "h": 4 },
      "type": "stat",
      "title": "本月总费用",
      "datasource": "CloudWatch",
      "targets": [{
        "expr": "SELECT total_fee FROM monthly_usage WHERE team_id='$team_id' AND billing_period='$billing_period'"
      }],
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": 0 },
              { "color": "yellow", "value": 1500 },
              { "color": "red", "value": 2000 }
            ]
          }
        }
      }
    },
    {
      "id": 2,
      "gridPos": { "x": 0, "y": 4, "w": 24, "h": 8 },
      "type": "timeseries",
      "title": "构建分钟趋势（30 天）",
      "datasource": "CloudWatch",
      "targets": [
        {
          "alias": "EC2 构建分钟",
          "metricName": "ec2_build_minutes_daily",
          "dimensions": { "team_id": "$team_id" },
          "statistics": ["Sum"]
        },
        {
          "alias": "Mac Mini 构建分钟",
          "metricName": "mac_mini_build_minutes_daily",
          "dimensions": { "team_id": "$team_id" },
          "statistics": ["Sum"]
        }
      ],
      "fieldConfig": {
        "defaults": { "unit": "short", "displayName": "${__field.labels.alias}" }
      },
      "options": {
        "tooltip": { "mode": "multi" },
        "legend": { "displayMode": "list", "placement": "bottom" }
      }
    }
  ]
}
```

---

## 4. 告警规则设计

### 4.1 配额使用 80% 预警

**触发条件**：任一维度使用率 ≥ 80%

```yaml
# AlertManager / CloudWatch Alarm
AlertName: jenkins_billing_quota_80_warning
Condition: (ec2_minutes_used / ec2_minutes_quota) >= 0.80
OR (mac_mini_minutes_used / mac_mini_minutes_quota) >= 0.80
EvaluationPeriod: 每小时检查一次
Notification:
  - Slack: #billing-alerts-${team_id}
  - Email: ${team_manager_email}
Message: |
  ⚠️ [配额预警] ${team_id}
  EC2 配额使用率：${ec2_usage_pct}%（${ec2_used}/${ec2_quota} min）
  Mac Mini 配额使用率：${mac_usage_pct}%（${mac_used}/${mac_quota} min）
  按当前趋势，预计在 ${exhaustion_date} 达到上限。
  查看详情：${dashboard_url}
```

### 4.2 配额使用 100% 告警

**触发条件**：任一维度使用率 ≥ 100%

```yaml
AlertName: jenkins_billing_quota_exceeded
Condition: (ec2_minutes_used / ec2_minutes_quota) >= 1.0
Severity: HIGH
Notification:
  - Slack: #billing-alerts-${team_id}（@team-manager）
  - Email: ${team_manager_email}, ${finance_contact_email}
  - PagerDuty: 非工作时间升级（Tier 3 团队）
Message: |
  🚨 [配额超额] ${team_id} EC2 配额已耗尽！
  已使用：${ec2_used} min（配额 ${ec2_quota} min）
  超额部分将按 $${overage_price}/min 计费。
  当前预计超额费用：$${estimated_overage_cost}
  [升级 Tier] | [查看用量] | [提交申请豁免]
```

### 4.3 异常构建时长告警

**触发条件**：单次构建时长超过该团队历史 P99 的 3 倍

```python
def check_abnormal_build_duration(team_id: str, build_duration_min: int):
    """检测异常长时间构建"""
    # 获取该团队历史 P99 构建时长
    p99_duration = get_team_p99_duration(team_id, days=30)
    threshold = p99_duration * 3

    if build_duration_min > threshold:
        send_alert(
            level='WARNING',
            team_id=team_id,
            message=f"异常构建时长：{build_duration_min} min（历史 P99 = {p99_duration} min，阈值 = {threshold} min）"
        )
```

**固定阈值告警**（不依赖历史数据）：
- EC2 单次构建 > 60 分钟：WARNING
- EC2 单次构建 > 120 分钟：ERROR（可能卡死）
- Mac Mini 单次构建 > 90 分钟：WARNING

### 4.4 Grafana Alerting 配置

```yaml
# grafana/alerts/quota_warning.yaml
apiVersion: 1
groups:
  - orgId: 1
    name: Jenkins Billing Alerts
    interval: 5m
    rules:
      - uid: ec2_quota_80pct
        title: EC2 配额使用 80%
        condition: C
        data:
          - refId: A
            datasourceUid: cloudwatch-prod
            model:
              expression: |
                SELECT ec2_minutes_used, ec2_minutes_quota, team_id
                FROM monthly_usage
                WHERE billing_period = date_format(now(), '%Y-%m')
          - refId: C
            datasourceUid: __expr__
            model:
              type: math
              expression: "$A.ec2_minutes_used / $A.ec2_minutes_quota"
        noDataState: NoData
        execErrState: Error
        for: 0s
        annotations:
          summary: "EC2 配额已用 {{ $values.C | humanize }}%"
        labels:
          severity: warning
          team: "{{ $labels.team_id }}"
        isPaused: false
```

---

## 5. 自助优化建议展示

Dashboard 底部固定展示优化建议面板（基于规则引擎分析）：

### 建议规则

| 场景 | 检测条件 | 建议内容 |
|------|---------|---------|
| 构建缓存未启用 | Gradle 构建 avg > 10 min | 启用 Gradle 远程缓存可节省 30-50% 时间 |
| 重复构建失败 | 失败率 > 15% | 高失败率导致额外费用，建议优化 Pipeline |
| 构建超时频繁 | 超 60 min 的构建 > 5 次/月 | 考虑拆分构建 Stage 或升级到更大规格 Agent |
| 非工作时间大量触发 | 22:00-06:00 期间构建占比 > 30% | 非工作时间队列空闲，效率最优 |
| 使用 Large 节点过多 | ec2-large 占比 > 40% | 检查是否所有 Large Job 都需要高规格 |
| Mac Mini 使用 Android 构建 | 在 Mac Mini 上触发非 iOS 构建 | 请将 Android 构建迁移到 EC2（费用低 7 倍）|
| Tier 超额严重 | 连续 2 月超额 > 50% | 升级 Tier 可节省 $XXX/月 |

```python
def generate_optimization_tips(team_id: str, billing_period: str) -> list:
    """生成个性化优化建议"""
    tips = []
    usage = get_team_monthly_usage(team_id, billing_period)
    builds = get_team_builds(team_id, billing_period)

    # 检查 Gradle 缓存
    gradle_builds = [b for b in builds if 'gradle' in b.get('build_tool', '')]
    if gradle_builds:
        avg_duration = sum(b['duration'] for b in gradle_builds) / len(gradle_builds)
        if avg_duration > 10:
            tips.append({
                'icon': '💡',
                'title': '启用 Gradle 远程缓存',
                'description': f'你的 Gradle 构建平均时长 {avg_duration:.1f} min，'
                               f'启用远程缓存预计可节省约 {avg_duration * 0.4:.1f} min/次，'
                               f'月节省约 {len(gradle_builds) * avg_duration * 0.4:.0f} min',
                'action_url': '/docs/build-cache-setup',
                'action_text': '查看配置指南'
            })

    # 检查 Tier 超额
    config = get_team_config(team_id)
    ec2_overage = max(0, usage['ec2_minutes_used'] - config['ec2_quota'])
    if ec2_overage > config['ec2_quota'] * 0.5:
        next_tier = get_next_tier(config['tier'])
        savings = calculate_tier_upgrade_savings(config['tier'], next_tier, usage)
        tips.append({
            'icon': '📈',
            'title': f'升级到 Tier {next_tier} 可节省费用',
            'description': f'本月 EC2 超额 {ec2_overage} min，'
                           f'升级到 {next_tier} Tier 可节省约 ${savings:.0f}/月',
            'action_url': '/portal/upgrade-tier',
            'action_text': '立即升级'
        })

    return tips
```
