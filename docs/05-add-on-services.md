# 附加增值服务（Add-on Services）

本章节详细描述平台提供的增值服务，这些服务超出标准 Tier 的内容，按需购买。

---

## 1. 专属 EC2 ASG（Dedicated EC2 Auto Scaling Group）

### 服务说明

为单个团队创建独立的 EC2 Auto Scaling Group，与其他团队的构建资源完全隔离。

**核心优势**：
- 资源不与其他团队共享，无"嘈杂邻居"问题
- 可定制实例规格和 ASG 策略
- 构建日志和产物访问隔离，满足合规需求
- 独立的 CloudWatch 监控仪表盘

**技术实现**：
- 独立 EC2 Launch Template，可自定义 AMI、实例类型
- 独立 ASG，Min/Max 按需配置
- Jenkins 中配置 Cloud Label 绑定到该 ASG
- 独立 IAM Role，限制 S3 Bucket 访问权限

### 定价

| 配置 | 月费 | 说明 |
|------|------|------|
| 基础专属 ASG（c5.4xlarge × 2-10）| $800/月 | 含 ASG 配置和维护 |
| 高配专属 ASG（c5.9xlarge × 2-8）| $1,500/月 | 含 ASG 配置和维护 |
| 自定义规格 ASG | 按需报价 | 联系平台团队 |

> 注：以上费用为管理费，EC2 实例费用按实际用量从团队配额扣除（或超额计费）。

### 申请流程

1. 通过内部工单系统提交申请，说明：实例规格需求、最大并发数、业务理由
2. 平台团队 1 个工作日内评估并确认方案
3. 配置完成时间：3 个工作日
4. 配置完成后团队进行验收测试
5. 下月 1 日起正式计费

---

## 2. 专属 Mac Mini 节点（Dedicated Mac Mini）

### 服务说明

独占一台 Mac Mini，不与任何其他团队共享，适用于需要保密性或高优先级 iOS 构建的团队。

**核心优势**：
- 独占硬件，零资源竞争
- 可安装特定版本 Xcode 而不影响其他团队
- 可配置特殊 Provisioning Profile 和证书
- 满足 App Store Connect 等需要特定设备的场景
- 构建产物（IPA、dSYM）访问完全隔离

**技术实现**：
- Mac Mini 配置专属 Jenkins Agent，仅对该团队可见
- 独立的 macOS 用户账户，SSH Key 仅团队持有
- 独立的 Keychain，存储代码签名证书
- 独立的 Fastlane Match 配置

### 定价

| 硬件型号 | 月管理费 | 说明 |
|---------|---------|------|
| Mac Mini M1（16GB）| $1,200/月 | 含硬件折旧、托管、运维 |
| Mac Mini M2 Pro（32GB）| $1,800/月 | 含硬件折旧、托管、运维 |

> 以上费用为**全包价**（All-in），包含硬件折旧、机房托管、电力、运维，不额外计费 Build Minutes（独占资源，团队可随意使用）。

### 申请流程

1. 提交申请，说明：所需硬件规格、Xcode 版本要求、代码签名需求
2. 平台团队确认库存（如无现货，采购周期 2-4 周）
3. 配置完成时间：2 个工作日（现货）
4. 团队提供代码签名证书用于配置
5. 验收测试后正式开始计费

---

## 3. 自定义 Build Agent AMI

### 服务说明

为团队定制专属的 EC2 AMI，预装团队所需的构建工具和依赖，无需每次构建时重新安装。

**可定制内容**：
- 特定版本的 Java、Node.js、Python、Go 等语言运行时
- 特定版本的构建工具（Gradle、Maven、Bazel 等）
- 预装的 SDK（Android SDK 特定版本、NDK 等）
- 私有 Registry 的凭证注入
- 企业根证书预装

**技术实现**：
- 基于基础 AMI（Amazon Linux 2023 / Ubuntu 22.04）
- 使用 Packer 自动化构建脚本
- AMI 版本管理（保留最近 3 个版本）
- 集成到 EC2 Launch Template

### 定价

| 服务 | 费用 | 说明 |
|------|------|------|
| 首次 AMI 定制 | $300/次 | 包含需求调研、构建、测试、文档 |
| AMI 更新维护 | $150/次 | 更新工具版本或新增依赖 |
| AMI 月度维护（自动安全补丁）| $200/月 | 自动应用 OS 和关键安全补丁 |

### 申请流程

1. 提交需求文档，包含：OS 类型、工具清单（名称+版本）、依赖说明
2. 平台团队确认可行性和预计时间
3. 制作 AMI：5-7 个工作日
4. 团队在测试环境验收
5. 上线到生产环境，绑定团队 ASG

---

## 4. Pipeline 模板定制

### 服务说明

平台提供标准化 Jenkinsfile 模板，但部分团队有特殊构建流程需求，可申请定制化 Pipeline 模板。

**可定制场景**：
- 特殊的多分支策略（如 GitFlow、Trunk-Based）
- 自定义代码质量门控（SonarQube、特定检查）
- 集成内部工具（内部包管理器、内部安全扫描）
- 自动化灰度发布流水线
- 多平台同步构建流水线（Android + iOS + Server 联动）

**技术交付物**：
- 定制化 Jenkinsfile 模板（支持 Shared Library）
- 使用文档
- 培训（30 分钟录播 or 现场演示）

### 定价

| 服务 | 费用 | 说明 |
|------|------|------|
| 标准模板定制 | $500/次 | 基于现有模板修改，工作量 < 2天 |
| 复杂模板开发 | $1,200/次 | 全新开发，工作量 2-5 天 |
| Shared Library 模块开发 | $800/次 | 公共 Groovy 模块，可被多个 Pipeline 复用 |

