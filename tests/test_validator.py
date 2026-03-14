"""测试: validator 字段校验"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature2_receipt.validator import validate_receipt, ReviewAction


class MockParsedReceipt:
    def __init__(self, **kwargs):
        self.receipt_no = kwargs.get("receipt_no")
        self.receipt_type = kwargs.get("receipt_type")
        self.product_name = kwargs.get("product_name")
        self.quantity = kwargs.get("quantity")
        self.unit = kwargs.get("unit")
        self.date = kwargs.get("date")
        self.warehouse = kwargs.get("warehouse")
        self.supplier = kwargs.get("supplier")
        self.remark = kwargs.get("remark")
        self.raw_text = kwargs.get("raw_text", "")
        self.field_confidences = kwargs.get("field_confidences", {})

    @property
    def overall_confidence(self):
        if not self.field_confidences:
            return 0.0
        return sum(self.field_confidences.values()) / len(self.field_confidences)


class TestValidator:
    def test_auto_pass_high_confidence(self):
        parsed = MockParsedReceipt(
            receipt_no="RK-20240315-001",
            product_name="螺丝",
            quantity=500,
            field_confidences={"receipt_no": 0.95, "product_name": 0.92, "quantity": 0.96},
        )
        result = validate_receipt(parsed)
        assert result.action == ReviewAction.AUTO_PASS
        assert result.is_valid
        assert len(result.errors) == 0

    def test_manual_review_medium_confidence(self):
        parsed = MockParsedReceipt(
            receipt_no="RK-20240315-001",
            product_name="螺丝",
            quantity=500,
            field_confidences={"receipt_no": 0.80, "product_name": 0.75, "quantity": 0.78},
        )
        result = validate_receipt(parsed)
        assert result.action == ReviewAction.MANUAL_REVIEW
        assert result.needs_review

    def test_force_review_low_confidence(self):
        parsed = MockParsedReceipt(
            receipt_no="RK-20240315-001",
            product_name="螺丝",
            quantity=500,
            field_confidences={"receipt_no": 0.50, "product_name": 0.55, "quantity": 0.45},
        )
        result = validate_receipt(parsed)
        assert result.action == ReviewAction.FORCE_REVIEW

    def test_force_review_missing_receipt_no(self):
        parsed = MockParsedReceipt(
            receipt_no=None,
            product_name="螺丝",
            quantity=500,
            field_confidences={"product_name": 0.95, "quantity": 0.96},
        )
        result = validate_receipt(parsed)
        assert result.action == ReviewAction.FORCE_REVIEW
        assert any(e.field == "receipt_no" for e in result.errors)

    def test_force_review_missing_product_name(self):
        parsed = MockParsedReceipt(
            receipt_no="RK-001",
            product_name=None,
            quantity=500,
            field_confidences={"receipt_no": 0.95, "quantity": 0.96},
        )
        result = validate_receipt(parsed)
        assert any(e.field == "product_name" for e in result.errors)

    def test_force_review_missing_quantity(self):
        parsed = MockParsedReceipt(
            receipt_no="RK-001",
            product_name="螺丝",
            quantity=None,
            field_confidences={"receipt_no": 0.95, "product_name": 0.92},
        )
        result = validate_receipt(parsed)
        assert any(e.field == "quantity" for e in result.errors)

    def test_negative_quantity_error(self):
        parsed = MockParsedReceipt(
            receipt_no="RK-001",
            product_name="螺丝",
            quantity=-10,
            field_confidences={"receipt_no": 0.95, "product_name": 0.92, "quantity": 0.90},
        )
        result = validate_receipt(parsed)
        assert any(e.field == "quantity" for e in result.errors)

    def test_warning_on_abnormal_receipt_no(self):
        parsed = MockParsedReceipt(
            receipt_no="abc xyz!!",
            product_name="螺丝",
            quantity=500,
            field_confidences={"receipt_no": 0.95, "product_name": 0.92, "quantity": 0.96},
        )
        result = validate_receipt(parsed)
        assert any(w.field == "receipt_no" for w in result.warnings)

    def test_warning_on_bad_date_format(self):
        parsed = MockParsedReceipt(
            receipt_no="RK20240315001",
            product_name="螺丝",
            quantity=500,
            date="15/03/2024",  # wrong format
            field_confidences={"receipt_no": 0.95, "product_name": 0.92, "quantity": 0.96, "date": 0.90},
        )
        result = validate_receipt(parsed)
        assert any(w.field == "date" for w in result.warnings)

    def test_all_fields_empty(self):
        parsed = MockParsedReceipt(field_confidences={})
        result = validate_receipt(parsed)
        assert result.action == ReviewAction.FORCE_REVIEW
        assert len(result.errors) >= 3
