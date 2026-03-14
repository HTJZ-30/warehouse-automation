"""正则 + 模糊匹配字段提取模块"""

import re
from dataclasses import dataclass, field
from typing import Optional

from rapidfuzz import fuzz

from shared.logger import get_logger

logger = get_logger("field_parser")


@dataclass
class ParsedReceipt:
    """解析后的单据字段"""
    receipt_no: Optional[str] = None          # 单据编号
    receipt_type: Optional[str] = None        # 入库 / 出库
    product_name: Optional[str] = None        # 品名
    quantity: Optional[float] = None          # 数量
    unit: Optional[str] = None               # 单位
    date: Optional[str] = None               # 日期
    warehouse: Optional[str] = None          # 仓库
    supplier: Optional[str] = None           # 供应商
    remark: Optional[str] = None             # 备注
    raw_text: str = ""                        # OCR 原始文本
    field_confidences: dict[str, float] = field(default_factory=dict)

    @property
    def overall_confidence(self) -> float:
        if not self.field_confidences:
            return 0.0
        return sum(self.field_confidences.values()) / len(self.field_confidences)


# ── 正则模式 ───────────────────────────────────────────────────

# 单据编号: 常见格式 RK-20240101-001, CK20240101001, 入库单号:xxx
RECEIPT_NO_PATTERNS = [
    re.compile(r'(?:单[据号]|编号|No|NO|单据编号)[.:：\s]*([A-Z]*[\-]?\d{6,}[\-]?\d*)', re.IGNORECASE),
    re.compile(r'([RCrc][KkCc][\-]?\d{8,}[\-]?\d*)'),  # RK-20240101-001
    re.compile(r'(?:入库|出库|收货|发货)\s*(?:单[号]?)?[.:：\s]*([A-Za-z0-9\-]+)'),
]

# 数量
QUANTITY_PATTERNS = [
    re.compile(r'(?:数量|数目|Qty|QTY|quantity)[.:：\s]*(\d+\.?\d*)', re.IGNORECASE),
    re.compile(r'(\d+\.?\d*)\s*(?:个|件|箱|包|台|套|只|条|吨|kg|KG|pcs|PCS)'),
]

# 日期
DATE_PATTERNS = [
    re.compile(r'(?:日期|Date|date)[.:：\s]*(\d{4}[\-/年]\d{1,2}[\-/月]\d{1,2}日?)'),
    re.compile(r'(\d{4}[\-/]\d{1,2}[\-/]\d{1,2})'),
    re.compile(r'(\d{4}年\d{1,2}月\d{1,2}日)'),
]

# 品名
PRODUCT_NAME_PATTERNS = [
    re.compile(r'(?:品名|物料|产品名称|物资名称|货品|Product)[.:：\s]*(.+?)(?:\s{2,}|\n|$)', re.IGNORECASE),
    re.compile(r'(?:名称|品目)[.:：\s]*(.+?)(?:\s{2,}|\n|$)'),
]

# 单位
UNIT_PATTERNS = [
    re.compile(r'(?:单位|Unit)[.:：\s]*(个|件|箱|包|台|套|只|条|吨|千克|kg|pcs)', re.IGNORECASE),
]

# 仓库 — 要求冒号分隔，避免匹配标题 "WAREHOUSE RECEIPT"
WAREHOUSE_PATTERNS = [
    re.compile(r'(?:仓库|库房|库位)\s*(?:Warehouse)?[.:：]\s*(.+?)(?:\s{2,}|\n|$)', re.IGNORECASE),
    re.compile(r'Warehouse[.:：]\s*(.+?)(?:\s{2,}|\n|$)', re.IGNORECASE),
]

# 供应商 — 匹配最终值部分 (跳过中间的英文标签)
SUPPLIER_PATTERNS = [
    re.compile(r'(?:供应商|供货商)\s*(?:Supplier|Vendor)?[.:：]\s*(.+?)(?:\s{2,}|\n|$)', re.IGNORECASE),
    re.compile(r'(?:Supplier|Vendor)[.:：]\s*(.+?)(?:\s{2,}|\n|$)', re.IGNORECASE),
]

