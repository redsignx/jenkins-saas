# 推行策略与阶段规划

## 总体时间线

```
月份:   1    2    3    4    5    6    7    8    9    10   11   12
       ├────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┤
Phase 0 ████████████                                            透明化阶段（影子账单）
Phase 1          ████████████                                   软计费阶段
Phase 2                    ████████████████████████████████    正式计费阶段
优化               ────────────────────────────────────────    持续优化（长期）
```

---

## Phase 0：透明化阶段（第 1-2 个月）

### 目标

让所有团队在**不产生任何费用**的情况下了解：
1. 自己每月消耗了多少构建资源
2. 如果计费，每月大概会产生多少费用
3. 应该选择哪个 Tier

### 时间线

| 周次 | 事项 |
|------|------|
| Week 1 | 部署计量系统，开始数据采集（只读，不计费）|
| Week 2 | 内部验证数据准确性，对比 AWS 账单 |
| Week 3 | 生成首批"影子账单"，内部审核 |
| Week 4 | 全公司发布通知，说明计划 |
| Week 5-8 | 发送每周影子账单，收集团队反馈 |
| Week 8 | Phase 0 总结，决定是否进入 Phase 1 |

### 影子账单设计

影子账单是"如果计费，你将收到的账单"，不产生实际费用。

**影子账单邮件模板**：

```
主题：[Jenkins Build Service] 2024年1月构建用量报告（仅参考，暂不计费）

Hi ${team_manager_name}，

这是 ${team_name} 团队 2024 年 1 月的 Jenkins 构建用量报告。
请注意：本报告仅供参考，当前阶段不产生实际费用。

━━━━━━━━━━━━━━━━━━━━━━━━
📊 本月构建用量摘要
━━━━━━━━━━━━━━━━━━━━━━━━

EC2 构建时长：  2,847 分钟
Mac Mini 时长：  623 分钟
构建次数：      1,134 次
Artifact 存储：   43.7 GB
平均排队等待：    3.2 分钟

━━━━━━━━━━━━━━━━━━━━━━━━
💰 假设计费金额（仅参考）
━━━━━━━━━━━━━━━━━━━━━━━━

推荐 Tier：Tier 2 Standard（$1,800/月）

如按 Tier 2 Standard 计费：
  月基础费：               $1,800.00
  EC2 超额（847 min）：      $33.88
  Mac Mini 超额（123 min）：  $14.76
  ---------------------------------
  估算月总费用：           $2,048.64

━━━━━━━━━━━━━━━━━━━━━━━━
💡 优化建议
━━━━━━━━━━━━━━━━━━━━━━━━

1. 启用 Gradle 远程缓存（预计节省 30% 构建时间，约 $20/月）
2. 考虑升级到 Tier 3（连续超额，升级后预计节省 $XX/月）

━━━━━━━━━━━━━━━━━━━━━━━━

📋 计划说明
━━━━━━━━━━━━━━━━━━━━━━━━

• 第 1-2 个月：仅发送参考账单，不收费（当前阶段）
• 第 3 个月起：开始正式计费，超额部分有宽限期
• 第 5 个月起：全面正式计费

您可以在以下链接查看详细的每次构建记录：
${dashboard_url}

如有任何问题，请联系 Jenkins Platform Team：
- Slack：#jenkins-platform
- Email：jenkins-platform@company.com
- 内部工单：${ticket_url}

Jenkins Platform Team
```

### 沟通计划

| 受众 | 渠道 | 内容 | 时间 |
|------|------|------|------|
| 全公司（所有团队）| 全员邮件 + Slack #announcements | 计费计划通知 | Week 4 周一 |
| 技术负责人（Tech Lead）| 专项会议（30 min）| 技术实现和数据来源说明 | Week 4 周三 |
| 财务部门 | 线下会议 | Cost Center 对接流程 | Week 4 周四 |
| 高频使用团队（Top 20）| 单独 1:1 | 个性化用量分析和 Tier 建议 | Week 5-6 |
| 管理层 | 月度报告 | 整体平台成本和回收情况 | 每月 15 日 |

### 团队 Onboarding 流程

