# PRD: 低库存预警与自动询价系统

# Low Inventory Alert & Automated Quotation System

| 字段 Field | 值 Value |
|---|---|
| 文档版本 Version | 1.0 |
| 创建日期 Created | 2026-03-14 |
| 作者 Author | Warehouse Automation Team |
| 状态 Status | Draft |
| 产品代号 Codename | **InventoryGuard** |
| 目标上线 Target Launch | 2026-Q2 |

---

## 1. Executive Summary 执行摘要

本文档定义"低库存预警与自动询价系统"（InventoryGuard）的产品需求。该系统旨在解决中小型仓库在库存管理中普遍存在的**被动补货**问题——仓管人员往往在缺货已经发生后才意识到需要采购，而手工比价流程又进一步拉长了补货周期。

InventoryGuard will continuously monitor inventory levels against configurable per-SKU thresholds, automatically scrape supplier websites for real-time quotations, generate formatted comparison reports, and push multi-channel notifications (email, DingTalk/WeCom webhook) to stakeholders. The system runs as a scheduled task (Windows Task Scheduler, daily at 02:00) to ensure alerts are ready before the morning shift begins.

**Core value proposition**: Transform inventory replenishment from a reactive, manual process into a proactive, data-driven workflow — reducing stockout incidents by ≥60% and procurement cycle time by ≥40%.

---

## 2. Problem Statement 问题陈述

### 2.1 Empathy-Driven Problem Framing

> **I am** 仓库管理员小王 (Warehouse Manager Wang), **trying to** keep stock levels healthy across 2,000+ SKUs and find the best supplier prices when replenishment is needed, **but** I only discover shortages when a picker reports an empty shelf, and then I have to spend 2-3 hours manually checking 5+ supplier websites to compare prices — by which time production may already be delayed.

> **I am** 采购主管李姐 (Procurement Lead Li), **trying to** make cost-effective purchasing decisions with full price visibility, **but** the quotes my team collects are scattered across WeChat messages, emails, and handwritten notes, making it impossible to do a fair apples-to-apples comparison before the purchase deadline.

> **I am** 运营总监陈总 (Operations Director Chen), **trying to** reduce carrying costs while maintaining a 99% order fulfillment rate, **but** I lack real-time visibility into which SKUs are approaching critical levels, and I cannot quantify how much we overspend due to emergency purchasing at unfavorable prices.

### 2.2 Current Pain Points 当前痛点

| # | Pain Point 痛点 | Impact 影响 | Frequency 频率 |
|---|---|---|---|
| 1 | 库存数据分散在多个 Excel 和旧版 SQL 系统中 | 无法全局掌握库存水位 | 每天 |
| 2 | 阈值管理靠人脑记忆或纸质记录 | 高价值/长交期物料与低价值物料使用相同补货逻辑 | 每次补货 |
| 3 | 手动逐个登录供应商网站询价 | 每次询价耗时 2-3 小时，且容易遗漏供应商 | 每周 2-3 次 |
| 4 | 比价结果无统一格式 | 决策依赖个人经验，缺乏审计追踪 | 每次采购 |
| 5 | 缺货预警靠人工巡仓发现 | 平均发现延迟 4-8 小时，生产线停工风险 | 每月 5-10 次 |

---

## 3. Proto-Personas 用户角色

### Persona 1: 仓管员小王 — "The Floor Operator"

| 维度 | 描述 |
|---|---|
| **Identity 身份** | 王建国，28 岁，某制造企业仓库管理员，工作 3 年。每天管理约 2,000 个 SKU 的出入库。 |
| **Voice 声音** | "我每天早上最怕的就是打开系统发现又有几个料缺货了，生产那边催得很急，但我昨天下班前明明检查过的啊……要是系统能自动提醒我就好了。" |
| **Context 场景** | 使用公司内部 Excel 表和一套老旧的 SQL Server 库存系统。日常工作在仓库和办公区之间来回。主要通过钉钉群接收工作通知。电脑水平一般，能用 Excel 但不会写公式。 |
| **Goals 目标** | 不再因为缺货被生产部投诉；减少每天花在库存盘点上的时间。 |
| **Frustrations 痛点** | 多个数据源无法联动；手工比对容易出错；供应商报价信息散落各处。 |

