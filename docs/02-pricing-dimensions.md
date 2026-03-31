# 核心计费维度详解

本文件详细描述构成账单的每一个计费维度，包括定义、计量方法、数据来源和计费精度。

---

## 维度一：构建时长（Build Minutes）

### 定义

构建时长是最核心的计费维度，衡量 Build Agent 被某次构建任务实际占用的时间。

### 精确计量方法

**数据来源**：Jenkins `RunListener` 插件或 Webhook 触发的事件

```
Build Minutes = ceil((build_end_timestamp - build_start_timestamp) / 60)
```

- `build_start_timestamp`：Agent 开始执行构建的时间（`onStarted` 事件时间戳）
- `build_end_timestamp`：构建结束的时间（`onCompleted` / `onFinalized` 事件时间戳）
- 使用 `ceil`（向上取整）到整数分钟
- 最小计费单位：**1 分钟**

### Queue Time 的处理

**Queue Time 不计入账单**，原因如下：

1. Queue Time 反映的是资源供给不足，而非团队实际消耗
2. Queue Time 受其他团队构建行为影响，对单个团队不公平
3. Queue Time 用于 SLA 监控和平台容量规划，不适合直接计费

Queue Time 仍然**被记录**在计量系统中，用于：
- SLA 达标率统计
- 平台容量规划报告
- Dashboard 中的队列分析面板

### 失败构建的计费规则

| 构建状态 | 是否计费 | 原因 |
|---------|---------|------|
| `SUCCESS` | ✅ 是 | 正常消耗资源 |
| `FAILURE` | ✅ 是 | 实际占用了 Agent 和 EC2 资源 |
| `UNSTABLE` | ✅ 是 | 实际占用了资源（测试失败但构建完成）|
| `ABORTED`（Agent 已分配）| ✅ 是 | Agent 已经被分配，资源已消耗 |
| `ABORTED`（队列中中止）| ❌ 否 | Agent 未分配，无资源消耗 |
| `NOT_BUILT` | ❌ 否 | 未执行 |

> **设计理由**：失败构建计费能激励团队优化 Pipeline，减少无效构建。同时，平台无法区分"有价值的失败"和"无价值的重试"，统一计费最为公平。

### 特殊场景处理

**Pipeline 多阶段构建（Parallel stages）**：
- 并行 stage 在同一个 Agent 上运行：按该 Agent 整个构建时长计一次
- 并行 stage 分配到不同 Agent：每个 Agent 的时长分别计费，然后**加总**

**Matrix 构建**：
- 每个 Matrix 维度组合分配独立 Agent：每个 Agent 分别计费

**重试（Retry）**：
- 每次重试作为独立构建记录，分别计费

---

## 维度二：计算资源类型（Node Type）

### EC2 实例规格差异化定价

不同 EC2 实例规格提供不同的计算能力，对应不同单价：

| Node Label | 实例规格 | vCPU | RAM | 适用场景 | EC2 超额单价 |
|-----------|---------|------|-----|---------|------------|
| `ec2-linux-small` | `t3.medium` / `c5.large` | 2 vCPU | 4-8 GB | 轻量测试、脚本任务 | $0.03/min |
| `ec2-linux-medium` | `c5.2xlarge` / `c5.4xlarge` | 8-16 vCPU | 16-32 GB | 标准 Android 构建 | $0.05/min |
| `ec2-linux-large` | `c5.9xlarge` / `c5.18xlarge` | 36-72 vCPU | 72-144 GB | 多模块大型项目构建 | $0.12/min |
| `ec2-linux-gpu` | `g4dn.xlarge` | 4 vCPU + T4 GPU | 16 GB | 机器学习、GPU 测试 | $0.20/min |

> 注：Tier 基础费中包含的配额以 `ec2-linux-medium` 为基准单位。`small` 节点使用会按折算比例（0.6x）抵扣配额，`large` 节点使用按放大比例（2.4x）抵扣配额。

**折算规则示例**：
```
团队使用 ec2-linux-small 10 分钟 → 抵扣配额 = 10 × 0.6 = 6 分钟
团队使用 ec2-linux-large 10 分钟 → 抵扣配额 = 10 × 2.4 = 24 分钟
```

### Mac Mini 定价

Mac Mini 是稀缺的、不可弹性扩展的物理资源，定价显著高于 EC2：

| Node Label | 硬件型号 | 芯片 | RAM | 适用场景 | Mac Mini 超额单价 |
|-----------|---------|------|-----|---------|-----------------|
| `mac-mini-ios-m1` | Mac Mini (2020) | Apple M1 | 16 GB | iOS 构建 | $0.12/min |
| `mac-mini-ios-m2` | Mac Mini (2023) | Apple M2 Pro | 32 GB | iOS 构建（高性能）| $0.15/min |

**Mac Mini 高价的理由**：
1. 物理资源，无法按需伸缩
2. 需要独立采购、维护、折旧
3. 托管在机房，有独立运维成本
4. iOS 构建必须使用 macOS，无替代方案

### 数据采集方法

**Node Label 采集**：
```groovy
// Jenkins Pipeline 中通过 env 获取
def nodeLabel = env.NODE_LABELS
// 或通过 Jenkins API
def node = build.getBuiltOn()
def nodeLabels = node.getLabelString()
```

**Webhook Payload 中的字段**：
```json
{
  "node_name": "mac-mini-prod-03",
  "node_labels": ["mac-mini-ios-m2", "macos", "xcode15"],
  "node_type": "mac-mini-m2"
}
```

平台维护 Node Label → Node Type 的映射表，用于计费分类。

---

## 维度三：构建频率（Build Count）

### 定义

