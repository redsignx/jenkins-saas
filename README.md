# Jenkins Build Service — Internal Billing Model

## 项目简介

本仓库包含 **Jenkins Build Service（Jenkins-as-a-Service）** 的完整内部计费模式（Chargeback）设计文档。

Jenkins Build Service 是公司内部统一构建平台，为全公司 100+ 移动端研发团队提供 CI/CD 构建能力：

- **Jenkins Controller**：运行在 AWS 上，统一调度与管理
- **EC2 Build Agents**：通过 EC2 ASG + EC2 Fleet 插件弹性伸缩，支持 Linux 各种规格
- **On-Prem Mac Mini**：专用于 iOS 应用构建，托管在公司自有机房

本文档集合设计了一套完整的内部计费（Chargeback）模式，涵盖定价模型、技术实现、推行策略等全部内容。

---

## 文档目录

| 章节 | 文件 | 内容摘要 |
|------|------|---------|
| 总览 | [docs/README.md](./docs/README.md) | 文档导航、快速开始、关键数字速查 |
| 01 | [计费模式总览](./docs/01-billing-model-overview.md) | 设计目标、架构、核心概念、与财务对接 |
| 02 | [核心计费维度](./docs/02-pricing-dimensions.md) | 构建时长、资源类型、频率、存储、SLA |
| 03 | [分层定价模型](./docs/03-tiered-plans.md) | Tier 1/2/3 完整配额、超额规则、升降级 |
| 04 | [单价定价逻辑](./docs/04-pricing-logic.md) | 成本拆解公式、EC2 + Mac Mini 成本分析 |
| 05 | [附加增值服务](./docs/05-add-on-services.md) | 专属节点、自定义 AMI、Pipeline 模板等 |
| 06 | [计量与计费系统](./docs/06-metering-system.md) | 架构、Webhook 配置、Lambda 代码、DynamoDB 设计 |
| 07 | [Dashboard 设计](./docs/07-billing-dashboard.md) | Grafana 配置、告警规则、优化建议 |
| 08 | [推行策略](./docs/08-rollout-strategy.md) | Phase 0/1/2 时间线、影子账单、沟通模板 |
| 09 | [常见问题](./docs/09-faq.md) | 20 个 Q&A，涵盖计费、Tier、争议处理 |
| 附录 | [系统架构图](./docs/diagrams/architecture.md) | Mermaid 架构图、数据流图、部署架构图 |

---

## 快速导航

### 💰 了解费用

→ [Tier 定价对比](./docs/03-tiered-plans.md#1-tier-总览对比表)  
→ [超额计费规则](./docs/03-tiered-plans.md#2-tier-1--basic详细说明)  
→ [成本计算公式](./docs/04-pricing-logic.md)

### 🔧 技术实现

→ [计量系统架构](./docs/06-metering-system.md)  
→ [Jenkins Webhook 配置](./docs/06-metering-system.md#21-jenkins-webhook-配置方法)  
→ [DynamoDB 表设计](./docs/06-metering-system.md#41-dynamodb-表设计)  
→ [系统架构图](./docs/diagrams/architecture.md)

### 📋 运营推行

→ [推行策略三阶段](./docs/08-rollout-strategy.md)  
→ [影子账单模板](./docs/08-rollout-strategy.md#影子账单设计)  
→ [常见问题解答](./docs/09-faq.md)

### 📊 Dashboard

→ [Dashboard 设计](./docs/07-billing-dashboard.md)  
→ [Grafana 配置示例](./docs/07-billing-dashboard.md#3-grafana-dashboard-json-配置示例)  
→ [告警规则](./docs/07-billing-dashboard.md#4-告警规则设计)

---

## 关键数字速查

| 指标 | Tier 1 Basic | Tier 2 Standard | Tier 3 Premium |
|------|-------------|-----------------|----------------|
| 月基础费 | $500 | $1,800 | $5,000 |
| EC2 配额 | 500 min | 2,000 min | 8,000 min |
| Mac Mini 配额 | 100 min | 500 min | 2,000 min |
| EC2 超额单价 | $0.05/min | $0.04/min | $0.03/min |
| Mac Mini 超额单价 | $0.15/min | $0.12/min | $0.10/min |
| 年付折扣 | 10% | 10% | 15% |

---

## 维护者

本项目由 **Jenkins Build Service Platform Team** 维护。

- 问题反馈：Slack `#jenkins-platform`
- 文档贡献：提交 PR 即可