### Persona 2: 采购主管李姐 — "The Cost Optimizer"

| 维度 | 描述 |
|---|---|
| **Identity 身份** | 李敏，35 岁，采购部主管，管理 3 人采购团队。负责年度采购预算约 800 万元。 |
| **Voice 声音** | "我需要看到所有供应商的报价放在一张表里，横向对比单价、交期、最小起订量。现在每次都是下面的人用微信截图发给我，我还得自己整理成 Excel，效率太低了。" |
| **Context 场景** | 日常使用 Excel 做采购分析。需要在采购前获得至少 3 家供应商的报价。通过企业微信与团队协作。对数据格式和准确性要求高。 |
| **Goals 目标** | 将采购比价时间从 3 小时缩短到 30 分钟；确保每笔采购都有完整的比价记录。 |
| **Frustrations 痛点** | 报价信息格式不统一；无法快速判断哪家供应商性价比最高；历史价格趋势无从追溯。 |

### Persona 3: 运营总监陈总 — "The Strategic Decider"

| 维度 | 描述 |
|---|---|
| **Identity 身份** | 陈浩，42 岁，运营总监，向 VP 汇报。关注整体运营效率和成本控制。 |
| **Voice 声音** | "我不需要看每一个 SKU 的细节，但我需要一个 dashboard 告诉我：今天有多少个高风险缺货 SKU？本月紧急采购占比多少？跟上月比是好了还是坏了？" |
| **Context 场景** | 主要通过邮件和钉钉接收报告。每周一早会需要库存健康度数据。关注 KPI 趋势而非操作细节。 |
| **Goals 目标** | 将缺货率控制在 1% 以下；紧急采购占比降至 5% 以下。 |
| **Frustrations 痛点** | 缺乏实时数据支持决策；问题总是在造成损失后才暴露。 |

---

## 4. Solution Overview 解决方案概述

### 4.1 System Architecture 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Windows Task Scheduler                      │
│                  (Trigger: Daily 02:00)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  InventoryGuard Main Process                  │
│                                                              │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │ Data Loader  │──▶│ Threshold    │──▶│ Alert Generator  │  │
│  │ (Excel/SQL)  │   │ Comparator   │   │                  │  │
│  └─────────────┘   └──────────────┘   └────────┬─────────┘  │
│                                                 │            │
│  ┌─────────────────────────────────────────────▼──────────┐  │
│  │              Quotation Engine                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │  │
│  │  │ Playwright  │  │ Price      │  │ Report Generator │  │  │
│  │  │ Scraper    │  │ Normalizer │  │ (openpyxl/xlsx)  │  │  │
│  │  └────────────┘  └────────────┘  └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Notification Dispatcher                    │  │
│  │  ┌─────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │ Email   │  │ DingTalk     │  │ WeCom Webhook    │  │  │
│  │  │ (SMTP)  │  │ Webhook      │  │                  │  │  │
│  │  └─────────┘  └──────────────┘  └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Core Modules 核心模块

#### Module 1: Data Loader 数据加载器
- **输入源 Input Sources**:
  - Excel files (`.xlsx` / `.xls`) — 通过 `openpyxl` / `xlrd` 读取
  - SQL Server / SQLite databases — 通过 `pyodbc` / `sqlite3` 读取
- **配置方式**: YAML config file 指定数据源类型、连接串/文件路径、sheet 名、列映射
- **输出**: Unified `pandas.DataFrame` with columns: `sku_code`, `sku_name`, `current_qty`, `unit`, `category`, `last_updated`

#### Module 2: Threshold Comparator 阈值比较器
- **阈值配置**: Per-SKU thresholds in a dedicated Excel/YAML file
  - `min_qty`: 最低库存量（触发预警）
  - `reorder_qty`: 建议补货量
  - `lead_time_days`: 供应商交期（天）
  - `priority`: `critical` / `high` / `medium` / `low`
- **比较逻辑**: `current_qty <= min_qty` → 触发预警
- **输出**: List of `AlertItem` objects with SKU info + deficit quantity + priority

