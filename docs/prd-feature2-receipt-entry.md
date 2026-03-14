# PRD: 出入库单据自动录入系统

# Warehouse Receipt Automated Entry System

| 字段 Field | 值 Value |
|---|---|
| 文档版本 Version | 1.0 |
| 创建日期 Created | 2026-03-14 |
| 作者 Author | Warehouse Automation Team |
| 状态 Status | Draft |
| 产品代号 Codename | **ReceiptBot** |
| 目标上线 Target Launch | 2026-Q2 |

---

## 1. Executive Summary 执行摘要

本文档定义"出入库单据自动录入系统"（ReceiptBot）的产品需求。该系统旨在解决仓库单据从纸质/图片形式到 WMS（仓库管理系统）数字化录入过程中的**人工瓶颈**问题——操作员每天需要手动将数十张出入库单据逐字录入系统，不仅耗时且极易出错。

ReceiptBot watches a designated folder for new receipt images, preprocesses them for optimal OCR quality, uses PaddleOCR to recognize Chinese+English mixed text, extracts structured fields via regex and fuzzy matching, routes results through a confidence-based review pipeline, provides a Tkinter GUI for human review when needed, and finally uses pyautogui RPA to auto-enter verified data into the WMS with screenshot verification.

**Core value proposition**: Reduce manual data entry time by ≥70% and entry error rate by ≥80%, transforming a tedious manual process into a supervised-automation workflow where humans review exceptions rather than type every character.

---

## 2. Problem Statement 问题陈述

### 2.1 Empathy-Driven Problem Framing

> **I am** 数据录入员小张 (Data Entry Clerk Zhang), **trying to** accurately enter 40-60 warehouse receipt documents into the WMS every day, **but** each receipt requires me to manually type 10+ fields (supplier name, item codes, quantities, dates), and after 4 hours of repetitive typing my error rate climbs significantly — yet any mistake can cause inventory discrepancies that take days to reconcile.

> **I am** 仓库主管刘哥 (Warehouse Supervisor Liu), **trying to** ensure that all incoming and outgoing goods are recorded in the WMS within 2 hours of physical receipt, **but** the data entry backlog often means receipts from the morning shift are not entered until the afternoon, creating a dangerous gap between physical inventory and system records.

> **I am** 质量审计员周姐 (Quality Auditor Zhou), **trying to** verify that WMS entries match the original paper receipts for compliance audits, **but** I have to pull paper files and manually cross-reference them against screen data — there is no digital link between the source document and the system entry.

### 2.2 Current Pain Points 当前痛点

| # | Pain Point 痛点 | Impact 影响 | Frequency 频率 |
|---|---|---|---|
| 1 | 每张单据 10+ 字段手工录入 | 每张耗时 3-5 分钟，每天 40-60 张 = 3-5 小时纯打字 | 每天 |
| 2 | 中英文混合单据难以准确辨认 | 供应商名称、型号常含英文，手写+打印混排 | 每张单据 |
| 3 | 录入错误率随疲劳上升 | 下午场错误率比上午高 3x，导致库存偏差 | 每天下午 |
| 4 | 纸质单据与系统记录无关联 | 审计时需人工翻找纸质档案 | 每次审计 |
| 5 | WMS 无批量导入接口 | 只能逐条通过 UI 录入，无 API 可用 | 每次录入 |
| 6 | 录入积压导致实物与系统不同步 | 出库时系统显示有货但实际已出库，或反之 | 每天 |

---

## 3. Proto-Personas 用户角色

### Persona 1: 录入员小张 — "The Data Warrior"

| 维度 | 描述 |
|---|---|
| **Identity 身份** | 张晓明，24 岁，仓库数据录入员，入职 1 年。每天坐在电脑前 8 小时，其中 4-5 小时用于单据录入。 |
| **Voice 声音** | "最痛苦的是那些手写的送货单，字迹潦草我要猜半天。有些供应商的单据还是英文的，型号一长串字母数字，打一个错就要重来。要是电脑能自动识别就好了，我只要检查一下确认就行。" |
| **Context 场景** | 工位有扫描仪和高拍仪。日常用 Windows 电脑操作 WMS 客户端（非 Web 版，无 API）。中文输入速度约 40 字/分钟。偶尔用手机拍单据照片。能使用基本软件但不懂编程。 |
| **Goals 目标** | 减少重复劳动；降低因录入错误被追责的风险；有更多时间做仓库其他工作。 |
| **Frustrations 痛点** | 长时间打字导致腱鞘炎；手写单据辨认困难；WMS 界面不支持批量导入。 |

### Persona 2: 仓库主管刘哥 — "The Throughput Manager"

| 维度 | 描述 |
|---|---|
| **Identity 身份** | 刘强，38 岁，仓库主管，管理 8 人团队（含 2 名录入员）。负责确保出入库流程顺畅。 |
| **Voice 声音** | "我的 KPI 是收货后 2 小时内完成系统录入。但实际上经常要 4-6 小时，碰到月底更夸张，单据堆成山。我要是能把录入时间砍掉一半，就能把人调去做更有价值的事情。" |
| **Context 场景** | 在仓库和办公室之间走动。通过钉钉群管理团队。需要随时知道录入进度。关注效率指标和人力利用率。 |
| **Goals 目标** | 实现 2 小时内录入 SLA；释放录入员工时用于其他岗位；减少录入错误引发的库存差异。 |
| **Frustrations 痛点** | 录入积压影响整体运营效率；错误发现滞后，纠错成本高。 |

### Persona 3: 质量审计员周姐 — "The Compliance Guardian"