```
团队收到影子账单邮件
          ↓
访问 Billing Portal，查看详细报告
          ↓
使用 Tier 推荐工具：输入每月预期用量 → 系统推荐最优 Tier
          ↓
填写 Tier 申请表（含 Cost Center 确认）
          ↓
平台团队确认（1 个工作日）
          ↓
等待正式计费开始（Phase 1）
```

**Tier 推荐工具逻辑**：
```python
def recommend_tier(monthly_ec2_minutes: int, monthly_mac_minutes: int,
                   monthly_builds: int, storage_gb: float) -> dict:
    """根据用量推荐最优 Tier"""
    tiers = ['basic', 'standard', 'premium']
    costs = {}

    for tier in tiers:
        config = TIER_CONFIGS[tier]
        total_cost = config['base_fee']
        total_cost += max(0, monthly_ec2_minutes - config['ec2_quota']) * config['ec2_overage_price']
        total_cost += max(0, monthly_mac_minutes - config['mac_quota']) * config['mac_overage_price']
        total_cost += max(0, monthly_builds - config.get('build_quota', 9999)) * config.get('build_overage_price', 0)
        total_cost += max(0, storage_gb - config['storage_quota_gb']) * 0.025
        costs[tier] = total_cost

    recommended = min(costs, key=costs.get)
    return {
        'recommended_tier': recommended,
        'estimated_cost': costs[recommended],
        'alternatives': costs
    }
```

### Phase 0 成功标准

- [ ] 100% 的活跃团队（月构建 > 0）已收到影子账单
- [ ] 70% 的团队已登录 Billing Portal 查看报告
- [ ] 50% 的团队已填写 Tier 申请表
- [ ] 数据准确率 ≥ 99%（通过抽样验证）
- [ ] 收到的反馈中，负面反馈 < 30%

---

## Phase 1：软计费阶段（第 3-4 个月）

### 目标

正式开始计费，但设置**宽限配额**，超额部分只警告不强制收费，给团队适应期。

### 关键设置

**宽限政策**：
- Tier 1 团队：配额放大 1.5 倍（如 EC2 配额 750 min 而非 500 min）
- Tier 2 团队：配额放大 1.3 倍
- Tier 3 团队：配额放大 1.2 倍
- **超额部分：记录但不计入本月账单，仅警告**

### Tier 选择指引

**如何决定应该选哪个 Tier**（给团队的决策树）：

```
月 EC2 构建时长 < 400 min AND Mac Mini < 80 min？
    → Tier 1 Basic（$500/月）

月 EC2 构建时长 400-1,600 min OR Mac Mini 80-400 min？
    → Tier 2 Standard（$1,800/月）

月 EC2 构建时长 > 1,600 min OR Mac Mini > 400 min OR 需要 7×24 SLA？
    → Tier 3 Premium（$5,000/月）
```

### 反馈收集机制

**自动反馈**：
- 每月账单邮件附带 NPS 调查问卷（5 个问题，2 分钟完成）
- Dashboard 中的"反馈"按钮
- 季度使用者访谈（每 Tier 抽取 3-5 个团队）

**NPS 问卷示例**：
```
1. 本月账单金额是否在你的预期范围内？（1-5 分）
2. 计费维度是否清晰易懂？（1-5 分）
3. Dashboard 是否提供了足够的信息？（1-5 分）
4. 你觉得价格是否合理？（1-5 分）
5. 你是否会向其他团队推荐使用我们的服务？（0-10 NPS）
6. 你最希望改进的一个地方是？（开放文字）
```

### Phase 1 成功标准

- [ ] 90% 的团队已完成 Tier 选择
- [ ] 计费系统运行稳定，无重大错误（DLQ 为空）
- [ ] NPS 得分 ≥ 30
- [ ] 没有团队因计费问题导致构建服务中断

---

## Phase 2：正式计费阶段（第 5 个月起）

### 全面执行计划

