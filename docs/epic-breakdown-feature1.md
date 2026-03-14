# Epic Breakdown: 低库存预警与自动询价

**Feature:** 低库存预警与自动询价 (Low Stock Alert & Auto-Inquiry)
**Date:** 2026-03-14
**Splitting Method:** Richard Lawrence's 9 Splitting Patterns
**Total Epics:** 5

---

## Epic 1: 数据提取 (Data Extraction)

**Splitting Pattern Used:** #1 — Workflow Steps
> 将整体工作流的第一步——数据获取——拆分为独立 Epic，使后续检测、报价、报表等步骤可基于统一数据模型独立开发。

### 描述

本 Epic 聚焦于从多种异构数据源（Excel 文件、SQL Server、MySQL）中提取库存数据，并将其映射到统一的 `InventoryRecord` 数据模型。系统需支持 Excel 列名自动映射（模糊匹配中英文列名），同时提供关系型数据库的连接与查询能力，确保下游模块获得结构一致、质量可控的库存快照。

### User Stories

**US-1.1: Excel 数据源导入与列自动映射**
> 作为仓库管理员，我希望系统能读取我上传的 Excel 库存表并自动识别列名（如"商品名称""数量""SKU"），这样我不必每次手动配置列映射。

**验收标准 (Acceptance Criteria):**
- [ ] 支持 `.xlsx` 和 `.xls` 格式文件读取
- [ ] 自动匹配至少以下列名变体：`商品名称/产品名/product_name`、`库存数量/数量/qty/quantity`、`SKU/sku/货号`
- [ ] 模糊匹配准确率 ≥ 95%（基于预定义的 20 组测试列名）
- [ ] 匹配失败时返回未匹配列清单，提示用户手动映射
- [ ] 处理含多 Sheet 的 Excel 文件时，默认取第一个 Sheet 或用户指定 Sheet

**US-1.2: SQL Server / MySQL 数据库数据源**
> 作为 IT 运维人员，我希望系统能通过配置文件连接公司的 SQL Server 或 MySQL 数据库，定时拉取最新库存数据，这样可以保证数据实时性。

**验收标准 (Acceptance Criteria):**
- [ ] 支持通过 YAML/JSON 配置文件指定数据库连接串（host, port, database, user, password）
- [ ] 密码字段支持环境变量引用（如 `${DB_PASSWORD}`），不硬编码
- [ ] 支持自定义 SQL 查询语句或指定表名 + 列映射
- [ ] 连接超时设置默认 30 秒，查询超时默认 120 秒
- [ ] 连接失败时记录错误日志并抛出明确异常，不静默忽略

**US-1.3: 统一 InventoryRecord 数据模型**
> 作为开发人员，我希望所有数据源的输出统一为 `InventoryRecord` 数据模型，这样下游检测和报表模块不必关心数据来源差异。

**验收标准 (Acceptance Criteria):**
- [ ] `InventoryRecord` 至少包含字段：`sku`, `product_name`, `current_qty`, `unit`, `warehouse`, `last_updated`, `source_type`
- [ ] 所有数据源适配器输出 `List[InventoryRecord]`
- [ ] 数据模型使用 Pydantic BaseModel，内置类型校验
- [ ] `current_qty` 为负数时自动标记为异常记录
- [ ] `last_updated` 统一为 UTC ISO 8601 格式

### 依赖 (Dependencies)

- 无上游 Epic 依赖（本 Epic 为数据入口）
- 下游依赖：Epic 2（低库存检测）、Epic 4（报表生成）

---

## Epic 2: 低库存检测 (Low Stock Detection)

**Splitting Pattern Used:** #3 — Business Rule Variations
> 低库存检测涉及多种业务规则（安全库存阈值、预警阈值、趋势检测），每种规则可独立实现和测试，属于典型的"业务规则变体"拆分。

### 描述

本 Epic 实现库存预警的核心检测逻辑。系统需支持按 SKU 粒度配置安全库存和预警阈值，生成两级告警（critical 严重 / warning 预警），并具备基于 7 天滑动窗口的下降趋势检测能力。检测结果以结构化 `AlertRecord` 输出，供报表和通知模块消费。

### User Stories

**US-2.1: Per-SKU 阈值配置与两级告警**
> 作为仓库主管，我希望能为每个 SKU 分别设置安全库存和预警阈值，并在库存触及不同阈值时收到不同级别的告警，这样我可以按轻重缓急处理补货。