| 维度 | 描述 |
|---|---|
| **Identity 身份** | 周丽，32 岁，质量与合规审计员。负责季度库存审计和合规检查。 |
| **Voice 声音** | "每次审计我都要拿着系统记录去翻纸质档案柜，一找就是半天。要是每条系统记录都能链接到原始单据的扫描件，审计效率能提高 10 倍。而且我还能追溯到底是识别错误还是人为错误。" |
| **Context 场景** | 季度审计时集中工作 1-2 周。需要原始凭证与系统记录的对应关系。关注数据准确性和可追溯性。 |
| **Goals 目标** | 每条 WMS 记录可追溯至原始单据影像；审计时间减少 50%。 |
| **Frustrations 痛点** | 纸质归档混乱，查找困难；无法判断错误来源（OCR 还是人工）。 |

---

## 4. Solution Overview 解决方案概述

### 4.1 System Architecture 系统架构

```
                          ┌─────────────────────┐
                          │   Watched Folder     │
                          │   (新单据图片)        │
                          └──────────┬──────────┘
                                     │ FileSystemWatcher
                                     ▼
┌──────────────────────────────────────────────────────────────┐
│                     ReceiptBot Pipeline                       │
│                                                              │
│  ┌─────────────────┐                                         │
│  │ Image Preprocess │  rotation / deskew / enhance /         │
│  │ (OpenCV/Pillow)  │  binarization / denoise                │
│  └────────┬────────┘                                         │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │ OCR Engine       │  PaddleOCR (Chinese + English)         │
│  │ (PaddleOCR)      │  → raw text blocks with coordinates    │
│  └────────┬────────┘                                         │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │ Field Extractor  │  regex patterns + fuzzy matching       │
│  │ (regex + fuzzy)  │  → structured fields + confidence      │
│  └────────┬────────┘                                         │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           Confidence-Based Router                        │ │
│  │                                                         │ │
│  │   ≥90%            70%-90%           <70%                │ │
│  │   AUTO-PASS       MANUAL REVIEW     FORCE REVIEW        │ │
│  │   ┌─────┐         ┌──────────┐     ┌──────────┐       │ │
│  │   │Queue│         │ Tkinter  │     │ Tkinter  │       │ │
│  │   │→RPA │         │ Review   │     │ Review   │       │ │
│  │   │     │         │ UI       │     │ UI (all  │       │ │
│  │   │     │         │ (flagged │     │  fields  │       │ │
│  │   │     │         │  fields) │     │  flagged)│       │ │
│  │   └──┬──┘         └────┬─────┘     └────┬─────┘       │ │
│  │      │                 │                │              │ │
│  │      └────────────┬────┘────────────────┘              │ │
│  └───────────────────┼────────────────────────────────────┘ │
│                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              RPA Entry Engine (pyautogui)                │ │
│  │  → Click fields → Type values → Tab between fields      │ │
│  │  → Submit form → Screenshot verification                │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Core Modules 核心模块

#### Module 1: Folder Watcher 文件夹监控
- **技术**: `watchdog` library — monitors configured directory for new image files
- **Supported formats**: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.bmp`, `.pdf` (first page)
- **Behavior**: On new file detected → wait 2s for write completion → enqueue for processing
- **Deduplication**: MD5 hash check to avoid processing the same file twice
- **Archive**: After processing, move source image to `archive/YYYY-MM-DD/` folder

#### Module 2: Image Preprocessor 图像预处理
- **技术栈**: OpenCV (`cv2`) + Pillow (`PIL`)
- **Processing pipeline**:
  1. **Rotation correction 旋转校正**: Detect text orientation via Hough line transform or PaddleOCR's built-in angle detection; auto-rotate to upright
  2. **Deskew 倾斜校正**: Correct minor skew (< 15 degrees) using affine transform
  3. **Enhancement 增强**: Adaptive histogram equalization (CLAHE) for uneven lighting
  4. **Binarization 二值化**: Adaptive thresholding (Gaussian) for mixed print/handwrite documents
  5. **Denoising 降噪**: Non-local means denoising for scanned documents; morphological operations for stamp/seal removal on key fields
  6. **Resolution normalization**: Upscale images below 300 DPI to 300 DPI for optimal OCR
- **Output**: Preprocessed image array passed to OCR engine; original preserved for review UI

#### Module 3: OCR Engine OCR 识别引擎
- **技术**: PaddleOCR (`paddleocr` Python package)
- **Model configuration**:
  - Detection model: `ch_PP-OCRv4_det` (text region detection)
  - Recognition model: `ch_PP-OCRv4_rec` (Chinese + English + numbers)
  - Direction classifier: `ch_ppocr_mobile_v2.0_cls` (text direction)
  - `use_angle_cls=True` for rotated text handling
  - `lang='ch'` (includes English recognition)
- **Output**: List of `(bounding_box, text, confidence)` tuples, sorted top-to-bottom, left-to-right
- **Performance target**: Process one standard A4 receipt image in < 3 seconds on CPU

#### Module 4: Field Extractor 字段提取器
- **Strategy**: Two-phase extraction
  - **Phase 1 — Regex patterns**: Predefined patterns for structured fields
    - 日期 Date: `r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?'`
    - 单据编号 Receipt No.: `r'[A-Z]{2,4}-\d{6,10}'` or `r'No[.:]?\s*\d+'`
    - 数量 Quantity: `r'(\d+(?:\.\d+)?)\s*(个|件|箱|kg|吨|pcs|EA)'`
    - 金额 Amount: `r'[¥￥$]\s*[\d,]+\.?\d*'` or `r'(\d[\d,]*\.\d{2})\s*元'`
    - 电话 Phone: `r'1[3-9]\d{9}'`
  - **Phase 2 — Fuzzy matching**: For semi-structured fields
    - 供应商名称 Supplier name: Match OCR text against known supplier list using `fuzzywuzzy.fuzz.token_sort_ratio` with threshold ≥ 80
    - 物料名称 Item name: Match against SKU master data
    - 仓库名称 Warehouse: Match against warehouse list