# 入库/出库类型
TYPE_KEYWORDS = {
    "入库": ["入库", "收货", "进货", "Inbound", "Receipt", "入库单"],
    "出库": ["出库", "发货", "出货", "Outbound", "Shipment", "出库单"],
}


def parse_ocr_result(ocr_result) -> ParsedReceipt:
    """从 OCR 结果中提取结构化字段

    策略: 先用 full_text 正则提取，若值为空或仅为标签残留，
    则回退到逐行匹配 — 找到标签行后取下一行作为值。

    Args:
        ocr_result: OCRResult 对象

    Returns:
        ParsedReceipt 包含提取的字段和置信度
    """
    full_text = ocr_result.full_text
    lines = [line.text for line in ocr_result.lines]
    parsed = ParsedReceipt(raw_text=full_text)

    # 逐行处理以利用 OCR 行置信度
    line_map = {line.text: line.confidence for line in ocr_result.lines}

    # 提取单据类型
    parsed.receipt_type = _extract_type(full_text)

    # 提取各字段
    parsed.receipt_no, conf = _extract_with_patterns(
        full_text, RECEIPT_NO_PATTERNS, line_map
    )
    if parsed.receipt_no:
        parsed.field_confidences["receipt_no"] = conf

    parsed.product_name, conf = _extract_with_patterns(
        full_text, PRODUCT_NAME_PATTERNS, line_map
    )
    # 回退: 如果品名提取结果看起来是标签残留，用逐行策略
    if _is_label_residue(parsed.product_name, ["Product", "品名", "物料", "名称"]):
        parsed.product_name, conf = _extract_next_line(
            lines, line_map,
            label_keywords=["品名", "Product", "物料", "产品名称", "物资名称"],
        )
    if parsed.product_name:
        parsed.field_confidences["product_name"] = conf

    qty_str, conf = _extract_with_patterns(full_text, QUANTITY_PATTERNS, line_map)
    if qty_str:
        try:
            parsed.quantity = float(qty_str)
            parsed.field_confidences["quantity"] = conf
        except ValueError:
            pass

    parsed.date, conf = _extract_with_patterns(full_text, DATE_PATTERNS, line_map)
    if parsed.date:
        parsed.field_confidences["date"] = conf

    parsed.unit, conf = _extract_with_patterns(full_text, UNIT_PATTERNS, line_map)
    if parsed.unit:
        parsed.field_confidences["unit"] = conf

    parsed.warehouse, conf = _extract_with_patterns(
        full_text, WAREHOUSE_PATTERNS, line_map
    )
    if _is_label_residue(parsed.warehouse, ["Warehouse", "仓库", "库房"]):
        parsed.warehouse, conf = _extract_next_line(
            lines, line_map,
            label_keywords=["仓库", "Warehouse", "库房", "库位"],
        )
    if parsed.warehouse:
        parsed.field_confidences["warehouse"] = conf

    parsed.supplier, conf = _extract_with_patterns(
        full_text, SUPPLIER_PATTERNS, line_map
    )
    if _is_label_residue(parsed.supplier, ["Supplier", "供应商", "供货商", "Vendor"]):
        parsed.supplier, conf = _extract_next_line(
            lines, line_map,
            label_keywords=["供应商", "Supplier", "供货商", "Vendor"],
        )
    if parsed.supplier:
        parsed.field_confidences["supplier"] = conf

    logger.info(
        "字段提取: 单号=%s, 品名=%s, 数量=%s, 置信度=%.2f%%",
        parsed.receipt_no, parsed.product_name, parsed.quantity,
        parsed.overall_confidence * 100,
    )
    return parsed


def _extract_type(text: str) -> Optional[str]:
    """识别入库/出库类型"""
    for type_name, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                return type_name
    return None


