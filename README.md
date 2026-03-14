# 仓库自动化系统 (Warehouse Automation)

自动化仓库低库存预警、供应商询价和出入库单据OCR录入。

## 功能

### Feature 1: 低库存预警与自动询价
- 支持 Excel / SQL 双数据源读取库存
- SKU 阈值对比，生成严重/预警两级告警
- Playwright 无头浏览器自动抓取供应商报价
- 生成 xlsx 比价报表（条件格式化，最优价高亮）
- 邮件 + 钉钉/企微 webhook 通知

### Feature 2: 出入库单据自动录入
- watchdog 文件夹监控，自动发现新单据图片
- 图像预处理（旋转校正、对比度增强、二值化）
- PaddleOCR 中英混合文字识别
- 正则 + rapidfuzz 模糊匹配字段提取
- 置信度分流：≥90% 自动通过 / 70-90% 人工复核 / <70% 强制复核
- Tkinter 双栏复核界面（原图 + 可编辑字段）
- pyautogui RPA 自动录入 WMS

## 项目结构

```
warehouse-automation/
├── config/               # YAML 配置文件
├── feature1_inventory/   # 低库存预警模块
├── feature2_receipt/     # 单据自动录入模块
├── shared/               # 公共模块 (日志/审计/配置/加密)
├── tests/                # pytest 测试
├── docs/                 # PM 产品文档
└── requirements.txt
```

## 安装

```bash
cd warehouse-automation
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install chromium
```

## 配置

1. 生成加密密钥：
```bash
python -m shared.crypto --generate-key
```

2. 加密敏感凭据：
```bash
python -m shared.crypto --encrypt "your_password"
```

3. 将加密值填入 `config/suppliers.yaml` 的 `*_encrypted` 字段

4. 编辑 `config/settings.yaml` 设置数据源、邮件等参数

5. 编辑 `config/thresholds.yaml` 配置 SKU 阈值

6. 编辑 `config/wms_mapping.yaml` 校准 WMS 界面坐标

## 运行

### Feature 1: 低库存预警
```bash
python -m feature1_inventory.main
```
建议配置 Windows 任务计划程序，每天凌晨 2 点运行。

### Feature 2: 单据自动录入
```bash
python -m feature2_receipt.main
```
启动后持续监控 `data/receipts/` 文件夹，放入单据图片即自动处理。

## 测试

```bash
pytest tests/ -v --cov=feature1_inventory --cov=feature2_receipt --cov=shared
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 数据读取 | pandas, openpyxl, pyodbc |
| 浏览器自动化 | Playwright |
| OCR | PaddleOCR |
| 图像处理 | OpenCV, Pillow |
| RPA | pyautogui, pygetwindow |
| 字段匹配 | rapidfuzz |
| 配置管理 | PyYAML, Pydantic |
| 加密 | cryptography (Fernet) |
| 文件监控 | watchdog |
| 审计 | SQLite |
| 测试 | pytest |