- **Confidence scoring**: Per-field confidence = `OCR_confidence * extraction_confidence`
  - `OCR_confidence`: From PaddleOCR output
  - `extraction_confidence`: 1.0 for exact regex match, scaled by fuzzy ratio for fuzzy matches
- **Output**: `ExtractedReceipt` object with fields and per-field confidence scores

#### Module 5: Confidence Router 置信度路由器
- **Routing logic**:

| Overall Confidence | Route | Behavior |
|---|---|---|
| **≥ 90%** (all fields ≥ 90%) | AUTO-PASS 自动通过 | Directly queue for RPA entry; log for post-audit |
| **70% - 90%** (any field 70-90%, none < 70%) | MANUAL REVIEW 人工复核 | Open Tkinter review UI with low-confidence fields highlighted in orange |
| **< 70%** (any field < 70%) | FORCE REVIEW 强制复核 | Open Tkinter review UI with all fields editable, critical fields highlighted in red |

- **Overall confidence** = minimum of all individual field confidences
- **Configurable thresholds**: Upper and lower bounds adjustable in config

#### Module 6: Review UI 人工复核界面
- **技术**: Tkinter (Python built-in, no extra installation)
- **Layout**:
  ```
  ┌──────────────────────────────────────────────────────┐
  │  ReceiptBot Review — 单据复核                  [—][□][×]│
  ├───────────────────────┬──────────────────────────────┤
  │                       │  单据编号: [RK-20260314-001] │
  │                       │  日期:     [2026-03-14     ] │
  │   Original Image      │  供应商:   [华东五金有限公司 ] │ ← orange bg
  │   (zoomable,          │  物料编码: [WH-BOLT-M8     ] │
  │    pannable)          │  物料名称: [M8六角螺栓      ] │
  │                       │  数量:     [500            ] │
  │                       │  单位:     [个              ] │
  │                       │  单价:     [0.85           ] │ ← red bg
  │                       │  金额:     [425.00         ] │
  │                       │  备注:     [               ] │
  │                       ├──────────────────────────────┤
  │                       │  Confidence: 78.5%           │
  │                       │  [✓ Confirm 确认] [✗ Reject] │
  │                       │  [◀ Previous]  [Next ▶]      │
  └───────────────────────┴──────────────────────────────┘
  ```
- **Features**:
  - Left panel: Original image with zoom/pan (mouse wheel + drag)
  - Right panel: Extracted fields in editable text boxes
  - Color coding: Green (≥90%), Orange (70-90%), Red (<70%) field backgrounds
  - Keyboard shortcuts: `Enter` = Confirm, `Escape` = Skip to next, `Ctrl+Z` = Undo
  - Batch queue: Process multiple pending reviews in sequence with Previous/Next navigation
  - Field-to-image linking: Click a field to highlight its bounding box on the image

#### Module 7: RPA Entry Engine RPA 录入引擎
- **技术**: `pyautogui` for mouse/keyboard automation
- **WMS interaction flow**:
  1. Activate WMS window (`pyautogui.getWindowsWithTitle()`)
  2. Navigate to receipt entry form (configurable click coordinates or image recognition)
  3. For each field: click target input → clear existing content → type value → Tab to next
  4. Handle dropdowns: type partial text → wait for suggestion → select
  5. Submit form (click Save button)
  6. Wait for confirmation dialog → screenshot for verification
- **Safety mechanisms**:
  - Pre-entry screenshot to verify correct WMS page
  - Inter-keystroke delay (configurable, default 50ms) to avoid input dropping
  - Failsafe: `pyautogui.FAILSAFE = True` — move mouse to top-left corner to abort
  - Lock screen detection: pause if screen is locked
- **WMS field mapping**: Configurable YAML mapping receipt fields → WMS UI coordinates/tab-order

#### Module 8: Screenshot Verifier 截图验证器
- **Process**:
  1. After RPA entry + form submission, capture full-screen screenshot
  2. Crop WMS data area using configured coordinates
  3. Run PaddleOCR on cropped screenshot
  4. Compare OCR results against entered values (fuzzy match with threshold ≥ 95%)
  5. If match: mark as "verified" ✓ — archive screenshot
  6. If mismatch: mark as "verification failed" ✗ — queue for human review
- **Storage**: `archive/YYYY-MM-DD/{receipt_id}_entry_screenshot.png`

---

## 5. Success Metrics 成功指标

### 5.1 Primary KPIs 核心指标

| # | Metric 指标 | Current Baseline 当前基线 | Target 目标 | Measurement 测量方式 |
|---|---|---|---|---|
| 1 | 单据录入耗时 Per-Receipt Entry Time | 3-5 minutes (manual) | < 1 minute (auto + review) | Timestamp: image detected → WMS entry confirmed |
| 2 | 日录入能力 Daily Throughput | 40-60 receipts / person / day | 150+ receipts / person / day (with supervision) | Daily processed receipt count |
| 3 | 录入错误率 Entry Error Rate | ~5% of fields (manual) | < 1% of fields (with confidence routing) | Post-entry audit sampling |
| 4 | 录入积压时间 Entry Backlog Delay | 4-6 hours average | < 1 hour average | Time delta between receipt arrival and WMS entry |
| 5 | 自动通过率 Auto-Pass Rate | 0% (all manual) | ≥ 60% of receipts (confidence ≥ 90%) | Count of auto-passed / total receipts |