#### Module 3: Supplier Quotation Scraper 供应商报价爬虫
- **技术栈**: Playwright (async, Chromium headless)
- **供应商配置**: Per-supplier scraping rules in YAML
  - Login credentials (encrypted via `cryptography.Fernet`)
  - Search URL template
  - CSS selectors for price, MOQ, delivery time
  - Rate limiting / retry config
- **Anti-detection**: Random delays, viewport rotation, User-Agent randomization
- **输出**: `QuotationResult` per supplier per SKU

#### Module 4: Report Generator 报告生成器
- **格式**: `.xlsx` with multiple sheets
  - Sheet 1: 库存预警汇总 (Alert Summary)
  - Sheet 2: 供应商报价对比 (Quotation Comparison)
  - Sheet 3: 建议采购清单 (Recommended Purchase List)
- **Conditional Formatting 条件格式**:
  - 红色背景: `current_qty == 0` (已缺货)
  - 橙色背景: `current_qty <= min_qty * 0.5` (严重不足)
  - 黄色背景: `current_qty <= min_qty` (低于阈值)
  - 绿色高亮: 最低报价供应商
- **技术实现**: `openpyxl` with `ConditionalFormatting` rules

#### Module 5: Notification Dispatcher 通知分发器
- **Email**: SMTP with TLS, HTML body with summary table + attached xlsx report
- **DingTalk Webhook 钉钉机器人**: Markdown message with top-10 critical alerts + report download link
- **WeCom Webhook 企业微信机器人**: Same as DingTalk, adapted for WeCom API format
- **通知策略**:
  - `critical` priority → 立即推送全部渠道
  - `high` priority → 邮件 + 主渠道 webhook
  - `medium` / `low` → 仅包含在 daily report 中

### 4.3 Scheduling 调度方式

- **Primary**: Windows Task Scheduler, daily at `02:00 AM`
- **Reason**: 凌晨运行避免与日间业务争抢网络/数据库资源；早班员工 08:00 到岗时报告已就绪
- **Fallback**: 支持手动触发 (`python -m inventory_guard --run-now`)
- **Logging**: Rotating file log (`logs/inventory_guard_YYYYMMDD.log`) + error-level notifications

---

## 5. Success Metrics 成功指标

### 5.1 Primary KPIs 核心指标

| # | Metric 指标 | Current Baseline 当前基线 | Target 目标 | Measurement 测量方式 |
|---|---|---|---|---|
| 1 | 缺货发现延迟 Stockout Detection Delay | 4-8 hours (manual discovery) | < 30 minutes (next scheduled run) | Timestamp of alert vs. inventory drop below threshold |
| 2 | 询价耗时 Quotation Collection Time | 2-3 hours per batch | < 15 minutes (automated) | Log timestamps: scrape start → report generated |
| 3 | 缺货事件数 Monthly Stockout Incidents | ~10 per month | ≤ 4 per month (↓60%) | WMS stockout event count |
| 4 | 紧急采购占比 Emergency Purchase Ratio | ~20% of all POs | ≤ 8% of all POs | PO classification in procurement system |
| 5 | 采购成本节省 Procurement Cost Savings | Baseline (month 1) | ↓10% by month 3 | Average unit cost comparison, pre vs. post |

### 5.2 Secondary KPIs 辅助指标

| # | Metric 指标 | Target 目标 |
|---|---|---|
| 6 | 系统可用率 System Uptime | ≥ 99% (允许每月 < 7.2 小时停机) |
| 7 | 报告准确率 Report Accuracy | ≥ 98% (inventory qty matches source) |
| 8 | 爬虫成功率 Scraper Success Rate | ≥ 90% per supplier per run |
| 9 | 通知送达率 Notification Delivery Rate | ≥ 99% |
| 10 | 用户满意度 User Satisfaction (NPS) | ≥ 70 after 3 months |

---

## 6. User Stories 用户故事

### User Story 1: 查看每日低库存预警报告

> **As a** 仓库管理员 (warehouse operator),
> **I want** to receive an automated daily report listing all SKUs below their minimum threshold,
> **so that** I can prioritize replenishment before stockouts impact production.

