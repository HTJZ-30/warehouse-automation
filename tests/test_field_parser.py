"""测试: field_parser 字段解析"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature2_receipt.field_parser import (
    parse_ocr_result,
    fuzzy_match_product,
    RECEIPT_NO_PATTERNS,
    QUANTITY_PATTERNS,
    DATE_PATTERNS,
)


class MockOCRLine:
    def __init__(self, text, confidence=0.95):
        self.text = text
        self.confidence = confidence
        self.bbox = [[0, 0], [100, 0], [100, 20], [0, 20]]


class MockOCRResult:
    def __init__(self, lines):
        self.lines = [MockOCRLine(t, c) for t, c in lines]
        self.image_path = "test.png"

    @property
    def full_text(self):
        return "\n".join(line.text for line in self.lines)


class TestFieldParser:
    def test_parse_receipt_no(self):
        ocr = MockOCRResult([
            ("入库单", 0.98),
            ("单据编号: RK-20240315-001", 0.95),
            ("品名: 螺丝 M6x20", 0.92),
            ("数量: 500 个", 0.90),
        ])
        parsed = parse_ocr_result(ocr)
        assert parsed.receipt_no == "RK-20240315-001"
        assert parsed.receipt_type == "入库"

    def test_parse_product_name(self):
        ocr = MockOCRResult([
            ("品名: 轴承 6205-2RS", 0.95),
        ])
        parsed = parse_ocr_result(ocr)
        assert parsed.product_name == "轴承 6205-2RS"

    def test_parse_quantity(self):
        ocr = MockOCRResult([
            ("数量: 1000 件", 0.93),
        ])
        parsed = parse_ocr_result(ocr)
        assert parsed.quantity == 1000.0

    def test_parse_quantity_with_unit_suffix(self):
        ocr = MockOCRResult([
            ("500箱", 0.90),
        ])
        parsed = parse_ocr_result(ocr)
        assert parsed.quantity == 500.0

    def test_parse_chinese_date(self):
        ocr = MockOCRResult([
            ("日期: 2024年3月15日", 0.95),
        ])
        parsed = parse_ocr_result(ocr)
        assert parsed.date == "2024年3月15日"

    def test_parse_slash_date(self):
        ocr = MockOCRResult([
            ("日期: 2024/03/15", 0.95),
        ])
        parsed = parse_ocr_result(ocr)
        assert parsed.date == "2024/03/15"

    def test_parse_outbound(self):
        ocr = MockOCRResult([
            ("出库单", 0.98),
            ("编号: CK20240315002", 0.95),
        ])
        parsed = parse_ocr_result(ocr)
        assert parsed.receipt_type == "出库"

    def test_parse_full_receipt(self):
        ocr = MockOCRResult([
            ("入库单", 0.99),
            ("单据编号: RK-20240315-003", 0.95),
            ("品名: 密封圈 OR-25", 0.92),
            ("数量: 2000 个", 0.91),
            ("日期: 2024-03-15", 0.96),
            ("仓库: A区3号库", 0.88),
            ("供应商: 东莞精密五金有限公司", 0.90),
        ])
        parsed = parse_ocr_result(ocr)
        assert parsed.receipt_no == "RK-20240315-003"
        assert parsed.product_name == "密封圈 OR-25"
        assert parsed.quantity == 2000.0
        assert parsed.date == "2024-03-15"
        assert parsed.supplier is not None
        assert parsed.overall_confidence > 0.5

    def test_empty_ocr(self):
        ocr = MockOCRResult([])
        parsed = parse_ocr_result(ocr)
        assert parsed.receipt_no is None
        assert parsed.product_name is None
        assert parsed.quantity is None


class TestFuzzyMatch:
    def test_exact_match(self):
        result = fuzzy_match_product("螺丝 M6x20", ["螺丝 M6x20", "轴承 6205", "密封圈"])
        assert result == "螺丝 M6x20"

    def test_fuzzy_match(self):
        result = fuzzy_match_product("螺丝 M6×20", ["螺丝 M6x20", "轴承 6205"])
        assert result == "螺丝 M6x20"

    def test_no_match_below_threshold(self):
        result = fuzzy_match_product("完全不同", ["螺丝", "轴承"], threshold=70)
        assert result is None

    def test_best_match_selected(self):
        result = fuzzy_match_product("轴承6205", ["螺丝 M6", "轴承 6205-2RS", "密封圈"])
        assert result == "轴承 6205-2RS"