### 5.2 Secondary KPIs 辅助指标

| # | Metric 指标 | Target 目标 |
|---|---|---|
| 6 | OCR 识别准确率 OCR Character Accuracy | ≥ 95% on printed text, ≥ 85% on handwritten |
| 7 | 字段提取准确率 Field Extraction Accuracy | ≥ 92% (correct field assignment) |
| 8 | RPA 成功率 RPA Entry Success Rate | ≥ 98% (no WMS interaction errors) |
| 9 | 截图验证通过率 Screenshot Verification Pass Rate | ≥ 97% |
| 10 | 人工复核平均耗时 Avg. Manual Review Time | < 30 seconds per receipt |
| 11 | 系统处理速度 Processing Speed | < 10 seconds per receipt (preprocess + OCR + extract) |
| 12 | 原始单据可追溯率 Source Traceability Rate | 100% of WMS entries linked to source image |

---

## 6. User Stories 用户故事

### User Story 1: 自动监控文件夹并触发单据处理

> **As a** 数据录入员 (data entry clerk),
> **I want** the system to automatically detect when I scan or copy a new receipt image into the watched folder,
> **so that** I don't have to manually trigger the processing and can focus on reviewing results instead.

**Story Points**: 3 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Automatic Folder Watching and Processing Trigger

  Background:
    Given the ReceiptBot service is running
    And the watched folder is configured as "D:\warehouse\incoming_receipts\"
    And the archive folder is configured as "D:\warehouse\archive\"

  Scenario: Detect and process a new receipt image
    Given the watched folder is empty
    When a new file "receipt_001.jpg" is copied into the watched folder
    Then the system should detect the new file within 5 seconds
    And wait 2 seconds for the file write to complete
    And enqueue the file for the processing pipeline
    And display a log entry: "新单据检测到: receipt_001.jpg, 已加入处理队列"

  Scenario: Handle supported file formats
    When files with extensions .jpg, .png, .tif, .bmp, .pdf are added to the folder
    Then all files should be accepted and enqueued for processing
    When a file with extension .docx is added to the folder
    Then the file should be ignored with a warning log: "不支持的文件格式: .docx"

  Scenario: Prevent duplicate processing
    Given "receipt_001.jpg" has already been processed (MD5 hash recorded)
    When an identical file "receipt_001_copy.jpg" with the same MD5 hash is added
    Then the system should skip the file
    And log: "重复文件已跳过: receipt_001_copy.jpg (MD5 matches receipt_001.jpg)"

  Scenario: Archive processed images
    Given "receipt_001.jpg" has been fully processed
    Then the file should be moved to "D:\warehouse\archive\2026-03-14\receipt_001.jpg"
    And the original file should no longer exist in the watched folder
```

---

### User Story 2: 图像预处理以优化 OCR 识别质量

> **As a** 系统 (the system),
> **I want** to automatically preprocess receipt images (rotation, enhancement, binarization),
> **so that** the OCR engine receives optimal-quality input, maximizing text recognition accuracy even for low-quality scans and photos.

**Story Points**: 5 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Image Preprocessing Pipeline

  Scenario: Correct rotated image
    Given a receipt image "receipt_rotated.jpg" is rotated 90 degrees clockwise
    When the image preprocessor runs
    Then the image should be auto-rotated to upright orientation
    And the rotation angle should be logged: "图像旋转校正: -90°"

  Scenario: Correct skewed scan
    Given a receipt image "receipt_skewed.jpg" has a 7-degree skew
    When the image preprocessor runs
    Then the skew should be corrected via affine transform
    And the deskew angle should be logged: "倾斜校正: 7.0°"

  Scenario: Enhance low-contrast image
    Given a receipt image "receipt_dark.jpg" has poor contrast (mean brightness < 80)
    When the image preprocessor applies CLAHE enhancement
    Then the output image contrast should be measurably improved
    And text regions should have clearer separation from the background

  Scenario: Binarize for mixed print and handwriting
    Given a receipt image contains both printed and handwritten text
    When adaptive thresholding is applied
    Then both printed and handwritten text should be preserved as black-on-white
    And background artifacts (stamps, colored borders) should be minimized

  Scenario: Upscale low-resolution image
    Given a receipt image has resolution 150 DPI
    When the preprocessor checks resolution
    Then the image should be upscaled to 300 DPI using bicubic interpolation
    And the log should note: "分辨率提升: 150 DPI → 300 DPI"

  Scenario: Preserve original image
    Given any image undergoes preprocessing
    Then the original unmodified image should be preserved for the review UI
    And only the preprocessed copy should be passed to the OCR engine
```

---

### User Story 3: OCR 识别中英文混合单据内容

> **As a** 数据录入员 (data entry clerk),
> **I want** the system to accurately recognize both Chinese and English text on receipts, including printed text, handwritten annotations, and alphanumeric codes,
> **so that** I don't have to manually type out hard-to-read characters and product codes.

