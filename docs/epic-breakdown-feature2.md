# Epic Breakdown: 出入库单据自动录入

**Feature:** 出入库单据自动录入 (Automated Warehouse Receipt Entry)
**Date:** 2026-03-14
**Splitting Method:** Richard Lawrence's 9 Splitting Patterns
**Total Epics:** 5

---

## Epic 1: 图像采集 (Image Acquisition)

**Splitting Pattern Used:** #1 — Workflow Steps
> 图像采集是整个单据录入流水线的第一步，独立拆分后可以单独开发和测试文件监控逻辑，不依赖后续 OCR 或 RPA 模块。

### 描述

本 Epic 实现基于文件系统监控的图像自动采集能力。使用 `watchdog` 库监听指定目录，当新图像文件写入完成后自动触发后续处理流水线。系统需处理文件写入中断、大文件分块传输等场景，通过文件稳定性检测（文件大小在一定时间内不再变化）确保只处理完整文件。支持 jpg、png、bmp、tiff、heif 等常见图像格式。

### User Stories

**US-1.1: Watchdog 文件夹监控**
> 作为仓库操作员，我希望只需将单据照片/扫描件放入指定文件夹，系统就能自动发现并处理，不需要我手动点击任何按钮。

**验收标准 (Acceptance Criteria):**
- [ ] 使用 `watchdog` 库监听配置的"收件箱"目录（如 `./inbox/`）
- [ ] 监听事件类型：`FileCreatedEvent` 和 `FileMovedEvent`（覆盖复制和剪切粘贴场景）
- [ ] 支持递归监控子目录（可配置开关）
- [ ] 服务启动时扫描目录中已有的未处理文件（冷启动恢复）
- [ ] 监控服务作为后台守护进程运行，支持优雅关闭（SIGTERM / Ctrl+C）

**US-1.2: 文件稳定性检测**
> 作为系统管理员，我希望系统不会在文件还在传输过程中就开始处理，避免因读取不完整文件导致 OCR 失败。

**验收标准 (Acceptance Criteria):**
- [ ] 文件创建后等待稳定期：每 500ms 检查一次文件大小，连续 3 次（即 1.5 秒）大小不变则视为写入完成
- [ ] 稳定期可通过配置文件调整（`stability_check_interval_ms`, `stability_check_count`）
- [ ] 文件大小为 0 字节时跳过处理，记录警告日志
- [ ] 超过最大等待时间（默认 60 秒）仍不稳定的文件标记为异常，移入 `./failed/` 目录
- [ ] 正在检测稳定性的文件加入"处理中"集合，防止重复触发

**US-1.3: 多格式图像支持**
> 作为仓库操作员，我使用不同的设备拍照和扫描（手机、扫描仪、相机），产生的格式不同，我希望系统都能处理。

**验收标准 (Acceptance Criteria):**
- [ ] 支持格式：`.jpg`/`.jpeg`, `.png`, `.bmp`, `.tiff`/`.tif`, `.heif`/`.heic`
- [ ] 通过文件头（magic bytes）而非扩展名判断实际格式，防止扩展名与内容不匹配
- [ ] HEIF 格式自动转换为 PNG 后传递给 OCR 模块（使用 `pillow-heif`）
- [ ] 不支持的格式文件移入 `./unsupported/` 目录并记录日志
- [ ] 单文件大小上限 50MB，超过则跳过并记录警告

### 依赖 (Dependencies)

- 无上游 Epic 依赖（本 Epic 为流水线入口）
- 下游依赖：Epic 2（OCR 提取 — 消费采集到的图像文件）

---

## Epic 2: OCR 提取 (OCR Extraction)

**Splitting Pattern Used:** #6 — Simple/Complex (Defer Complexity)
> OCR 提取涉及从简单的高质量扫描件到复杂的手机拍照（歪斜、光照不均、模糊）等不同难度。先实现"简单"场景（标准扫描件识别），再逐步增加图像预处理管线处理复杂场景。

### 描述

本 Epic 实现图像预处理与 OCR 文字识别。预处理管线包括自动旋转校正、CLAHE 对比度增强、去噪、自适应二值化等步骤，将图像质量优化到 OCR 引擎最佳识别状态。使用 PaddleOCR 进行中英文混合识别，输出每行文字及其置信度分数，供下游数据校验模块使用。

### User Stories