**Story Points**: 5 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Daily Low Inventory Alert Report

  Background:
    Given the system is configured with inventory data sources (Excel and/or SQL)
    And per-SKU threshold configurations exist in the threshold config file
    And the scheduled task is registered in Windows Task Scheduler for 02:00 daily

  Scenario: Generate alert for SKUs below minimum threshold
    Given SKU "WH-BOLT-M8" has current_qty of 50
    And SKU "WH-BOLT-M8" has min_qty threshold of 100
    When the daily inventory check runs at 02:00
    Then SKU "WH-BOLT-M8" should appear in the alert list
    And the deficit quantity should be calculated as 50
    And the alert priority should be determined by the SKU's configured priority level

  Scenario: No alert for SKUs above threshold
    Given SKU "WH-NUT-M6" has current_qty of 500
    And SKU "WH-NUT-M6" has min_qty threshold of 200
    When the daily inventory check runs
    Then SKU "WH-NUT-M6" should NOT appear in the alert list

  Scenario: Handle zero-stock items with critical priority
    Given SKU "WH-WASHER-M10" has current_qty of 0
    And SKU "WH-WASHER-M10" has min_qty threshold of 100
    When the daily inventory check runs
    Then SKU "WH-WASHER-M10" should appear in the alert list with priority "critical"
    And the report row should be highlighted with red background
```

---

### User Story 2: 自动抓取供应商报价并生成比价报告

> **As a** 采购主管 (procurement lead),
> **I want** the system to automatically scrape supplier websites for the latest prices of low-stock SKUs,
> **so that** I can make purchasing decisions based on a consolidated, formatted comparison report without manual data collection.

**Story Points**: 13 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Automated Supplier Quotation Scraping

  Background:
    Given the following suppliers are configured in supplier_config.yaml:
      | supplier_name | website_url              | enabled |
      | 供应商A       | https://supplier-a.com   | true    |
      | 供应商B       | https://supplier-b.com   | true    |
      | 供应商C       | https://supplier-c.com   | true    |
    And Playwright browser engine is available in headless mode

  Scenario: Successfully scrape prices from all configured suppliers
    Given 3 SKUs have been flagged as below threshold
    When the quotation engine runs for each flagged SKU
    Then the system should query each enabled supplier for each SKU
    And collect unit_price, moq (minimum order quantity), and estimated_delivery_days
    And store results in a structured QuotationResult format

  Scenario: Handle supplier website unavailability gracefully
    Given 供应商B's website returns HTTP 503
    When the quotation engine attempts to scrape 供应商B
    Then the system should retry up to 3 times with exponential backoff
    And if all retries fail, mark 供应商B as "unreachable" in the report
    And continue scraping remaining suppliers without blocking

  Scenario: Generate xlsx comparison report with conditional formatting
    Given quotation results have been collected from 3 suppliers for SKU "WH-BOLT-M8"
    And supplier prices are: 供应商A=¥0.85, 供应商B=¥0.72, 供应商C=¥0.91
    When the report generator creates the comparison sheet
    Then the lowest price (¥0.72, 供应商B) should be highlighted in green
    And the report should include columns: SKU, 供应商, 单价, MOQ, 交期, 总价(按建议补货量)
    And the report file should be saved as inventory_alert_report_20260314.xlsx

  Scenario: Apply rate limiting to avoid supplier website blocking
    Given the scraper is configured with min_delay=2s and max_delay=5s between requests
    When scraping prices for 10 SKUs from 供应商A
    Then each request should be separated by a random delay between 2-5 seconds
    And the total scraping time for 供应商A should be at least 20 seconds
```

---

### User Story 3: 多渠道通知预警消息

> **As a** 运营总监 (operations director),
> **I want** to receive inventory alerts through email and IM webhooks (DingTalk/WeCom),
> **so that** I am immediately aware of critical stock situations even before opening any reports.