**Story Points**: 8 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: PaddleOCR Chinese+English Mixed Text Recognition

  Background:
    Given PaddleOCR is initialized with:
      | parameter       | value                          |
      | lang            | ch                             |
      | use_angle_cls   | true                           |
      | det_model_dir   | ch_PP-OCRv4_det                |
      | rec_model_dir   | ch_PP-OCRv4_rec                |

  Scenario: Recognize printed Chinese text
    Given a receipt image contains printed Chinese text: "华东五金有限公司"
    When PaddleOCR processes the preprocessed image
    Then the recognized text should include "华东五金有限公司" with confidence ≥ 95%

  Scenario: Recognize mixed Chinese-English product codes
    Given a receipt contains the product code "M8×30六角螺栓 GB/T5782-2016"
    When PaddleOCR processes the image
    Then the recognized text should include both the Chinese description and English/numeric code
    And character-level accuracy should be ≥ 90%

  Scenario: Recognize handwritten quantities
    Given a receipt contains handwritten text "数量: 500"
    When PaddleOCR processes the image
    Then the system should recognize the digits with confidence ≥ 80%
    And if confidence is below 90%, the field should be flagged for manual review

  Scenario: Handle table-structured receipt
    Given a receipt image contains a table with rows of items
    When PaddleOCR processes the image
    Then text blocks should be returned with bounding box coordinates
    And blocks should be sortable into rows and columns by coordinate proximity
    And each row should correspond to one line item on the receipt

  Scenario: Process one receipt within performance target
    Given a standard A4 receipt image (300 DPI, ~2000×3000 px)
    When PaddleOCR processes the image
    Then the total OCR time should be < 3 seconds on CPU
    And the output should include all detected text blocks with confidence scores
```

---

### User Story 4: 字段提取与置信度路由

> **As a** 仓库主管 (warehouse supervisor),
> **I want** the system to automatically extract structured fields from OCR text and route them based on confidence levels,
> **so that** high-confidence entries are processed instantly while questionable ones get human attention — balancing speed with accuracy.

**Story Points**: 8 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Field Extraction and Confidence-Based Routing

  Scenario: Extract date field via regex
    Given OCR output contains the text block "入库日期: 2026年03月14日"
    When the field extractor processes this text
    Then the extracted date should be "2026-03-14"
    And the extraction confidence should be ≥ 95%

  Scenario: Extract supplier name via fuzzy matching
    Given OCR output contains "华东五金有限公刊" (OCR error: 刊 instead of 司)
    And the supplier master list contains "华东五金有限公司"
    When fuzzy matching runs with threshold 80%
    Then the matched supplier should be "华东五金有限公司"
    And the fuzzy match ratio should be approximately 87.5%
    And the field confidence should reflect the fuzzy ratio

  Scenario: Route high-confidence receipt to AUTO-PASS
    Given all extracted fields for receipt "RK-001" have confidence ≥ 90%
    When the confidence router evaluates the receipt
    Then the receipt should be routed to AUTO-PASS queue
    And no manual review should be required
    And the log should record: "RK-001: 自动通过 (min_confidence=92.3%)"

  Scenario: Route medium-confidence receipt to MANUAL REVIEW
    Given receipt "RK-002" has field confidences:
      | field      | confidence |
      | date       | 96%        |
      | supplier   | 83%        |
      | quantity   | 95%        |
      | amount     | 78%        |
    When the confidence router evaluates the receipt
    Then the overall confidence should be 78% (minimum of all fields)
    And the receipt should be routed to MANUAL REVIEW
    And the "supplier" and "amount" fields should be highlighted for attention

  Scenario: Route low-confidence receipt to FORCE REVIEW
    Given receipt "RK-003" has a field "supplier" with confidence 55%
    When the confidence router evaluates the receipt
    Then the receipt should be routed to FORCE REVIEW
    And ALL fields should be marked as requiring verification
    And the review UI should display all fields with editable backgrounds

  Scenario: Configurable confidence thresholds
    Given the config file sets auto_pass_threshold=85 and review_threshold=65
    When a receipt has overall confidence 87%
    Then it should be routed to AUTO-PASS (≥85%)
    When a receipt has overall confidence 70%
    Then it should be routed to MANUAL REVIEW (65-85%)
    When a receipt has overall confidence 60%
    Then it should be routed to FORCE REVIEW (<65%)
```

---

### User Story 5: 人工复核界面操作

> **As a** 数据录入员 (data entry clerk),
> **I want** a clear, intuitive review interface that shows me the original receipt image alongside extracted fields with confidence indicators,
> **so that** I can quickly verify and correct OCR results without switching between windows or re-reading the entire document.

**Story Points**: 8 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Tkinter Manual Review UI

  Scenario: Display review interface with image and fields
    Given a receipt "RK-002" is routed to MANUAL REVIEW
    When the review UI opens for this receipt
    Then the left panel should display the original (non-preprocessed) receipt image
    And the right panel should show all extracted fields in editable text boxes
    And fields with confidence < 90% should have orange backgrounds
    And fields with confidence < 70% should have red backgrounds
    And the overall confidence percentage should be displayed at the bottom

  Scenario: Zoom and pan on receipt image
    Given the review UI is open with a receipt image
    When the user scrolls the mouse wheel on the image panel
    Then the image should zoom in/out centered on the cursor position
    When the user clicks and drags on the image
    Then the image should pan in the drag direction

  Scenario: Edit and confirm fields
    Given the review UI shows "供应商: 华东五金有限公刊" with orange background
    When the user corrects the field to "华东五金有限公司"
    And clicks the "确认 Confirm" button (or presses Enter)
    Then the corrected value should be saved
    And the receipt should be queued for RPA entry
    And the review UI should advance to the next pending receipt

  Scenario: Navigate between pending reviews
    Given there are 5 receipts pending review
    When the user clicks "Next ▶" or presses the right arrow key
    Then the UI should display the next pending receipt
    When the user clicks "◀ Previous"
    Then the UI should display the previous receipt

  Scenario: Reject a receipt
    Given the review UI is showing a severely damaged/unreadable receipt
    When the user clicks "Reject 驳回"
    Then the receipt should be marked as "rejected" in the processing log
    And moved to "archive/rejected/" folder
    And a note should be recorded explaining it requires manual entry
    And the UI should advance to the next pending receipt

  Scenario: Keyboard shortcuts for efficiency
    Given the review UI is open
    When the user presses Enter, the current receipt should be confirmed
    When the user presses Escape, the current receipt should be skipped
    When the user presses Ctrl+Z, the last edit should be undone
    When the user presses Tab, focus should move to the next field