def _is_label_residue(value: Optional[str], label_keywords: list[str]) -> bool:
    """判断提取值是否为标签残留 (如 'Product:' 而非实际值)"""
    if value is None:
        return True
    clean = value.strip().rstrip(":：.").strip()
    if not clean:
        return True
    for kw in label_keywords:
        if clean.lower() == kw.lower() or clean.lower().startswith(kw.lower() + ":"):
            return True
    return False


def _extract_next_line(
    lines: list[str],
    line_map: dict[str, float],
    label_keywords: list[str],
) -> tuple[Optional[str], float]:
    """逐行查找标签，取其同行冒号后内容或下一行作为值

    处理 OCR 将 "品名 Product: 螺丝 M6x20" 拆为多行的情况:
    - 行1: "品名Product:"
    - 行2: "螺丝"
    - 行3: "M6x20"
    → 合并行2+行3 = "螺丝 M6x20"
    """
    for i, line in enumerate(lines):
        line_lower = line.lower()
        for kw in label_keywords:
            if kw.lower() in line_lower:
                # 尝试提取冒号后的内容
                for sep in [":", "：", "."]:
                    if sep in line:
                        after = line.split(sep, 1)[1].strip()
                        # 过滤掉仅为另一个标签关键词的情况
                        if after and not _is_label_residue(after, label_keywords):
                            conf = line_map.get(line, 0.5)
                            return after, conf

                # 冒号后为空或无冒号 → 取下一行
                if i + 1 < len(lines):
                    next_val = lines[i + 1].strip()
                    conf = line_map.get(lines[i + 1], 0.5)
                    # 可能值被拆成多行 (如 "螺丝" + "M6x20")，合并相邻非标签行
                    if i + 2 < len(lines):
                        next_next = lines[i + 2].strip()
                        # 如果下下行也不是标签行且较短，合并
                        if (not _line_is_label(next_next) and
                                len(next_next) < 30 and
                                not any(c in next_next for c in [":", "："])):
                            next_val = f"{next_val} {next_next}"
                    return next_val, conf

    return None, 0.0


def _line_is_label(line: str) -> bool:
    """判断一行是否为标签行 (包含已知标签关键词)"""
    all_keywords = [
        "单据", "编号", "品名", "Product", "数量", "Qty", "日期", "Date",
        "供应商", "Supplier", "仓库", "Warehouse", "备注", "Remark",
        "制单人", "审核人", "打印时间",
    ]
    line_lower = line.lower()
    return any(kw.lower() in line_lower for kw in all_keywords)


def _extract_with_patterns(
    text: str,
    patterns: list[re.Pattern],
    line_map: dict[str, float],
) -> tuple[Optional[str], float]:
    """用正则模式列表提取字段，返回 (值, 置信度)"""
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            # 从匹配行获取 OCR 置信度
            confidence = _get_line_confidence(match.group(0), line_map)
            return value, confidence
    return None, 0.0


def _get_line_confidence(matched_text: str, line_map: dict[str, float]) -> float:
    """用模糊匹配找到 OCR 行的置信度"""
    best_score = 0.0
    best_conf = 0.5  # 默认
    for line_text, conf in line_map.items():
        score = fuzz.partial_ratio(matched_text, line_text) / 100.0
        if score > best_score:
            best_score = score
            best_conf = conf
    return best_conf


def fuzzy_match_product(product_name: str, known_products: list[str], threshold: int = 70) -> Optional[str]:
    """模糊匹配品名到已知产品列表

    Args:
        product_name: OCR 识别的品名
        known_products: 已知产品名称列表
        threshold: 最低匹配分数 (0-100)

    Returns:
        最佳匹配的产品名，或 None
    """
    best_match = None
    best_score = 0
    for known in known_products:
        score = fuzz.ratio(product_name, known)
        if score > best_score:
            best_score = score
            best_match = known

    if best_score >= threshold:
        logger.info("模糊匹配: '%s' -> '%s' (分数 %d)", product_name, best_match, best_score)
        return best_match
    return None