**Story Points**: 5 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Multi-Channel Alert Notifications

  Scenario: Send email notification with report attachment
    Given the daily run has generated an alert report with 5 critical SKUs
    And email recipients are configured as ["wang@company.com", "li@company.com"]
    When the notification dispatcher processes the alerts
    Then an HTML email should be sent to all configured recipients
    And the email subject should contain the date and alert count: "[InventoryGuard] 2026-03-14 低库存预警: 5个SKU需关注"
    And the email body should contain a summary table of top critical alerts
    And the xlsx report should be attached to the email

  Scenario: Send DingTalk webhook notification
    Given the DingTalk webhook URL is configured in notification_config.yaml
    And there are 2 critical-priority alerts
    When the notification dispatcher sends to DingTalk
    Then a Markdown-formatted message should be posted to the DingTalk webhook
    And the message should include: alert count, top critical SKU names, and a prompt to check email for the full report
    And the HTTP response status should be 200

  Scenario: Send WeCom webhook notification
    Given the WeCom webhook key is configured
    When the notification dispatcher sends to WeCom
    Then a Markdown-formatted message should be posted to the WeCom webhook endpoint
    And the message format should conform to WeCom Bot API specification

  Scenario: Notification routing based on priority
    Given alerts include: 2 critical, 3 high, 10 medium SKUs
    When the notification dispatcher processes the alerts
    Then critical alerts should trigger: email + DingTalk + WeCom
    And high alerts should trigger: email + primary webhook channel
    And medium alerts should be included only in the email report attachment
```

---

### User Story 4: 配置和管理 SKU 阈值

> **As a** 仓库管理员 (warehouse operator),
> **I want** to configure minimum stock thresholds, reorder quantities, and priority levels for each SKU,
> **so that** the alert system respects the unique replenishment needs of different materials (e.g., long-lead-time items need higher safety stock).

**Story Points**: 3 | **Priority**: P1-Should Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: SKU Threshold Configuration

  Scenario: Load thresholds from configuration file
    Given a threshold config file exists at config/thresholds.yaml (or thresholds.xlsx)
    And it contains entries:
      | sku_code     | min_qty | reorder_qty | lead_time_days | priority |
      | WH-BOLT-M8  | 100     | 500         | 7              | high     |
      | WH-NUT-M6   | 200     | 1000        | 3              | medium   |
    When the system loads threshold configuration
    Then each SKU should have its own threshold parameters
    And SKUs not in the config file should use default thresholds (min_qty=50, priority=low)

  Scenario: Support bulk import of thresholds via Excel
    Given a user prepares an Excel file with 500 SKU threshold entries
    When the file is placed in the config directory and the system reloads
    Then all 500 thresholds should be loaded successfully
    And any duplicate SKU entries should use the last occurrence with a warning logged

  Scenario: Validate threshold configuration on load
    Given a threshold entry has min_qty set to -10
    When the system loads the configuration
    Then a validation error should be logged for that entry
    And the system should skip the invalid entry and continue loading others
    And the daily run should still proceed with valid entries
```

---

### User Story 5: 查看历史预警趋势

> **As a** 运营总监 (operations director),
> **I want** the system to retain historical alert data and generate trend summaries,
> **so that** I can track whether our inventory health is improving over time and justify the system's ROI.

**Story Points**: 5 | **Priority**: P1-Should Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Historical Alert Trend Tracking

  Scenario: Persist daily alert results to history database
    Given the daily run generates 15 alerts on 2026-03-14
    When the run completes successfully
    Then all 15 alert records should be saved to the history table (SQLite)
    And each record should include: run_date, sku_code, current_qty, min_qty, deficit, priority

  Scenario: Generate weekly trend summary
    Given alert history exists for the past 7 days
    When the weekly summary is triggered (every Monday)
    Then the system should calculate:
      | metric                    | description                     |
      | total_alerts_this_week    | Sum of daily unique SKU alerts  |
      | trend_vs_last_week        | % change from previous week     |
      | top_5_recurring_skus      | SKUs appearing most frequently  |
      | avg_deficit_by_category   | Average deficit grouped by category |
    And the summary should be included in the Monday notification

  Scenario: Retain history for at least 90 days
    Given alert history data older than 90 days exists
    When the daily cleanup job runs
    Then records older than 90 days should be archived to a compressed CSV
    And the SQLite database should only contain the last 90 days of data
