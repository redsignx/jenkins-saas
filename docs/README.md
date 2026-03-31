# Jenkins Build Service — 内部计费模式文档

## 项目背景

Jenkins Build Service 是公司内部的统一构建平台，为全公司上百个移动端研发团队提供 CI/CD 构建能力。平台基础设施包括：

- **Jenkins Controller**：运行在 AWS 上，提供统一的任务调度与管理
- **通用 EC2 Build Agent**：通过多个 EC2 Auto Scaling Group（ASG）+ EC2 Fleet 插件弹性提供 Linux 构建能力，支持各种实例规格
- **On-Prem Mac Mini 集群**：专门用于 iOS 应用构建，托管在公司自有机房

随着使用团队不断增长，资源占用与成本归属问题日益突出。本文档集合设计了一套完整的**内部计费（Chargeback）模式**，旨在实现：

- 成本公平分摊，激励各团队合理使用资源
- 为平台团队提供可持续的运营资金
- 为管理层提供透明的成本可视化视图

---

## 文档结构

```
docs/
├── README.md                          ← 本文件：总览与导航
├── 01-billing-model-overview.md       ← 计费模式总览
├── 02-pricing-dimensions.md           ← 核心计费维度详解
├── 03-tiered-plans.md                 ← 分层定价模型
├── 04-pricing-logic.md                ← 单价定价逻辑与成本拆解
├── 05-add-on-services.md              ← 附加增值服务
├── 06-metering-system.md              ← 计量与计费系统架构
├── 07-billing-dashboard.md            ← Dashboard 设计
├── 08-rollout-strategy.md             ← 推行策略与阶段规划
├── 09-faq.md                          ← 常见问题
└── diagrams/
    └── architecture.md                ← 系统架构图（Mermaid）
```

---

## 章节导航

| 序号 | 文件 | 内容摘要 |
|------|------|---------|
| 01 | [计费模式总览](./01-billing-model-overview.md) | 设计目标、整体架构、核心概念、与内部 Chargeback 流程对接 |
| 02 | [核心计费维度](./02-pricing-dimensions.md) | 构建时长、资源类型、频率、存储、SLA 等维度的详细说明 |
| 03 | [分层定价模型](./03-tiered-plans.md) | Tier 1/2/3 完整配额表、超额规则、升降级、年度折扣 |
| 04 | [单价定价逻辑](./04-pricing-logic.md) | 成本拆解公式、EC2 + Mac Mini 完整成本分析、Margin 建议 |
| 05 | [附加增值服务](./05-add-on-services.md) | 专属节点、自定义 AMI、Pipeline 模板等增值服务详细说明 |
| 06 | [计量与计费系统](./06-metering-system.md) | 数据采集、传输、存储、聚合、账单生成的完整架构与示例代码 |
| 07 | [Dashboard 设计](./07-billing-dashboard.md) | 各面板详细说明、Grafana 配置示例、告警规则、优化建议 |
| 08 | [推行策略](./08-rollout-strategy.md) | Phase 0/1/2 时间线、影子账单、沟通模板、KPI、风险管理 |
| 09 | [常见问题](./09-faq.md) | 15+ 个 Q&A，覆盖计费规则、Tier 选择、超额处理、争议解决 |
| 附录 | [系统架构图](./diagrams/architecture.md) | 完整 Mermaid 架构图、数据流图、部署架构图 |

---

## 快速开始指南

### 我是平台团队成员，想了解如何落地计费系统

1. 阅读 [01-计费模式总览](./01-billing-model-overview.md) 了解整体设计理念
2. 阅读 [06-计量与计费系统](./06-metering-system.md) 了解技术实现细节
3. 阅读 [08-推行策略](./08-rollout-strategy.md) 制定落地计划

### 我是业务团队，想了解如何选择 Tier

1. 阅读 [03-分层定价模型](./03-tiered-plans.md) 了解各 Tier 配额
2. 参考 [09-常见问题](./09-faq.md) 中的 Tier 选择指引
3. 联系平台团队申请开通

### 我是财务/管理层，想了解成本归属

1. 阅读 [01-计费模式总览](./01-billing-model-overview.md)
2. 阅读 [08-推行策略](./08-rollout-strategy.md) 中的 Cost Center 对接部分
3. 阅读 [07-Dashboard 设计](./07-billing-dashboard.md) 了解可视化报告

### 我想了解技术架构

1. 参考 [diagrams/architecture.md](./diagrams/architecture.md) 查看整体架构图
2. 阅读 [06-计量与计费系统](./06-metering-system.md) 了解实现细节

---

## 关键数字速查

| 指标 | Tier 1 (Basic) | Tier 2 (Standard) | Tier 3 (Premium) |
|------|---------------|-------------------|-----------------|
| 月基础费 | $500 | $1,800 | $5,000 |
| EC2 配额 | 500 min | 2,000 min | 8,000 min |
| Mac Mini 配额 | 100 min | 500 min | 2,000 min |
| EC2 超额单价 | $0.05/min | $0.04/min | $0.03/min |
| Mac Mini 超额单价 | $0.15/min | $0.12/min | $0.10/min |
| SLA 响应时间 | 工作日 4h | 工作日 2h | 7x24 30min |

---

## 维护者

本文档由 Jenkins Build Service Platform Team 维护。如有问题或建议，请通过内部工单系统提交。

**最后更新**：2024 年  
**文档版本**：v1.0
