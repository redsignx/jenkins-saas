# 单价定价逻辑与成本拆解

## 1. 核心定价公式

```
单位成本 = (直接基础设施成本 + 间接成本分摊) / 总可用资源量

对外单价 = 单位成本 × (1 + Margin 率)
```

其中：
- **直接基础设施成本**：EC2 费用、EBS 费用、数据传输费用等可直接归因的成本
- **间接成本分摊**：Jenkins Controller 分摊、运维人力分摊、平台开发维护分摊
- **总可用资源量**：月度总可用 Build Minutes（基于平均利用率估算）
- **Margin 率**：建议 15%~30%，用于覆盖不可预见成本和平台发展资金

---

## 2. EC2 构建节点完整成本分析

### 2.1 EC2 实例费用（On-Demand vs Spot 混合策略）

Jenkins EC2 Fleet 插件支持混合 Spot + On-Demand 策略：

| 策略 | 说明 | 成本节省 |
|------|------|---------|
| 100% On-Demand | 高可用，无中断风险 | 基准价格 |
| 70% Spot + 30% On-Demand | 推荐策略，Spot 中断时切换 On-Demand | 节省约 50%~70% |
| 100% Spot | 低成本，但存在构建中断风险 | 节省约 70%~90% |

**推荐混合策略**：70% Spot + 30% On-Demand

```
月 EC2 成本 = Spot 实例费用 × 70% + On-Demand 实例费用 × 30%
```

**以 `c5.4xlarge` 为例（us-east-1，2024 价格参考）**：
| 计费方式 | 小时单价 | 月成本（720h）|
|---------|---------|-------------|
| On-Demand | $0.68/h | $489.6/月 |
| Spot（平均）| $0.20/h | $144.0/月 |
| 混合（70%S+30%OD）| $0.344/h | **$247.7/月** |

**ASG 节点规划**（以 10 台 `c5.4xlarge` 为例）：
```
月 EC2 实例费 = 10 台 × $247.7/月 = $2,477/月
月可用 Build Minutes = 10 台 × 720h × 60min × 75% 利用率 = 324,000 min
EC2 纯硬件成本 = $2,477 / 324,000 = $0.0076/min
```

### 2.2 EBS 存储成本

每个 EC2 Build Agent 需要 EBS 卷作为构建 workspace：

| 存储类型 | 用途 | 单价 | 每台 Agent 月成本 |
|---------|------|------|----------------|
| gp3 100 GB | OS + Jenkins Agent | $0.08/GB/月 | $8.00/月 |
| gp3 200 GB | Build workspace | $0.08/GB/月 | $16.00/月 |
| **合计** | | | **$24.00/月** |

```
10 台 Agent × $24/月 = $240/月
每分钟 EBS 成本 = $240 / 324,000 min = $0.00074/min
```

### 2.3 数据传输成本

| 流向 | 说明 | AWS 费用 |
|------|------|---------|
| EC2 → S3（Artifact 上传）| 同区域，免费 | $0 |
| S3 → 外部（下载 Artifact）| 按出站流量 | $0.09/GB |
| EC2 → S3 Cache（Gradle/npm）| 同区域，免费 | $0 |
| 数据传入 EC2 | 免费 | $0 |

估算：每次构建平均上传 Artifact 50 MB
```
10 台 Agent × 全天利用率 → 月约 50,000 次构建
数据传输费 = 50,000 × 0.05 GB × $0.09/GB = $225/月（Artifact 出站）
每分钟数据传输成本 = $225 / 324,000 min ≈ $0.00069/min
```

### 2.4 Jenkins Controller 分摊

Jenkins Controller 是平台固定成本，按所有团队分摊：