```

---

### User Story 6: 手动触发预警检查

> **As a** 仓库管理员 (warehouse operator),
> **I want** to manually trigger an inventory check and report at any time,
> **so that** I can get an immediate status update when an urgent situation arises without waiting for the next scheduled run.

**Story Points**: 2 | **Priority**: P1-Should Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Manual Trigger for Inventory Check

  Scenario: Run inventory check via command line
    Given the system is installed and configured
    When the user executes: python -m inventory_guard --run-now
    Then the full pipeline should execute: data load → threshold check → scrape → report → notify
    And the process should output progress to stdout in real-time
    And the final report should be saved with a timestamp in the filename

  Scenario: Run check without scraping (fast mode)
    Given the user only needs an inventory status update without quotations
    When the user executes: python -m inventory_guard --run-now --skip-scrape
    Then the system should only perform: data load → threshold check → report (no quotation columns)
    And the total runtime should be under 60 seconds
    And notifications should still be sent

  Scenario: Prevent concurrent runs
    Given a scheduled run is already in progress
    When a manual run is triggered
    Then the system should detect the lock file and exit with a message: "另一个实例正在运行，请稍后再试"
    And no duplicate run should execute
```

---

### User Story 7: 供应商配置与凭证管理

> **As a** 系统管理员 (system administrator),
> **I want** to securely configure supplier website credentials and scraping rules,
> **so that** the quotation scraper can access supplier portals without exposing passwords in plain text.

**Story Points**: 3 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Supplier Configuration and Credential Management

  Scenario: Encrypt supplier credentials
    Given a new supplier "供应商D" needs to be configured
    When the admin runs: python -m inventory_guard config add-supplier
    And provides the supplier URL, username, and password
    Then the password should be encrypted using Fernet symmetric encryption
    And stored in supplier_config.yaml as an encrypted string
    And the encryption key should be stored separately in a key file with restricted permissions

  Scenario: Configure scraping selectors for a new supplier
    Given the admin needs to add CSS selectors for 供应商D's product page
    When the admin edits supplier_config.yaml with:
      | field          | selector                    |
      | price          | .product-price .value       |
      | moq            | .min-order-qty              |
      | delivery_time  | .delivery-estimate span     |
    Then the scraper should be able to extract these fields from 供应商D's pages

  Scenario: Disable a supplier without removing configuration
    Given 供应商C is temporarily offline for maintenance
    When the admin sets enabled=false for 供应商C in supplier_config.yaml
    Then the daily scraping run should skip 供应商C
    And the report should note "供应商C: 已禁用 (disabled)" instead of showing an error