**US-2.1: 图像预处理管线**
> 作为系统开发人员，我希望在 OCR 识别之前对图像进行标准化预处理，以提升手机拍照等低质量图像的识别准确率。

**验收标准 (Acceptance Criteria):**
- [ ] 预处理管线步骤（按顺序执行）：
  1. 自动旋转校正（基于 EXIF 方向信息 + Hough 变换倾斜检测，纠偏角度 ≤ 45°）
  2. CLAHE 自适应直方图均衡化（`clipLimit=2.0`, `tileGridSize=(8,8)`）
  3. 高斯去噪（`kernel_size=3`）或非局部均值去噪（根据噪声水平自动选择）
  4. 自适应二值化（`cv2.adaptiveThreshold`, `blockSize=11`, `C=2`）
- [ ] 每个步骤可通过配置独立启用/禁用
- [ ] 预处理后的图像保存到 `./preprocessed/` 目录（可配置是否保留，默认保留用于调试）
- [ ] 预处理耗时记录到日志，单张图像预处理不超过 5 秒（1920x1080 分辨率基准）

**US-2.2: PaddleOCR 中英文识别**
> 作为仓库管理员，我希望系统能准确识别单据上的中文商品名称、英文型号、数字数量等混合内容。

**验收标准 (Acceptance Criteria):**
- [ ] 使用 PaddleOCR（`lang='ch'` 中英文模型）进行文字识别
- [ ] 输出格式：`List[OcrLine]`，每行包含 `text`, `confidence`, `bbox`（边界框坐标）
- [ ] 整体识别准确率 ≥ 90%（基于 50 张标准测试单据）
- [ ] 支持识别表格结构（行列关系），输出结构化表格数据
- [ ] GPU 可用时自动启用 GPU 加速（`use_gpu=True`），否则 fallback 到 CPU

**US-2.3: 置信度评分与分级**
> 作为质量控制人员，我希望每行 OCR 识别结果都带有置信度分数，这样系统可以自动判断哪些结果需要人工复核。

**验收标准 (Acceptance Criteria):**
- [ ] 每行识别结果的置信度分数范围 0.0 - 1.0
- [ ] 计算整张单据的平均置信度和最低置信度
- [ ] 置信度 < 0.5 的行标记为 `LOW_CONFIDENCE`，在日志中高亮
- [ ] 输出结果中保留原始 OCR 引擎返回的全部元数据
- [ ] 支持将识别结果以 JSON 格式导出（用于调试和回归测试）

### 依赖 (Dependencies)

- 上游依赖：Epic 1（图像采集 — 提供预检完成的图像文件路径）
- 下游依赖：Epic 3（数据校验 — 消费 OCR 识别结果）
- 外部依赖：PaddleOCR 模型文件下载（首次运行自动下载）、OpenCV 安装

---

## Epic 3: 数据校验 (Data Validation)

**Splitting Pattern Used:** #3 — Business Rule Variations
> 数据校验包含多种独立的业务规则：正则匹配、模糊匹配、必填校验、格式校验、置信度路由。每种规则可独立编写和测试，属于典型的"业务规则变体"拆分。

### 描述

本 Epic 实现从 OCR 原始文本到结构化单据字段的提取与校验。通过正则表达式和模糊匹配算法从非结构化文本中提取关键字段（单据编号、商品名称、数量、日期等），对提取结果执行多层校验规则（必填性、格式合规性），并根据整体置信度进行三级路由：自动通过（≥90%）、人工复核（70%-90%）、强制拒绝（<70%）。

### User Stories

**US-3.1: 正则 + 模糊匹配字段提取**
> 作为系统开发人员，我希望系统能从 OCR 文本中自动提取单据的关键字段，即使 OCR 识别有小错误也能通过模糊匹配纠正。

**验收标准 (Acceptance Criteria):**
- [ ] 提取字段清单：`receipt_no`（单据编号）, `product_name`（商品名称）, `quantity`（数量）, `unit`（单位）, `date`（日期）, `warehouse`（仓库）, `operator`（操作人）, `receipt_type`（入库/出库）
- [ ] 单据编号提取：正则匹配 `[A-Z]{2,4}-\d{8,12}` 及常见变体
- [ ] 日期提取：支持 `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY年MM月DD日`, `MM-DD-YYYY` 等格式
- [ ] 数量提取：支持整数和小数，自动处理 OCR 常见错误（如 `O` → `0`, `l` → `1`）
- [ ] 商品名称：使用 `fuzzywuzzy`/`rapidfuzz` 与商品主数据库模糊匹配，阈值 ≥ 80 分视为匹配成功
- [ ] 每个字段提取结果包含：`value`, `confidence`, `source_text`（原始 OCR 文本片段）