### 申请流程

1. 提交需求说明文档（当前 Pipeline 的问题、期望实现的功能）
2. 平台团队需求评审会（30 分钟）
3. 提供方案文档和报价
4. 团队确认方案后开始开发
5. 测试和交付

---

## 5. 额外 Artifact 存储

### 服务说明

超出 Tier 默认配额的额外 S3 Artifact 存储空间，支持自定义保留策略。

**特性**：
- 存储在专属 S3 Bucket 前缀下（`s3://jenkins-artifacts/teams/{team_id}/`）
- 支持自定义保留天数（30/60/90/180/365 天）
- 支持 S3 生命周期规则（如 90 天后转 Glacier）
- 支持 S3 版本控制（保留多个版本的构建产物）

### 定价

| 存储类型 | 单价 | 说明 |
|---------|------|------|
| S3 Standard 存储 | $0.025/GB/月 | 频繁访问的产物 |
| S3 Standard-IA 存储 | $0.015/GB/月 | 30 天后自动转 IA |
| S3 Glacier 存储 | $0.005/GB/月 | 90 天后自动转 Glacier |

**推荐策略（生命周期规则）**：
```
0-30 天 → S3 Standard（$0.025/GB/月）
30-90 天 → S3 Standard-IA（$0.015/GB/月）
90-365 天 → S3 Glacier Instant Retrieval（$0.005/GB/月）
365 天+ → 自动删除（或转 Glacier Deep Archive）
```

---

## 6. 构建缓存加速

### 服务说明

为团队提供专属的高速构建缓存服务，显著减少构建时间（通常减少 30%~60%）。

**技术方案**：
- **Gradle/Maven 缓存**：团队专属 S3 bucket 前缀，Gradle Build Cache 远程模式
- **Docker Layer 缓存**：私有 ECR 存储 Docker layer，避免重复拉取
- **npm/yarn 缓存**：共享 S3 缓存 + 本地 SSD 预热（LRU 淘汰）
- **Android SDK 预热 AMI**：将 Android SDK 打包进 AMI，省去下载时间

**实现原理**：
```groovy
// Gradle 远程缓存配置（在团队的 settings.gradle 中）
buildCache {
    remote(HttpBuildCache) {
        url = 'https://gradle-cache.jenkins-internal.company.com/cache/'
        credentials {
            username = System.getenv('GRADLE_CACHE_USER')
            password = System.getenv('GRADLE_CACHE_PASS')
        }
        push = true
        enabled = true
    }
}
```

### 定价

| 服务 | 月费 | 说明 |
|------|------|------|
| Gradle/Maven 远程缓存 | $200/月 | 含 20 GB 专属缓存空间 |
| npm/yarn 缓存 | $150/月 | 含 10 GB 专属缓存空间 |
| Docker Layer 缓存（ECR）| $100/月 | 含 50 GB ECR 存储 |
| **全套缓存套餐** | **$350/月** | 以上全部，8折优惠 |

> 💡 **ROI 估算**：如果团队月均 EC2 构建 2,000 分钟，缓存可节省 30% = 600 分钟，按 Tier 2 超额单价 $0.04/min 折算节省 $24，缓存费用 $200，纯粹节省不划算，但缓存**降低等待时间**的价值远不止于此（开发效率 + 心理体验）。

---

## 7. 构建结果通知集成

### 服务说明

将 Jenkins 构建结果自动推送到团队的通信工具（Slack、企业微信、钉钉、飞书等）。

**标准集成（免费）**：
- Slack Webhook 通知（构建成功/失败）
- 邮件通知

**高级集成（付费）**：
- 构建状态卡片（包含链接、时长、变更记录）
- @相关人通知（基于 Git commit author）
- 失败自动创建 Jira / 内部工单
- 与 DingTalk / 企业微信机器人深度集成
- 多环境聚合通知（dev/staging/prod 构建状态汇总）

### 定价

| 服务 | 费用 |
|------|------|
| 标准 Slack/Email 通知 | **免费** |
| 高级通知集成（自定义卡片 + @通知）| $100/月 |
| Jira 自动建单集成 | $150/月 |
| 多环境聚合通知 | $200/月 |

### 申请流程

1. 提交申请，附上 Webhook URL 或 API Key
2. 平台团队配置完成时间：1 个工作日
3. 验证测试
4. 高级功能当月即时计费

---

## Add-on 服务汇总表

| Add-on | 月费 | 一次性费 | 适用 Tier |
|--------|------|---------|---------|
| 专属 EC2 ASG（基础）| $800/月 | — | Tier 2 及以上 |
| 专属 EC2 ASG（高配）| $1,500/月 | — | Tier 3 |
| 专属 Mac Mini M1 | $1,200/月 | — | 任意 Tier |
| 专属 Mac Mini M2 Pro | $1,800/月 | — | 任意 Tier |
| 自定义 AMI（首次）| — | $300/次 | 任意 Tier |
| 自定义 AMI 月维护 | $200/月 | — | 任意 Tier |
| Pipeline 模板定制（标准）| — | $500/次 | 任意 Tier |
| Pipeline 模板定制（复杂）| — | $1,200/次 | 任意 Tier |
| 额外 Artifact 存储 | $0.025/GB/月 | — | 任意 Tier |
| 全套构建缓存 | $350/月 | — | 任意 Tier |
| 高级通知集成 | $100/月 | — | 任意 Tier |
| Jira 自动建单 | $150/月 | — | 任意 Tier |