```

---

## 7. Scope 范围

### 7.1 In Scope 范围内

| # | Feature 功能 | Description 描述 |
|---|---|---|
| 1 | 多源数据加载 | 支持从 Excel (.xlsx/.xls) 和 SQL (SQL Server, SQLite) 读取库存数据 |
| 2 | 可配置阈值 | Per-SKU 阈值配置，支持 YAML 和 Excel 格式 |
| 3 | 自动化爬虫询价 | 基于 Playwright 的无头浏览器爬虫，支持多供应商 |
| 4 | 比价报告生成 | 带条件格式的 xlsx 报告，包含预警汇总、报价对比、建议采购清单 |
| 5 | 多渠道通知 | Email (SMTP/TLS) + 钉钉 Webhook + 企业微信 Webhook |
| 6 | 定时调度 | Windows Task Scheduler 每日凌晨 2:00 执行 |
| 7 | 手动触发 | 支持命令行手动执行，含快速模式（跳过爬虫） |
| 8 | 凭证加密 | 供应商登录凭证 Fernet 加密存储 |
| 9 | 历史数据存储 | SQLite 存储 90 天预警历史，支持趋势分析 |

### 7.2 Out of Scope 范围外

| # | Feature 功能 | Reason 原因 | Future Phase 未来阶段 |
|---|---|---|---|
| 1 | 自动下采购单 Auto-PO creation | 风险过高，需人工审批环节 | Phase 2 |
| 2 | Web UI 管理界面 | 当前用户习惯命令行 + Excel，优先 MVP | Phase 2 |
| 3 | 需求预测 Demand forecasting | 需要历史销售数据和 ML 模型，复杂度高 | Phase 3 |
| 4 | 多仓库支持 Multi-warehouse | 当前仅 1 个仓库，暂不需要 | Phase 2 |
| 5 | Mobile app 移动端 | Webhook 通知已覆盖移动场景 | Phase 3 |
| 6 | ERP 直连 Direct ERP integration | 需 ERP 厂商配合，周期长 | Phase 2 |
| 7 | 供应商 API 对接 Supplier API | 多数供应商无公开 API，先用爬虫方案 | Phase 2 |

---

## 8. Risks & Mitigations 风险与缓解措施

| # | Risk 风险 | Probability 概率 | Impact 影响 | Mitigation 缓解措施 |
|---|---|---|---|---|
| 1 | **供应商网站改版导致爬虫失效** Supplier website redesign breaks scraper | High 高 | High 高 | 模块化 selector 配置，便于快速更新；每次运行记录 scraping 成功率；连续 3 次失败触发管理员告警 |
| 2 | **供应商反爬机制升级** Anti-scraping measures (CAPTCHA, IP blocking) | Medium 中 | High 高 | Random delays + User-Agent rotation + viewport randomization；考虑代理 IP 池；降级策略：标记为"需人工询价" |
| 3 | **数据源格式变更** Excel column/SQL schema changes | Medium 中 | Medium 中 | 列映射通过配置文件管理，非硬编码；启动时验证列是否存在，缺失时明确报错 |
| 4 | **邮件/Webhook 送达失败** Notification delivery failure | Low 低 | Medium 中 | 多渠道冗余（邮件 + 2 个 webhook）；发送失败自动重试 3 次；本地日志保留完整报告 |
| 5 | **凌晨运行时数据库维护** Database maintenance window at 02:00 | Low 低 | Medium 中 | 支持配置调度时间；失败时自动延迟 30 分钟重试，最多重试 3 次 |
| 6 | **敏感凭证泄露** Credential exposure | Low 低 | Critical 极高 | Fernet 加密存储；密钥文件设置严格权限 (600)；.gitignore 排除所有配置含凭证的文件 |
| 7 | **Playwright 浏览器更新不兼容** Browser engine compatibility | Low 低 | Low 低 | Pin Playwright version in requirements.txt；定期更新并测试 |

---

## Appendix A: Technical Dependencies 技术依赖

| Package | Version | Purpose |
|---|---|---|
| Python | ≥ 3.10 | Runtime |
| pandas | ≥ 2.0 | Data loading and manipulation |
| openpyxl | ≥ 3.1 | Excel read/write with formatting |
| xlrd | ≥ 2.0 | Legacy .xls file support |
| playwright | ≥ 1.40 | Headless browser automation |
| pyodbc | ≥ 5.0 | SQL Server connectivity |
| cryptography | ≥ 41.0 | Fernet encryption for credentials |
| pyyaml | ≥ 6.0 | Configuration file parsing |
| requests | ≥ 2.31 | Webhook HTTP calls |
| Jinja2 | ≥ 3.1 | HTML email template rendering |

## Appendix B: Configuration File Structure 配置文件结构

```yaml
# config/main_config.yaml
inventory_sources:
  - type: excel
    path: "data/inventory_current.xlsx"
    sheet: "库存总表"
    column_mapping:
      sku_code: "物料编码"
      sku_name: "物料名称"
      current_qty: "当前库存"
      unit: "单位"
      category: "分类"

  - type: sql
    driver: "ODBC Driver 17 for SQL Server"
    server: "192.168.1.100"
    database: "WarehouseDB"
    query: "SELECT sku_code, sku_name, current_qty, unit, category FROM v_inventory_current"

thresholds:
  config_file: "config/thresholds.xlsx"
  defaults:
    min_qty: 50
    reorder_qty: 200
    lead_time_days: 7
    priority: "low"

notifications:
  email:
    enabled: true
    smtp_server: "smtp.company.com"
    smtp_port: 587
    use_tls: true
    sender: "inventory-guard@company.com"
    recipients:
      - "wang@company.com"
      - "li@company.com"
      - "chen@company.com"
  dingtalk:
    enabled: true
    webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxxxx"
    secret: "SECxxxxx"
  wecom:
    enabled: true
    webhook_key: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

schedule:
  cron_time: "02:00"
  retry_on_failure: true
  max_retries: 3
  retry_delay_minutes: 30
```

---

*Document generated on 2026-03-14. This is a living document and will be updated as the project evolves.*