**US-3.2: 字段校验规则**
> 作为仓库主管，我希望系统能自动检查提取出的字段是否完整合规，避免错误数据进入 WMS 系统。

**验收标准 (Acceptance Criteria):**
- [ ] 必填字段校验：`receipt_no`, `product_name`, `quantity`, `date` 缺失任一则标记为校验失败
- [ ] 格式校验规则：
  - `quantity` > 0 且为合理范围（可配置上限，默认 999999）
  - `date` 不晚于当前日期 + 1 天（防止未来日期）
  - `date` 不早于当前日期 - 365 天（防止过老单据）
  - `receipt_no` 不与已处理单据重复（防重复录入）
- [ ] 校验结果分为 `PASS`（全部通过）、`WARN`（非必填字段异常）、`FAIL`（必填字段缺失/格式错误）
- [ ] 校验失败原因以结构化列表输出，每条包含字段名、规则名、错误详情

**US-3.3: 置信度三级路由**
> 作为质量控制人员，我希望系统根据识别置信度自动决定：高置信度直接录入、中等置信度提交人工复核、低置信度直接拒绝，这样既保证效率又控制准确性。

**验收标准 (Acceptance Criteria):**
- [ ] 综合置信度计算：各字段置信度的加权平均（权重可配置，必填字段权重更高）
- [ ] 路由规则：
  - `AUTO_PASS`：综合置信度 ≥ 90%，直接发送到 RPA 录入
  - `REVIEW`：综合置信度 70% - 90%，进入人工复核队列
  - `FORCE_REJECT`：综合置信度 < 70%，拒绝处理并移入失败目录
- [ ] 阈值可通过配置文件调整（`auto_pass_threshold`, `review_threshold`）
- [ ] 路由决策记录到审计日志，包含：`receipt_no`, `confidence`, `route_decision`, `decided_at`
- [ ] `REVIEW` 状态的单据在人工确认/修改后可重新提交到 RPA 录入

### 依赖 (Dependencies)

- 上游依赖：Epic 2（OCR 提取 — 提供 `List[OcrLine]` 识别结果）
- 下游依赖：Epic 4（RPA 录入 — 消费校验通过的结构化字段）、Epic 5（日志审计 — 记录校验和路由决策）
- 数据依赖：商品主数据库（用于模糊匹配商品名称）

---

## Epic 4: RPA 录入 (RPA Entry)

**Splitting Pattern Used:** #8 — Break Out a Spike
> RPA 自动化录入涉及与外部 WMS 系统的 GUI 交互，技术不确定性高（窗口定位、控件识别、中文输入等）。先做技术探针（Spike）验证 pyautogui + pygetwindow 的可行性，再实现完整录入流程。

### 描述

本 Epic 实现基于桌面 GUI 自动化的 WMS 系统单据录入。使用 `pygetwindow` 定位并激活 WMS 窗口，通过 `pyautogui` 基于坐标定位执行表单填写操作，中文文本通过剪贴板方式输入以避免输入法兼容问题。录入完成后截图保存作为操作凭证。

### User Stories

**US-4.1: WMS 窗口激活与定位**
> 作为系统管理员，我希望 RPA 模块能自动找到并激活 WMS 客户端窗口，即使窗口被最小化或被其他窗口遮挡。

**验收标准 (Acceptance Criteria):**
- [ ] 使用 `pygetwindow` 通过窗口标题关键字（可配置）查找 WMS 窗口
- [ ] 支持精确匹配和模糊匹配窗口标题（如包含 "WMS" 或 "仓库管理"）
- [ ] 窗口最小化时自动恢复（`restore()`），非前台时自动激活（`activate()`）
- [ ] WMS 窗口未找到时等待最多 30 秒（轮询间隔 2 秒），超时则报错中止
- [ ] 激活后等待 1 秒确保窗口完全渲染，再执行后续操作

**US-4.2: 坐标定位表单填写与中文输入**
> 作为仓库操作员，我希望 RPA 能自动在 WMS 的入库/出库表单中填写单据信息，包括中文商品名称，替代我的重复手工录入。