| 日期 | 事项 |
|------|------|
| Phase 2 开始前 4 周 | 发送正式计费开始通知 |
| Phase 2 开始前 2 周 | 最后一次 Tier 调整窗口 |
| Phase 2 开始前 1 周 | 与财务部门确认转账流程就绪 |
| Phase 2 第 1 天 | 正式计费生效，取消宽限倍数 |
| Phase 2 第 1 个月末 | 发出第一张正式账单 |
| Phase 2 第 1 个月 + 15 天 | 第一笔内部转账 |

### 与财务部门对接流程

**前期准备（Phase 2 前 1 个月）**：
1. 与财务 IT 系统对接（SAP / Oracle Finance）
2. 确认内部转账 API 或流程
3. 创建平台团队的"收款" Cost Center
4. 测试端到端转账流程

**月度对账流程**：
```
平台团队生成账单（每月 5 日）
         ↓
账单发送给各团队 Manager（含 Cost Center 确认）
         ↓
团队 Manager 确认用量（截止每月 10 日）
         ↓
财务团队收到汇总转账请求（每月 12 日）
         ↓
财务系统执行 Cost Center 内部转账（每月 15-20 日）
         ↓
转账完成通知（每月 20 日）
         ↓
平台团队确认入账，月度对账完成
```

### Cost Center 映射

**映射表维护原则**：
- 由平台团队在 Git 仓库中以 YAML 文件维护
- 每次变更需要 PR + 财务部门代表 Review
- 每季度与财务部门全面校对

```yaml
# config/team_costcenter_mapping.yaml
teams:
  - team_id: mobile-android-team
    jenkins_folder: mobile/android
    cost_center_code: CC-1001
    cost_center_name: 移动端 Android 团队
    business_unit: 移动事业部
    finance_contact: finance-mobile@company.com
    team_manager: android-lead@company.com
    tier: standard
    effective_date: 2024-05-01

  - team_id: mobile-ios-team
    jenkins_folder: mobile/ios
    cost_center_code: CC-1002
    cost_center_name: 移动端 iOS 团队
    business_unit: 移动事业部
    finance_contact: finance-mobile@company.com
    team_manager: ios-lead@company.com
    tier: premium
    effective_date: 2024-05-01
```

### 争议处理流程

**第一步：团队提交争议**
- 在 Billing Portal 中点击"对账单有异议"
- 填写：争议描述、具体构建记录（Build URL + Build Number）、主张金额

**第二步：平台团队核查（3 个工作日）**
- 对比 DynamoDB 中的构建记录和 Jenkins 构建日志
- 核查是否存在数据采集误差
- 出具核查报告

**第三步：结果处理**
```
核查结果为平台错误 → 出具更正账单，差额冲抵下月账单
核查结果为数据准确 → 维持原账单，向团队解释
核查结果存疑（数据缺失）→ 按团队主张金额处理（有利于团队原则）
双方无法达成一致 → 升级到双方 Manager，由管理层裁决
```

**争议处理时限**：
- 一般争议：5 个工作日
- 复杂争议（需要多方确认）：10 个工作日
- 升级裁决：20 个工作日

---

## 持续优化阶段

### 季度 Review 流程

每季度（Q1/Q2/Q3/Q4）末进行一次全面 Review：

**Review 内容**：
1. 平台成本与收入对比（是否覆盖成本 + Margin 合理）
2. 各 Tier 分布和流转情况
3. 用量趋势和预测（未来季度扩容计划）
4. NPS 和用户满意度
5. 定价调整建议

**Review 参与者**：
- 平台团队 Manager
- 高频使用团队代表（各 Tier 1-2 个）
- 财务部门代表
- 基础架构团队代表

### 定价调整机制

**触发调整的条件**：
- AWS 价格调整 > 15%
- 平台成本结构重大变化（如 Mac Mini 批量采购）
- 用量数据显示某 Tier 定价明显不合理（超额率持续 > 80%）
- 新增资源类型（如 GPU 节点）

**调整流程**：
```
平台团队提出调整提案（包含数据支撑）
            ↓
内部审核（1 周）
            ↓
向所有团队发布"价格调整预通知"（提前 60 天）
            ↓
30 天后发送正式通知（含调整后价格表）
            ↓
新价格生效（60 天后）
```

### 新增服务计划