**验收标准 (Acceptance Criteria):**
- [ ] 支持通过 CSV 或数据库表为每个 SKU 配置 `safety_stock`（安全库存）和 `warning_threshold`（预警阈值）
- [ ] `warning_threshold` 必须 ≥ `safety_stock`，否则配置校验报错
- [ ] 当 `current_qty < safety_stock` 时生成 `CRITICAL` 级别告警
- [ ] 当 `safety_stock ≤ current_qty < warning_threshold` 时生成 `WARNING` 级别告警
- [ ] 未配置阈值的 SKU 使用全局默认值（可在配置文件中设置）
- [ ] 检测结果包含：`sku`, `product_name`, `current_qty`, `threshold_hit`, `alert_level`, `detected_at`

**US-2.2: 7 天下降趋势检测**
> 作为采购经理，我希望系统能识别连续 7 天库存呈下降趋势的商品（即使尚未触及阈值），这样我可以提前启动询价流程，避免断货。

**验收标准 (Acceptance Criteria):**
- [ ] 基于最近 7 天的库存快照数据计算趋势（需至少 5 个数据点）
- [ ] 趋势检测算法：线性回归斜率为负且 R² ≥ 0.7，或连续 5 天以上逐日递减
- [ ] 趋势告警级别为 `TREND_WARNING`，与阈值告警并行输出
- [ ] 输出包含：预计归零天数（按当前下降速率外推）
- [ ] 数据点不足 5 天时跳过趋势检测，不报错

**US-2.3: 告警去重与静默期**
> 作为仓库主管，我不希望同一个 SKU 在同一天内重复告警轰炸我，系统应支持告警静默期设置。

**验收标准 (Acceptance Criteria):**
- [ ] 同一 SKU 的同一级别告警在静默期内（默认 24 小时）不重复触发
- [ ] 告警级别升级（WARNING → CRITICAL）时立即触发，不受静默期限制
- [ ] 静默期可按全局或 Per-SKU 配置
- [ ] 告警记录持久化到 SQLite，用于去重判断

### 依赖 (Dependencies)

- 上游依赖：Epic 1（数据提取 — 提供 `InventoryRecord` 列表）
- 下游依赖：Epic 3（供应商报价 — 消费告警 SKU 清单）、Epic 4（报表生成）、Epic 5（通知调度）

---

## Epic 3: 供应商报价抓取 (Supplier Scraping)

**Splitting Pattern Used:** #6 — Simple/Complex (Defer Complexity)
> 供应商网站结构各异，登录机制不同（表单登录、验证码、OAuth）。先实现"简单"场景（标准表单登录 + 价格页抓取），再逐步处理复杂场景（验证码、动态加载、反爬对抗），体现"先简后繁"拆分。

### 描述

本 Epic 实现基于 Playwright 的无头浏览器自动化，对多家供应商网站执行登录、导航、价格抓取。系统需支持异步并发抓取（通过 Semaphore 控制并发数），将抓取结果标准化为 `QuoteRecord` 输出。供应商配置（URL、登录凭证、CSS 选择器）通过配置文件管理。

### User Stories

**US-3.1: Playwright 无头浏览器自动化与供应商登录**
> 作为采购专员，我希望系统能自动登录各供应商平台并抓取最新报价，这样我不必每天手动登录 5-6 个网站逐一查价。

**验收标准 (Acceptance Criteria):**
- [ ] 使用 Playwright (Chromium) 无头模式执行浏览器自动化
- [ ] 供应商配置文件包含：`name`, `login_url`, `username`, `password`, `price_page_url`, `selectors`
- [ ] 密码字段支持环境变量引用或加密存储
- [ ] 支持标准表单登录（用户名 + 密码字段 + 提交按钮，通过 CSS 选择器定位）
- [ ] 登录成功判断：检测登录后页面特征元素（可配置选择器）
- [ ] 登录失败时记录截图到 `logs/screenshots/` 目录，并标记该供应商为 `SCRAPE_FAILED`

**US-3.2: 价格数据抓取与标准化**
> 作为采购专员，我希望系统从供应商页面提取商品价格、最小起订量等信息，并统一格式输出，方便比价。

**验收标准 (Acceptance Criteria):**
- [ ] 通过 CSS 选择器提取：`product_name`, `unit_price`, `currency`, `moq`（最小起订量）, `lead_time`
- [ ] 输出标准化 `QuoteRecord`：`supplier`, `sku`, `unit_price`, `currency`, `moq`, `lead_time`, `scraped_at`
- [ ] 价格字段自动去除货币符号和千分位分隔符，转为 `Decimal` 类型
- [ ] 页面加载超时设置为 30 秒，元素等待超时 10 秒
- [ ] 抓取失败的 SKU 记录原因（元素未找到 / 超时 / 格式异常）