```

---

### User Story 6: RPA 自动录入 WMS

> **As a** 数据录入员 (data entry clerk),
> **I want** the system to automatically enter verified receipt data into the WMS application using RPA,
> **so that** I am freed from repetitive typing and can focus on exception handling and quality verification.

**Story Points**: 13 | **Priority**: P0-Must Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: pyautogui RPA Auto-Entry into WMS

  Background:
    Given the WMS application is running and logged in
    And the RPA field mapping is configured in wms_mapping.yaml:
      | receipt_field | wms_action                          |
      | receipt_no    | click(120,250) → type → tab         |
      | date          | click(120,290) → type → tab         |
      | supplier      | click(120,330) → type → wait → select|
      | item_code     | click(120,400) → type → tab         |
      | quantity      | click(320,400) → type → tab         |
      | unit_price    | click(420,400) → type → tab         |

  Scenario: Successfully enter a receipt into WMS
    Given a verified receipt with all fields confirmed
    And the WMS is on the receipt entry page
    When the RPA engine processes the receipt
    Then for each field in the mapping:
      - The mouse should click the target coordinates
      - The existing content should be cleared (Ctrl+A → Delete)
      - The field value should be typed with inter-keystroke delay of 50ms
      - A Tab key should be pressed to move to the next field
    And the Save button should be clicked
    And the system should wait for the WMS confirmation dialog

  Scenario: Handle WMS dropdown/autocomplete fields
    Given the "supplier" field in WMS is a dropdown with autocomplete
    When the RPA engine enters the supplier name
    Then it should type the first 4 characters of the supplier name
    And wait 500ms for the autocomplete suggestion list
    And select the matching suggestion (via arrow keys + Enter)

  Scenario: Pre-entry WMS page verification
    Given the RPA engine is about to start entry
    When it takes a pre-entry screenshot
    Then it should verify the WMS is on the correct page (receipt entry form)
    And if the page is incorrect, the entry should be aborted with error: "WMS 页面不正确，录入已取消"

  Scenario: Failsafe mechanism
    Given the RPA engine is in the middle of entering data
    When the user moves the mouse to the top-left corner of the screen (0,0)
    Then pyautogui.FailSafeException should be raised
    And all RPA operations should immediately stop
    And the current receipt should be marked as "entry_interrupted"
    And a log entry should record the interruption

  Scenario: Handle WMS error dialog
    Given the RPA engine has submitted a receipt
    When the WMS displays an error dialog (e.g., "物料编码不存在")
    Then the RPA engine should detect the error dialog via image recognition
    And capture a screenshot of the error
    And mark the receipt as "entry_failed" with the error message
    And dismiss the dialog and return WMS to a clean state
```

---

### User Story 7: 录入后截图验证

> **As a** 质量审计员 (quality auditor),
> **I want** the system to take a screenshot after each WMS entry and verify the entered data matches the source,
> **so that** every entry has a verifiable audit trail linking the original receipt image to the WMS record.

**Story Points**: 5 | **Priority**: P1-Should Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Post-Entry Screenshot Verification

  Scenario: Capture and verify successful entry
    Given the RPA engine has just submitted receipt "RK-001" into WMS
    And the WMS shows the saved record on screen
    When the screenshot verifier runs
    Then a full-screen screenshot should be captured
    And the WMS data area should be cropped using configured coordinates
    And PaddleOCR should be run on the cropped area
    And each recognized value should be compared against the entered data
    And if all fields match (fuzzy ratio ≥ 95%), mark as "verified ✓"
    And save the screenshot to "archive/2026-03-14/RK-001_entry_verified.png"

  Scenario: Detect verification mismatch
    Given the RPA entered quantity "500" for receipt "RK-002"
    But the screenshot OCR reads quantity as "50" (digit dropped during entry)
    When the verifier compares values
    Then the mismatch should be detected for the "quantity" field
    And the receipt should be marked as "verification_failed ✗"
    And the receipt should be queued for re-entry or manual correction
    And a notification should be sent to the supervisor

  Scenario: Archive screenshots for audit trail
    Given receipt "RK-001" has been verified
    Then the following files should exist in the archive:
      | file                                           | purpose              |
      | archive/2026-03-14/RK-001_original.jpg         | Original receipt     |
      | archive/2026-03-14/RK-001_preprocessed.jpg     | Preprocessed for OCR |
      | archive/2026-03-14/RK-001_entry_verified.png   | WMS screenshot       |
      | archive/2026-03-14/RK-001_metadata.json        | Extraction results   |
    And the metadata.json should contain: extracted fields, confidences, route taken, reviewer (if any), entry timestamp, verification result

  Scenario: Handle verification timeout
    Given the WMS takes longer than 10 seconds to refresh after submission
    When the screenshot verifier waits for the expected page
    Then after 10 seconds timeout, retry screenshot capture once
    And if still unable to verify, mark as "verification_timeout" and queue for manual check