每月该团队在平台上触发的**独立构建次数**（不含 Stage 数量）。

### 为什么需要此维度

1. **防止滥用**：即使每次构建时间很短，大量构建会占用 Jenkins Controller 调度资源
2. **保障公平**：构建次数多的团队消耗更多 Controller CPU 和内存
3. **Tier 分层依据**：构建次数是区分轻量/中量/重量用户的重要指标

### 计量规则

- 仅计算**已分配 Agent 并开始执行**的构建（未分配 Agent 的 `ABORTED` 不计入）
- Pipeline 中的每个 Node Block 如果复用同一 Agent，算作同一次构建
- Matrix 构建的每个组合算作独立构建
- Jenkins 定时触发、Webhook 触发、手动触发均计入

### 配额超额处理

超出月度构建次数上限后：
- Tier 1：超出后每次构建额外收费 $0.10/次
- Tier 2：超出后每次构建额外收费 $0.05/次（次数限制更宽松）
- Tier 3：无构建次数限制

---

## 维度四：存储占用（Storage）

### 存储类型

| 存储类型 | 说明 | 收费方式 |
|---------|------|---------|
| **Artifact 存储（S3）** | 构建产物，如 APK、IPA、日志 | 按 GB/月 计费 |
| **Workspace 缓存（EBS/S3）** | Gradle/Maven/npm 缓存 | 按 GB/月 计费 |
| **构建日志（CloudWatch Logs）** | Jenkins 构建日志 | 按 GB 存储+查询计费 |

### Artifact 存储计费

```
月度 Artifact 存储费 = 月末 S3 存储量(GB) × $0.025/GB/月
```

- 各 Tier 包含免费 Artifact 存储额度（见 Tier 表）
- 超出部分按 $0.025/GB/月 计费（与 AWS S3 Standard 成本对齐）
- 保留策略：默认保留 90 天，超过后自动删除（团队可申请延长）

### Workspace 缓存计费

- 构建缓存存储在共享 S3 bucket 中，以 Team ID 为前缀
- 缓存上限：每个团队 100 GB（可通过 Add-on 购买更多）
- 超出缓存上限后，旧缓存自动 LRU 淘汰

### 数据采集方法

**Artifact 存储采集**：
```python
# 使用 AWS S3 List API 统计每个团队的存储量
s3 = boto3.client('s3')
paginator = s3.get_paginator('list_objects_v2')
total_size = 0
for page in paginator.paginate(Bucket='jenkins-artifacts', Prefix=f'teams/{team_id}/'):
    for obj in page.get('Contents', []):
        total_size += obj['Size']
# 每天统计一次，月末取最大值用于计费
```

---

## 维度五：优先级与 SLA（Priority / SLA）

### 队列优先级如何实现

Jenkins 通过 **Priority Sorter Plugin** 实现队列优先级：

```groovy
// Tier 3 Premium 团队的 Job 配置
properties([
    pipelineTriggers([...]),
    [
        $class: 'PriorityJobProperty',
        jobPriority: 1  // 1=最高, 10=最低
    ]
])
```

| Tier | 队列优先级值 | 说明 |
|------|------------|------|
| Tier 3 Premium | 1-3 | 最高优先级，抢占空闲节点 |
| Tier 2 Standard | 4-6 | 中等优先级 |
| Tier 1 Basic | 7-9 | 标准优先级 |
| 未付费团队 | 10 | 最低优先级，限流 |

### SLA 等级定义

| SLA 指标 | Tier 1 (Basic) | Tier 2 (Standard) | Tier 3 (Premium) |
|---------|---------------|-------------------|-----------------|
| 平均队列等待时间保证 | ≤ 15 min | ≤ 5 min | ≤ 2 min |
| 平台可用性 SLA | 95% | 99% | 99.5% |
| 故障响应时间 | 工作日 4h | 工作日 2h | 7×24 30min |
| 计划维护通知 | 24h 前 | 48h 前 | 72h 前 |
| 年度账单 Review | ❌ | ✅ | ✅ |
| 专属技术支持 | ❌ | ❌ | ✅ |

### 数据采集方法

**Queue Wait Time 采集**：
```json
{
  "queue_entered_at": "2024-01-15T10:00:00Z",
  "build_started_at": "2024-01-15T10:03:27Z",
  "queue_wait_seconds": 207
}
```

通过对比 `queue_entered_at`（Job 进入队列时间）和 `build_started_at`（Agent 分配时间）计算。

---

## 计费精度汇总

| 维度 | 计费精度 | 最小计费单位 | 四舍五入规则 |
|------|---------|------------|------------|
| 构建时长 | 秒级采集，分钟级计费 | 1 分钟 | 向上取整（ceil）|
| 存储 | 每日 GB 快照 | 0.01 GB | 向上取整 |
| 构建次数 | 整数 | 1 次 | 无需取整 |
| 费用金额 | 分 | $0.01 | 四舍五入到分 |

---

## 各维度数据采集来源汇总

| 维度 | 采集来源 | 采集频率 | 存储位置 |
|------|---------|---------|---------|
| 构建时长 | Jenkins Webhook（onStarted + onCompleted）| 实时 | DynamoDB `build_events` |
| Node Type | Jenkins Webhook（node_labels 字段）| 实时 | DynamoDB `build_events` |
| 构建次数 | DynamoDB 聚合 | 月末 | DynamoDB `monthly_usage` |
| Artifact 存储 | AWS S3 List API | 每日 23:59 | DynamoDB `storage_snapshots` |
| Queue Wait Time | Jenkins Webhook（queue_entered_at）| 实时 | DynamoDB `build_events` |
| 构建状态 | Jenkins Webhook（build_result）| 实时 | DynamoDB `build_events` |