**验收标准 (Acceptance Criteria):**
- [ ] 表单字段坐标通过配置文件管理（`field_name: {x, y}` 映射），支持多种 WMS 界面模板
- [ ] 填写流程：点击字段坐标 → 清空已有内容（Ctrl+A → Delete）→ 输入内容 → Tab 跳转下一字段
- [ ] 中文文本输入方式：复制到剪贴板（`pyperclip`）→ Ctrl+V 粘贴，避免输入法干扰
- [ ] 数字和英文内容使用 `pyautogui.typewrite()` 直接输入
- [ ] 每个字段填写后等待 300ms（可配置），防止输入过快 WMS 来不及响应
- [ ] 填写完成后模拟点击"保存"/"提交"按钮

**US-4.3: 截图验证与异常处理**
> 作为质量控制人员，我希望 RPA 每次录入后自动截图保存，并验证是否出现成功提示，这样我可以事后核查。

**验收标准 (Acceptance Criteria):**
- [ ] 点击提交后等待 2 秒，截取 WMS 窗口区域截图
- [ ] 截图文件保存到 `./screenshots/YYYYMMDD/`，文件名包含单据编号和时间戳
- [ ] 通过 OCR 或图像匹配检测截图中是否包含"保存成功"/"提交成功"等关键文字
- [ ] 检测到错误提示（如"单据编号重复""必填字段为空"）时标记为录入失败
- [ ] 录入失败时自动点击"取消"按钮关闭对话框，恢复 WMS 到初始状态
- [ ] 连续 3 次录入失败时暂停 RPA 流程，发送告警通知

### 依赖 (Dependencies)

- 上游依赖：Epic 3（数据校验 — 提供校验通过的结构化单据字段）
- 下游依赖：Epic 5（日志审计 — 记录录入结果和截图路径）
- 环境依赖：WMS 客户端已安装并登录、屏幕分辨率与坐标配置匹配

---

## Epic 5: 日志审计 (Logging & Audit)

**Splitting Pattern Used:** #4 — Interface Variations
> 日志审计涉及多种输出接口（结构化日志文件、SQLite 数据库、文件归档、Tkinter UI），每种接口可独立实现，属于"接口变体"拆分。

### 描述

本 Epic 实现贯穿全流程的日志记录、审计追踪、文件归档和人工复核界面。所有操作（图像采集、OCR、校验、RPA 录入）的执行结果以结构化 JSON 格式记录日志，关键数据写入 SQLite 审计表。处理完成的文件自动归档到 `processed/` 或 `failed/` 目录。提供 Tkinter 桌面 UI 供质检人员查看待复核单据并进行人工确认或修正。

### User Stories

**US-5.1: 结构化 JSON 日志**
> 作为 IT 运维人员，我希望系统以结构化 JSON 格式记录日志，方便我用日志分析工具（如 ELK）进行集中分析和告警。

**验收标准 (Acceptance Criteria):**
- [ ] 使用 Python `logging` + `python-json-logger` 输出 JSON 格式日志
- [ ] 每条日志必含字段：`timestamp`（ISO 8601）, `level`, `module`, `message`, `run_id`, `receipt_no`（如适用）
- [ ] 日志级别：`DEBUG`（开发调试）, `INFO`（正常流程）, `WARNING`（可恢复异常）, `ERROR`（不可恢复异常）
- [ ] 日志文件按天轮转（`TimedRotatingFileHandler`），保留 30 天
- [ ] 同时输出到控制台（`StreamHandler`）和文件（`./logs/app_YYYYMMDD.log`）
- [ ] 敏感信息（密码、Token）在日志中自动脱敏为 `***`

**US-5.2: SQLite 审计追踪**
> 作为仓库主管，我希望每张单据从扫描到录入的完整处理链路都被记录，方便追溯任何一张单据的处理过程。