| 成本项 | 月成本 | 说明 |
|--------|-------|------|
| EC2 实例（r5.2xlarge，On-Demand）| $373/月 | Controller 主机 |
| EC2 实例（r5.xlarge，备用）| $186/月 | HA 备用节点 |
| EBS（500 GB gp3）| $40/月 | Jenkins 数据目录 |
| S3（Build 日志存储）| $50/月 | |
| CloudWatch（监控）| $30/月 | |
| ELB（负载均衡）| $18/月 | |
| Route53（DNS）| $1/月 | |
| **Controller 总月成本** | **$698/月** | |
| **按 100 个团队分摊** | **$6.98/团队/月** | |

```
每分钟 Controller 分摊成本（按全平台总 Build Minutes 分摊）：
假设平台月总 Build Minutes = 2,000,000 min
Controller 每分钟分摊 = $698 / 2,000,000 = $0.000349/min
```

### 2.5 运维人力分摊

| 人力类别 | 月成本（假设）| 分摊到 EC2 构建的比例 | EC2 月人力分摊 |
|---------|------------|------------------|-------------|
| SRE（2 人）× $150/天 × 20 天 | $6,000/月 | 60% | $3,600/月 |
| DevOps Engineer（1 人）× $120/天 × 20 天 | $2,400/月 | 70% | $1,680/月 |
| **EC2 运维人力合计** | | | **$5,280/月** |

```
假设平台 EC2 月总 Build Minutes = 1,500,000 min
每分钟 EC2 运维人力成本 = $5,280 / 1,500,000 = $0.00352/min
```

### 2.6 平台开发维护分摊

| 工作内容 | 月成本（假设）| 分摊比例 |
|---------|------------|---------|
| 计费系统开发维护 | $3,000/月 | 100% 分摊 |
| Jenkins 插件维护 | $1,500/月 | 100% 分摊 |
| Pipeline 模板维护 | $1,000/月 | 100% 分摊 |
| **平台开发合计** | **$5,500/月** | |

```
每分钟平台开发分摊 = $5,500 / 2,000,000 = $0.00275/min
```

### 2.7 EC2 成本汇总与定价推导

| 成本项 | 每分钟成本 |
|--------|---------|
| EC2 实例（混合 Spot/On-Demand）| $0.00760/min |
| EBS 存储 | $0.00074/min |
| 数据传输 | $0.00069/min |
| Controller 分摊 | $0.00035/min |
| 运维人力 | $0.00352/min |
| 平台开发维护 | $0.00275/min |
| **EC2 总成本** | **$0.01565/min** |
| **Margin 20%** | $0.00313/min |
| **对外定价（Medium 基准）** | **$0.019/min ≈ $0.02/min** |

> 超额单价 $0.03~$0.05/min 相对成本有充足 Margin，合理。

---

## 3. Mac Mini 完整成本分析

### 3.1 硬件折旧（3 年周期）

| 硬件型号 | 采购价格（参考）| 月折旧（36 个月）|
|---------|-------------|----------------|
| Mac Mini M1（16GB RAM）| $1,499 | $41.6/台/月 |
| Mac Mini M2 Pro（32GB RAM）| $2,399 | $66.6/台/月 |

> 采购价格含税，建议使用直线折旧法。配件（数据线、KVM）等按 10% 溢价计入。

### 3.2 机房托管费用

假设 Mac Mini 托管在公司自有或租用的数据中心：

| 费用项 | 月成本（每台）| 说明 |
|--------|------------|------|
| 机架空间（1U）| $50/月 | 数据中心托管报价 |
| 网络端口（1G）| $20/月 | 含带宽 |
| KVM over IP | $5/月 | 远程管理 |
| **托管合计** | **$75/月/台** | |

### 3.3 电力与网络成本

| 费用项 | 说明 | 月成本（每台）|
|--------|------|------------|
| 功耗（Mac Mini M2 Pro，约 30W 满载）| 30W × 24h × 30天 × $0.12/kWh | $2.59/月 |
| UPS / 电力保障 | 20% 溢价 | $0.52/月 |
| **电力合计** | | **$3.11/月/台** |