**US-3.3: 异步并发抓取与限流**
> 作为系统管理员，我希望多家供应商的抓取任务能并行执行以提高效率，但需要限制并发数以避免被封 IP 或耗尽系统资源。

**验收标准 (Acceptance Criteria):**
- [ ] 使用 `asyncio.Semaphore` 控制并发浏览器实例数（默认 3，可配置）
- [ ] 每个供应商抓取任务独立，单个失败不影响其他供应商
- [ ] 请求间隔随机延迟 2-5 秒（可配置范围），模拟人工操作
- [ ] 支持配置代理（HTTP/SOCKS5）用于 IP 轮换
- [ ] 所有供应商抓取完成后汇总结果，包含成功/失败统计

### 依赖 (Dependencies)

- 上游依赖：Epic 2（低库存检测 — 提供需要询价的 SKU 清单）
- 下游依赖：Epic 4（报表生成 — 消费 `QuoteRecord` 列表）
- 外部依赖：Playwright 浏览器引擎安装（`playwright install chromium`）

---

## Epic 4: 报表生成 (Report Generation)

**Splitting Pattern Used:** #2 — Data Variations
> 报表包含多种数据类型（告警数据、报价数据、推荐数据），每类数据的展示逻辑和格式不同，按数据变体拆分为独立 Sheet 实现。

### 描述

本 Epic 实现多 Sheet Excel 报表生成。报表包含三个核心 Sheet：告警清单（Alerts）、供应商报价对比（Quotes）、采购建议（Recommendations）。支持条件格式化（红色=严重、黄色=预警、绿色=最优价）和自动列宽调整，输出专业级采购决策报表。

### User Stories

**US-4.1: 多 Sheet xlsx 报表结构**
> 作为采购经理，我希望收到一份包含告警清单、报价对比、采购建议的 Excel 报表，这样我可以在一个文件中完成采购决策。

**验收标准 (Acceptance Criteria):**
- [ ] 使用 `openpyxl` 生成 `.xlsx` 格式报表
- [ ] Sheet 1 "告警清单"：包含 `SKU`, `商品名称`, `当前库存`, `安全库存`, `预警阈值`, `告警级别`, `趋势`
- [ ] Sheet 2 "供应商报价"：包含 `SKU`, `商品名称`, `供应商A报价`, `供应商B报价`, ..., `最低价`, `最低价供应商`
- [ ] Sheet 3 "采购建议"：包含 `SKU`, `商品名称`, `建议采购量`, `推荐供应商`, `预计金额`, `优先级`
- [ ] 每个 Sheet 第一行为冻结表头，包含筛选器（AutoFilter）
- [ ] 报表文件名格式：`inventory_report_YYYYMMDD_HHMMSS.xlsx`

**US-4.2: 条件格式化与可视化**
> 作为采购经理，我希望报表中用颜色直观标注告警级别和最优报价，这样我可以快速定位关键信息。

**验收标准 (Acceptance Criteria):**
- [ ] 告警清单 Sheet：`CRITICAL` 行背景色为红色（#FF4444），`WARNING` 为黄色（#FFD700）
- [ ] 供应商报价 Sheet：每行最低报价单元格背景色为绿色（#90EE90）
- [ ] 采购建议 Sheet：优先级"高"为红色字体，"中"为橙色，"低"为灰色
- [ ] 数字列使用千分位格式（如 `#,##0.00`）
- [ ] 日期列使用 `YYYY-MM-DD` 格式

**US-4.3: 自动列宽调整与打印优化**
> 作为仓库管理员，我希望打开报表后列宽自动适配内容，打印时也有合理的页面布局。

**验收标准 (Acceptance Criteria):**
- [ ] 列宽根据表头和数据内容自动计算（中文字符按 2 字符宽度计算）
- [ ] 最大列宽限制为 50 字符，超长内容自动换行
- [ ] 设置打印区域、页眉（报表标题 + 日期）、页脚（页码）
- [ ] 横向打印（Landscape）以适应多列数据

### 依赖 (Dependencies)

- 上游依赖：Epic 2（告警数据）、Epic 3（报价数据）
- 下游依赖：Epic 5（调度与运维 — 发送报表附件）

---

## Epic 5: 调度与运维 (Scheduling & Operations)

**Splitting Pattern Used:** #4 — Interface Variations (Notification Channels)
> 通知渠道（邮件、钉钉、企业微信）属于同一功能的不同接口变体，每种渠道可独立实现和上线，用户按需启用。