```

---

### User Story 8: 处理批量单据队列

> **As a** 仓库主管 (warehouse supervisor),
> **I want** the system to process multiple receipt images in a FIFO queue with progress tracking,
> **so that** I can monitor the processing status and ensure no receipt is lost or stuck.

**Story Points**: 5 | **Priority**: P1-Should Have

**Acceptance Criteria (Gherkin)**:

```gherkin
Feature: Batch Processing Queue Management

  Scenario: Process multiple receipts in FIFO order
    Given 10 receipt images are in the watched folder
    When the system detects and enqueues all 10 files
    Then files should be processed in the order they were detected (by file modification time)
    And each file should go through the complete pipeline sequentially:
      preprocess → OCR → extract → route → review (if needed) → RPA → verify

  Scenario: Display queue status
    Given 10 receipts are enqueued, 3 completed, 1 in review, 6 pending
    When the system displays status (in log and/or tray icon tooltip)
    Then the status should show:
      | status       | count |
      | 已完成       | 3     |
      | 待复核       | 1     |
      | 处理中       | 1     |
      | 排队中       | 5     |
      | 总计         | 10    |

  Scenario: Continue processing after review
    Given receipt "RK-005" is routed to MANUAL REVIEW
    And receipts "RK-006" through "RK-010" are in AUTO-PASS queue
    When the reviewer has not yet opened the review UI
    Then AUTO-PASS receipts should continue processing via RPA
    And MANUAL REVIEW receipts should wait in the review queue
    And the two queues should not block each other

  Scenario: Handle processing failure gracefully
    Given receipt "RK-007" causes an unexpected error during OCR
    When the error occurs
    Then the error should be logged with full stack trace
    And the receipt should be moved to "failed/" folder
    And processing should continue with the next receipt "RK-008"
    And the daily summary should include the failure count
```

---

## 7. Scope 范围

### 7.1 In Scope 范围内

| # | Feature 功能 | Description 描述 |
|---|---|---|
| 1 | 文件夹监控 | watchdog 监控指定目录，自动检测新增图片文件 |
| 2 | 图像预处理 | OpenCV 旋转校正、倾斜校正、增强、二值化、降噪、分辨率归一化 |
| 3 | OCR 识别 | PaddleOCR 中英文混合识别，输出文本+坐标+置信度 |
| 4 | 字段提取 | Regex 正则匹配 + fuzzywuzzy 模糊匹配，结构化字段提取 |
| 5 | 置信度路由 | 三级路由：≥90% 自动通过 / 70-90% 人工复核 / <70% 强制复核 |
| 6 | Tkinter 复核 UI | 原始图片 + 可编辑字段 + 置信度标色 + 键盘快捷键 |
| 7 | RPA 自动录入 | pyautogui 模拟键鼠操作录入 WMS 客户端 |
| 8 | 截图验证 | 录入后截图 + OCR 反向验证 + 存档 |
| 9 | 批量队列管理 | FIFO 队列，自动通过和人工复核并行不阻塞 |
| 10 | 审计追溯 | 原始图片 + 预处理图 + 截图 + metadata.json 完整存档 |

### 7.2 Out of Scope 范围外

| # | Feature 功能 | Reason 原因 | Future Phase 未来阶段 |
|---|---|---|---|
| 1 | WMS API 直连 | WMS 无开放 API，只能通过 UI 操作 | 如 WMS 升级后考虑 |
| 2 | 手写体专项训练 | 需大量标注数据和模型训练周期，PaddleOCR 内置模型先用 | Phase 2 |
| 3 | Web 版复核界面 | Tkinter 本地界面已满足单机使用场景 | Phase 2 |
| 4 | 多用户并发录入 | 当前只有 1-2 名录入员，单机串行即可 | Phase 2 |
| 5 | 自动学习/模型微调 | 需积累足够标注数据后进行 | Phase 3 |
| 6 | 移动端拍照上传 | 当前通过扫描仪/高拍仪获取图片，移动端可通过文件夹同步实现 | Phase 2 |
| 7 | 多 WMS 系统适配 | 当前仅对接 1 套 WMS | Phase 2 |
| 8 | 发票/税务单据处理 | 涉及发票验真等额外合规要求 | Phase 3 |

---

## 8. Risks & Mitigations 风险与缓解措施

| # | Risk 风险 | Probability 概率 | Impact 影响 | Mitigation 缓解措施 |
|---|---|---|---|---|
| 1 | **OCR 识别率不达标** OCR accuracy below target, especially on handwritten/low-quality documents | Medium 中 | High 高 | 多级预处理管道提升输入质量；置信度路由确保低质量结果一定经过人工复核；收集错误样本用于后续模型微调 |
| 2 | **WMS UI 变更导致 RPA 失效** WMS UI layout changes break RPA coordinate mappings | Medium 中 | High 高 | RPA 坐标配置外部化（YAML），非硬编码；支持图像识别模式（`pyautogui.locateOnScreen`）作为备选；WMS 更新后快速重新标定坐标 |
| 3 | **pyautogui 输入丢失** Keystrokes dropped by WMS (input too fast or WMS lag) | Medium 中 | Medium 中 | 可配置 inter-keystroke delay（默认 50ms，可调至 100ms）；每个字段输入后读回验证；WMS 响应慢时自动增加等待时间 |
| 4 | **图片质量差异大** Highly variable image quality (phone photos vs. scanner vs. fax) | High 高 | Medium 中 | 自适应预处理管道根据图片特征选择最佳处理策略；极低质量图片强制人工复核 |
| 5 | **PaddleOCR 模型加载慢** PaddleOCR model initialization time (~10-15s cold start) | Low 低 | Low 低 | 服务常驻内存，模型只在启动时加载一次；使用 PaddleOCR Server 模式避免重复初始化 |
| 6 | **RPA 与用户操作冲突** User accidentally moves mouse or uses keyboard during RPA entry | Medium 中 | Medium 中 | RPA 执行前弹窗提示"正在自动录入，请勿操作鼠标键盘"；pyautogui.FAILSAFE 机制紧急中断；可配置在用户不活跃时段批量执行 |
| 7 | **单据格式多样化** Different suppliers use different receipt formats | High 高 | Medium 中 | 字段提取器支持多套 regex 模板，按供应商/单据类型匹配；模糊匹配兜底；新格式快速添加模板配置 |
| 8 | **审计合规性质疑** Auditors question automated entry reliability | Low 低 | High 高 | 完整审计追溯链：原始图片 → OCR 结果 → 人工修正记录 → 截图验证；每条记录标注是"自动通过"还是"人工复核后通过" |
| 9 | **屏幕分辨率/缩放不一致** Different screen DPI/scaling breaks RPA coordinates | Medium 中 | Medium 中 | 启动时检测屏幕分辨率和 DPI 缩放比例，自动调整坐标；支持多套坐标配置 profile |
| 10 | **长时间运行内存泄露** Memory leak from PaddleOCR / image processing over extended sessions | Low 低 | Medium 中 | 每处理 N 张图片后强制 garbage collection；监控内存使用，超阈值自动重启服务 |

---

## Appendix A: Technical Dependencies 技术依赖

| Package | Version | Purpose |
|---|---|---|
| Python | ≥ 3.10 | Runtime |
| paddlepaddle | ≥ 2.5 | PaddleOCR backend (CPU version) |
| paddleocr | ≥ 2.7 | OCR engine (detection + recognition + classification) |
| opencv-python | ≥ 4.8 | Image preprocessing (rotation, deskew, binarize, denoise) |
| Pillow | ≥ 10.0 | Image I/O and basic manipulation |
| numpy | ≥ 1.24 | Image array operations |
| watchdog | ≥ 3.0 | File system event monitoring |
| pyautogui | ≥ 0.9.54 | RPA mouse/keyboard automation |
| fuzzywuzzy | ≥ 0.18 | Fuzzy string matching for field extraction |
| python-Levenshtein | ≥ 0.21 | Speed up fuzzywuzzy calculations |
| pyyaml | ≥ 6.0 | Configuration file parsing |
| tkinter | (built-in) | Review UI framework |

## Appendix B: Confidence Routing Decision Table 置信度路由决策表

```
Input: Per-field confidence scores for a single receipt