| 计划 | 时间 | 内容 |
|------|------|------|
| Windows Build Agent | Q3 2024 | 支持 Windows UWP 构建 |
| GPU Build Agent | Q4 2024 | 机器学习模型测试 |
| 动态 Spot 折扣 | Q1 2025 | 根据 Spot 实际节省比例给团队折扣 |
| 按需付费模式 | Q2 2025 | 无 Tier 固定费，纯按量计费 |

---

## 关键成功指标（KPI）

### 财务指标

| KPI | 目标值 | 测量方式 |
|-----|--------|---------|
| 月度成本回收率 | ≥ 85%（第 6 个月起）| 实收 / 实际成本 |
| 超额收入占比 | 10-20%（说明定价合理）| 超额收入 / 总收入 |
| 账单争议率 | < 2%（账单数量）| 争议单数 / 总账单数 |
| 年度预付比例 | > 30%（稳定后）| 年付团队数 / 总团队数 |

### 运营指标

| KPI | 目标值 | 测量方式 |
|-----|--------|---------|
| 数据采集准确率 | ≥ 99.9% | 抽样验证 |
| 账单生成及时率 | 100%（每月 5 日前）| 账单发送记录 |
| 争议处理及时率 | ≥ 95%（5 工作日内）| 争议工单记录 |
| Dashboard 可用性 | ≥ 99.5% | CloudWatch 监控 |

### 用户体验指标

| KPI | 目标值 | 测量方式 |
|-----|--------|---------|
| NPS 得分 | ≥ 40（成熟期）| 季度 NPS 调查 |
| Dashboard 月活率 | ≥ 70%（团队数）| Grafana 访问日志 |
| Tier 自主选择率 | ≥ 80%（无需平台推荐）| 申请记录 |

---

## 风险与缓解措施

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| 团队强烈抵制计费 | 中 | 高 | Phase 0 充分沟通；提供合理的过渡期；高层背书 |
| 数据采集不准确 | 低 | 高 | Phase 0 双重验证；抽样审计；有利于团队原则 |
| Jenkins Webhook 丢失事件 | 低 | 中 | SQS DLQ + 重试；每日数据校验 |
| AWS 成本大幅上涨 | 低 | 中 | Spot 混合策略；Reserved Instance；90天调整一次定价 |
| 团队绕过计费（直连 Agent）| 极低 | 低 | IAM 权限控制；Jenkins Folder 隔离 |
| Mac Mini 硬件损坏 | 低 | 中 | 维护备用机；损坏期间按比例减免费用 |
| 财务系统对接失败 | 低 | 中 | Phase 1 阶段提前与财务确认；保留 Excel 手动转账方案 |

---

## 沟通模板

### 计费计划通知邮件（Phase 0 Week 4）

```
主题：[重要通知] Jenkins Build Service 计费计划 - 2024年5月正式启动

Hi All，

Jenkins Platform Team 计划于 2024 年 5 月 1 日开始对 Jenkins Build Service 实施内部计费（Chargeback）。

背景：
随着 Jenkins 用量持续增长，构建资源（EC2、Mac Mini）的成本已成为重要的运营开支。
为了实现成本公平分摊和可持续运营，我们计划引入内部计费模式。

计划节奏：
• 3-4 月（当前）：透明化阶段，只发送参考账单，不产生实际费用
• 3-4 月：各团队选择合适的 Tier 套餐
• 5 月起：正式计费开始

下一步行动：
1. 查看你的团队本月用量报告：${dashboard_url}
2. 使用 Tier 推荐工具，了解适合你团队的套餐：${tier_tool_url}
3. 填写 Tier 申请表（3月31日前）：${signup_url}

如有疑问，欢迎在 #jenkins-billing-qa（Slack）提问，
或阅读详细文档：${billing_docs_url}

Jenkins Platform Team
```

### FAQ 提醒邮件（每月随账单发送）

```
主题：[Jenkins Billing] 2024年1月账单 - ${team_name}（$${total_fee}）

...（账单摘要）...

❓ 有疑问？
• 账单说明文档：${billing_docs_url}
• 常见问题：${faq_url}
• 提交争议：${dispute_url}
• 联系我们：#jenkins-platform（Slack）
```