### 3.4 macOS / Apple 开发工具许可费

| 许可类型 | 年费 | 月均成本 |
|---------|------|---------|
| Apple Developer Program | $99/年（整个公司一个账号）| 约 $0.7/月（分摊到每台 Mac Mini）|
| Xcode（免费）| $0 | $0 |
| 商业 CI 插件（如 Fastlane 商业版）| 视情况 | $5-20/月/台 |

> macOS 随硬件免费，无额外许可费用。

### 3.5 运维人力分摊（Mac Mini 专项）

Mac Mini 需要专门的物理运维（操作系统更新、Xcode 升级、硬件维护）：

| 人力类别 | 时间估算 | 月成本分摊（每台）|
|---------|---------|---------------|
| 系统更新（macOS、Xcode）| 2h/月/台 × $60/h | $120/月/台 |
| 硬件故障处理 | 平均 0.5h/月/台 × $60/h | $30/月/台 |
| 远程协助 | 1h/月/台 × $60/h | $60/月/台 |
| **Mac Mini 运维合计** | | **$210/月/台** |

### 3.6 Mac Mini 成本汇总与定价推导

以 Mac Mini M2 Pro 为例：

| 成本项 | 月成本（每台）|
|--------|------------|
| 硬件折旧 | $66.6 |
| 机房托管 | $75.0 |
| 电力网络 | $3.1 |
| macOS 许可分摊 | $5.7 |
| 运维人力 | $210.0 |
| 平台开发分摊（按比例）| $20.0 |
| **Mac Mini 总月成本** | **$380.4/台/月** |

```
每台 Mac Mini 月可用 Build Minutes（75% 利用率）：
= 720h × 60min × 75% = 32,400 min/月

Mac Mini 纯成本 = $380.4 / 32,400 = $0.01174/min

加 Margin 25%（Mac Mini 不可弹性扩展，溢价合理）：
对外定价 = $0.01174 × 1.25 = $0.0147/min ≈ **$0.015/min**

Tier 超额单价 $0.10~$0.15/min，相对成本有大量 Margin。
```

> **Margin 高的原因**：Mac Mini 是**稀缺资源**，无法按需扩容，高 Margin 起到**价格信号**作用，引导团队减少不必要的 iOS 构建，优先利用 EC2 完成非 iOS 任务。

---

## 4. Margin 设定建议

| 资源类型 | 建议 Margin 范围 | 推荐 Margin | 说明 |
|---------|---------------|-----------|------|
| EC2 构建（基础费包含配额）| 15%~25% | **20%** | 弹性资源，成本较易预测 |
| EC2 超额部分 | 30%~50% | **40%** | 超额单价包含额外 Margin，引导升级 |
| Mac Mini 基础费包含配额 | 25%~35% | **30%** | 稀缺资源，运维复杂 |
| Mac Mini 超额部分 | 50%~80% | **65%** | 超额价格应足够高，真正引导控制用量 |
| Artifact 存储 | 10%~20% | **15%** | 与 AWS S3 成本高度相关，Margin 较低 |

### Margin 的用途

从 Margin 中提取资金用于：
1. 覆盖实际成本波动（Spot 价格浮动、汇率等）
2. 平台团队的基础建设投入（新功能、扩容）
3. 服务备用基金（硬件损坏、紧急扩容）
4. 团队激励（绩效奖金）

---

## 5. 定价 Review 周期和调整机制

### Review 周期

| Review 类型 | 频率 | 触发条件 |
|-----------|------|---------|
| 例行 Review | 每半年（1月、7月）| 固定时间 |
| 紧急 Review | 随时 | AWS 价格变化 > 20%，或成本结构重大变化 |
| 年度全面 Review | 每年 12 月 | 新财年预算规划 |

### 调整原则