Step 1: Calculate overall_confidence = min(all field confidences)

Step 2: Apply routing rules:

┌─────────────────────────┬──────────────────┬─────────────────────────────┐
│ Condition               │ Route            │ UI Behavior                 │
├─────────────────────────┼──────────────────┼─────────────────────────────┤
│ overall ≥ 90%           │ AUTO-PASS        │ No UI; direct to RPA queue  │
│ 70% ≤ overall < 90%    │ MANUAL REVIEW    │ Open UI; flag fields < 90%  │
│ overall < 70%           │ FORCE REVIEW     │ Open UI; flag ALL fields    │
└─────────────────────────┴──────────────────┴─────────────────────────────┘

Thresholds are configurable in config/pipeline_config.yaml:
  auto_pass_threshold: 90
  manual_review_threshold: 70
```

## Appendix C: Sample Receipt Field Mapping 单据字段映射示例

```yaml
# config/field_templates.yaml
receipt_types:
  - name: "标准入库单"
    type: "inbound"
    fields:
      - name: "receipt_no"
        label: "入库单号"
        regex: "入库单号[：:]\s*([A-Z]{2}-\d{8,12})"
        required: true
      - name: "date"
        label: "日期"
        regex: "日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)"
        required: true
      - name: "supplier"
        label: "供应商"
        regex: "供应商[：:]\s*(.+?)(?:\s{2,}|$)"
        fuzzy_match_source: "supplier_master"
        required: true
      - name: "item_code"
        label: "物料编码"
        regex: "([A-Z]{2,4}-[A-Z0-9]+-[A-Z0-9]+)"
        fuzzy_match_source: "sku_master"
        required: true
      - name: "item_name"
        label: "物料名称"
        fuzzy_match_source: "sku_master"
        required: true
      - name: "quantity"
        label: "数量"
        regex: "(\d+(?:\.\d+)?)\s*(个|件|箱|kg|吨|pcs|EA)"
        required: true
      - name: "unit"
        label: "单位"
        regex: "\d+(?:\.\d+)?\s*(个|件|箱|kg|吨|pcs|EA)"
        required: true
      - name: "unit_price"
        label: "单价"
        regex: "[¥￥]?\s*(\d+(?:\.\d{1,4})?)"
        required: false
      - name: "total_amount"
        label: "金额"
        regex: "金额[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})"
        required: false
      - name: "warehouse"
        label: "仓库"
        fuzzy_match_source: "warehouse_list"
        required: true
      - name: "remark"
        label: "备注"
        regex: "备注[：:]\s*(.+?)$"
        required: false
```

## Appendix D: Archive Folder Structure 归档目录结构

```
D:\warehouse\
├── incoming_receipts\          ← Watched folder (images land here)
├── archive\
│   └── 2026-03-14\
│       ├── RK-001_original.jpg
│       ├── RK-001_preprocessed.jpg
│       ├── RK-001_entry_verified.png
│       ├── RK-001_metadata.json
│       ├── RK-002_original.jpg
│       ├── ...
│       └── daily_summary.json
├── failed\                     ← Images that failed processing
├── rejected\                   ← Images rejected by reviewer
├── config\
│   ├── pipeline_config.yaml
│   ├── wms_mapping.yaml
│   ├── field_templates.yaml
│   └── supplier_master.csv
└── logs\
    └── receiptbot_20260314.log
```

---

*Document generated on 2026-03-14. This is a living document and will be updated as the project evolves.*