### 描述

本 Epic 实现任务调度、多渠道通知和运维审计能力。通过 Windows Task Scheduler 定时触发检测流程，检测结果通过邮件（含报表附件）、钉钉 Webhook、企业微信 Webhook 发送通知。所有操作记录写入 SQLite 审计表，支持历史追溯。

### User Stories

**US-5.1: Windows Task Scheduler 定时调度**
> 作为 IT 运维人员，我希望系统能通过 Windows 计划任务定时执行库存检测流程（如每天早上 8:00），无需人工手动触发。

**验收标准 (Acceptance Criteria):**
- [ ] 提供 PowerShell 脚本自动注册 Windows 计划任务（任务名称、执行时间、Python 脚本路径可配置）
- [ ] 计划任务配置：每日执行、失败后重试 3 次（间隔 10 分钟）
- [ ] 支持"用户未登录时也运行"模式
- [ ] 任务启动时记录 `run_id`（UUID），贯穿整个执行链路用于日志追踪
- [ ] 提供手动触发入口（命令行 `python main.py --run-now`）

**US-5.2: 邮件通知（含报表附件）**
> 作为采购经理，我希望每天早上收到一封包含库存报表的邮件，如果有严重告警则邮件标题标注"紧急"。

**验收标准 (Acceptance Criteria):**
- [ ] 使用 SMTP（支持 SSL/TLS）发送邮件，配置项：`smtp_host`, `smtp_port`, `sender`, `password`, `recipients`
- [ ] 邮件正文包含告警摘要（CRITICAL x 条，WARNING y 条）
- [ ] 报表 xlsx 文件作为附件，附件大小限制 25MB
- [ ] 存在 CRITICAL 告警时邮件标题前缀 `[紧急]`
- [ ] 发送失败时重试 2 次，最终失败记录到审计日志

**US-5.3: 钉钉 / 企业微信 Webhook 通知**
> 作为仓库主管，我希望在钉钉或企业微信群中收到库存告警推送，这样我在手机上就能第一时间看到。

**验收标准 (Acceptance Criteria):**
- [ ] 支持钉钉自定义机器人 Webhook（含签名验证 `HmacSHA256`）
- [ ] 支持企业微信群机器人 Webhook
- [ ] 消息格式：Markdown 卡片，包含告警级别、SKU、当前库存、建议操作
- [ ] 单条消息长度超过平台限制时自动分片发送
- [ ] 通知渠道可在配置文件中按需启用/禁用

**US-5.4: SQLite 审计日志**
> 作为 IT 运维人员，我希望系统记录每次执行的详细日志（开始时间、结束时间、告警数、报表路径、通知状态），方便排查问题和生成运维报告。

**验收标准 (Acceptance Criteria):**
- [ ] SQLite 审计表 `audit_log`：`run_id`, `started_at`, `finished_at`, `status`, `alert_count_critical`, `alert_count_warning`, `report_path`, `notification_results`, `error_message`
- [ ] 每个子步骤（数据提取、检测、抓取、报表、通知）独立记录状态
- [ ] 审计数据保留 90 天，超期自动清理
- [ ] 提供 CLI 命令查询最近 N 次执行记录（`python main.py --audit-history 10`）

### 依赖 (Dependencies)

- 上游依赖：Epic 4（报表文件）、Epic 2（告警数据）
- 外部依赖：SMTP 服务器访问权限、钉钉/企业微信 Webhook URL 配置

---

## Epic 依赖关系总览

```
Epic 1 (数据提取)
  │
  ▼
Epic 2 (低库存检测)
  │          │
  ▼          ▼
Epic 3      Epic 4 (报表生成) ◄── Epic 3
(供应商报价)  │
  │          ▼
  └──────► Epic 5 (调度与运维)
```

## 拆分模式使用总结

| Epic | 拆分模式 | 模式编号 | 说明 |
|------|---------|---------|------|
| Epic 1: 数据提取 | Workflow Steps | #1 | 工作流第一步独立拆出 |
| Epic 2: 低库存检测 | Business Rule Variations | #3 | 多种检测规则独立实现 |
| Epic 3: 供应商报价抓取 | Simple/Complex | #6 | 先简单登录抓取，再处理复杂反爬 |
| Epic 4: 报表生成 | Data Variations | #2 | 多种数据类型对应不同 Sheet |
| Epic 5: 调度与运维 | Interface Variations | #4 | 多种通知渠道独立实现 |