1. **价格只降不升**原则（理想情况）：随规模增长，单位成本下降，应反映到定价中
2. **提前 60 天通知**：价格调整需提前 2 个月通知所有团队
3. **锁价保护**：年付用户当年不受价格调整影响
4. **最大调幅**：单次价格调整不超过 ±20%

---

## 6. 从 AWS 账单推导构建分钟单价的完整步骤

### Step 1：获取 AWS 账单数据

```bash
# 使用 AWS Cost Explorer API 获取上月 EC2 + EBS 费用
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --filter '{"Tags":{"Key":"Service","Values":["jenkins-build"]}}' \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE
```

示例输出：
```json
{
  "EC2-Instances": { "Amount": "8432.50", "Unit": "USD" },
  "EC2-EBS": { "Amount": "1240.00", "Unit": "USD" },
  "AWSDataTransfer": { "Amount": "325.75", "Unit": "USD" }
}
```

### Step 2：获取 Jenkins 实际构建数据

```sql
-- 从 DynamoDB / RDS 查询上月总构建分钟数
SELECT
  SUM(build_duration_minutes) AS total_minutes,
  COUNT(*) AS total_builds,
  AVG(build_duration_minutes) AS avg_duration
FROM build_events
WHERE billing_period = '2024-01'
  AND node_type LIKE 'ec2-%'
  AND build_result IN ('SUCCESS', 'FAILURE', 'UNSTABLE', 'ABORTED_WITH_AGENT');
```

示例结果：
```
total_minutes: 1,847,320
total_builds: 142,560
avg_duration: 12.96 minutes
```

### Step 3：计算直接成本单价

```python
# 上月 EC2 直接成本
ec2_instance_cost = 8432.50
ec2_ebs_cost = 1240.00
data_transfer_cost = 325.75
direct_cost = ec2_instance_cost + ec2_ebs_cost + data_transfer_cost
# = $10,000.25

# 总构建分钟数
total_build_minutes = 1_847_320

# 直接成本单价
direct_cost_per_minute = direct_cost / total_build_minutes
# = $10,000.25 / 1,847,320 = $0.005414/min
```

### Step 4：加入间接成本分摊

```python
controller_cost = 698.00      # Jenkins Controller
ops_labor_cost = 5280.00      # 运维人力（EC2 部分）
dev_cost = 3666.67            # 平台开发（按 EC2/总资源 = 2/3 分摊）
total_indirect = controller_cost + ops_labor_cost + dev_cost
# = $9,644.67

indirect_cost_per_minute = total_indirect / total_build_minutes
# = $9,644.67 / 1,847,320 = $0.005222/min
```

### Step 5：计算总成本单价

```python
total_cost_per_minute = direct_cost_per_minute + indirect_cost_per_minute
# = $0.005414 + $0.005222 = $0.010636/min

# 加 20% Margin
final_price_per_minute = total_cost_per_minute * 1.20
# = $0.010636 × 1.20 = $0.012763/min ≈ $0.013/min（Medium 基准节点）
```

### Step 6：验证 Tier 定价合理性

```python
# Tier 2 Standard: 月基础费 $1,800，包含 2,000 min EC2 配额
tier2_cost = total_cost_per_minute * 2000
# = $0.010636 × 2,000 = $21.27（我们的成本）
# 月基础费 $1,800 >> $21.27，说明基础费中包含了大量间接成本分摊

# 更合理的理解：基础费 = 配额成本 + 间接成本包月 + 服务保障溢价
service_fee_per_team = (total_indirect / 100_teams) = $96.45/团队/月
quota_cost = total_cost_per_minute * 2000 = $21.27
premium_margin = 1800 - 96.45 - 21.27 = $1,682.28（溢价 = 队列优先级 + SLA + 服务保障）
```

> 💡 **结论**：$1,800 的月基础费中，约 $120 是实际成本，约 $1,680 是 SLA + 服务保障的溢价。这在 SaaS 定价中是常见且合理的——团队购买的是**确定性**和**服务保障**，而不仅仅是计算资源本身。