**验收标准 (Acceptance Criteria):**
- [ ] SQLite 数据库文件：`./data/audit.db`
- [ ] 审计表 `receipt_audit`：
  - `id` (INTEGER PRIMARY KEY)
  - `run_id` (TEXT) — 本次运行唯一标识
  - `receipt_no` (TEXT) — 单据编号
  - `image_path` (TEXT) — 原始图像路径
  - `ocr_confidence` (REAL) — OCR 整体置信度
  - `validation_result` (TEXT) — 校验结果 (PASS/WARN/FAIL)
  - `route_decision` (TEXT) — 路由决策 (AUTO_PASS/REVIEW/FORCE_REJECT)
  - `rpa_status` (TEXT) — RPA 录入状态 (SUCCESS/FAILED/SKIPPED)
  - `screenshot_path` (TEXT) — 录入截图路径
  - `error_message` (TEXT) — 错误信息
  - `created_at` (TEXT) — 创建时间
  - `updated_at` (TEXT) — 最后更新时间
- [ ] 每个处理阶段完成后实时更新对应字段（非最后一次性写入）
- [ ] 提供 CLI 查询命令：`python main.py --audit-query --receipt-no XX --date YYYY-MM-DD`

**US-5.3: 文件归档管理**
> 作为系统管理员，我希望处理完成的图像文件自动归档到对应目录，保持收件箱整洁，同时方便回溯原始文件。

**验收标准 (Acceptance Criteria):**
- [ ] 处理成功的文件移入 `./archive/processed/YYYYMMDD/`
- [ ] 处理失败的文件移入 `./archive/failed/YYYYMMDD/`
- [ ] 归档时保留原始文件名，若同名则追加序号（如 `receipt_001_2.jpg`）
- [ ] 归档目录自动创建，无需手动建立
- [ ] 归档文件保留 180 天，超期自动清理（通过独立清理任务）
- [ ] 归档操作记录到审计表（`archive_path` 字段）

**US-5.4: Tkinter 人工复核 UI**
> 作为质检人员，我希望有一个桌面界面查看置信度中等（70%-90%）的待复核单据，直接在界面上确认或修正 OCR 结果后提交录入。

**验收标准 (Acceptance Criteria):**
- [ ] Tkinter 桌面应用，启动命令：`python main.py --review-ui`
- [ ] 主界面布局：
  - 左侧：待复核单据列表（显示单据编号、置信度、接收时间）
  - 右上：原始图像预览（支持缩放和拖拽）
  - 右下：OCR 提取字段编辑表单（各字段可修改）
- [ ] 操作按钮：
  - "确认无误" → 将单据发送到 RPA 录入队列
  - "修正后提交" → 使用修改后的字段值发送到 RPA 录入队列
  - "拒绝" → 标记为人工拒绝，移入失败目录
- [ ] 列表支持按置信度排序、按日期筛选
- [ ] 已处理的单据自动从待复核列表中移除
- [ ] 界面响应时间 < 500ms，图像加载支持异步（不阻塞 UI）

### 依赖 (Dependencies)

- 上游依赖：Epic 3（数据校验 — 提供路由决策和待复核队列）、Epic 4（RPA 录入 — 提供录入结果）
- 贯穿依赖：本 Epic 的日志和审计组件被 Epic 1-4 全部依赖（作为横切关注点）

---

## Epic 依赖关系总览

```
Epic 1 (图像采集)
  │
  ▼
Epic 2 (OCR 提取)
  │
  ▼
Epic 3 (数据校验)
  │          │
  ▼          ▼
Epic 4      Epic 5 (日志审计)
(RPA 录入)   ▲  ▲  ▲  ▲
  │          │  │  │  │
  └──────────┘  │  │  │
     Epic 1 ────┘  │  │
     Epic 2 ───────┘  │
     Epic 3 ──────────┘

注：Epic 5 (日志审计) 是横切关注点，被所有其他 Epic 依赖。
    实际开发中建议 Epic 5 的基础设施（日志框架、审计表结构）最先实现。
```

## 拆分模式使用总结

| Epic | 拆分模式 | 模式编号 | 说明 |
|------|---------|---------|------|
| Epic 1: 图像采集 | Workflow Steps | #1 | 流水线第一步独立拆出 |
| Epic 2: OCR 提取 | Simple/Complex | #6 | 先处理高质量扫描件，再增加复杂预处理 |
| Epic 3: 数据校验 | Business Rule Variations | #3 | 多种校验规则和路由策略独立实现 |
| Epic 4: RPA 录入 | Break Out a Spike | #8 | 先做技术探针验证 GUI 自动化可行性 |
| Epic 5: 日志审计 | Interface Variations | #4 | 多种输出接口（日志/数据库/UI）独立实现 |
