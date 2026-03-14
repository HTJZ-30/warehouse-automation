"""字段校验 + 置信度路由模块"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from shared.logger import get_logger

logger = get_logger("validator")


class ReviewAction(Enum):
    """校验结果的处理动作"""
    AUTO_PASS = "auto_pass"       # ≥90% 自动通过
    MANUAL_REVIEW = "review"      # 70-90% 人工复核
    FORCE_REVIEW = "force_review" # <70% 强制复核


@dataclass
class ValidationError:
    """单个字段的校验错误"""
    field: str
    message: str
    severity: str = "error"  # "error" | "warning"


@dataclass
class ValidationResult:
    """校验汇总结果"""
    action: ReviewAction
    errors: list[ValidationError]
    warnings: list[ValidationError]
    confidence: float
    is_valid: bool

    @property
    def needs_review(self) -> bool:
        return self.action in (ReviewAction.MANUAL_REVIEW, ReviewAction.FORCE_REVIEW)


def validate_receipt(
    parsed,
    auto_pass_threshold: float = 0.90,
    review_threshold: float = 0.70,
) -> ValidationResult:
    """校验解析后的单据字段

    校验规则:
    1. 必填字段非空检查
    2. 单据编号格式校验
    3. 数量正数检查
    4. 日期格式校验
    5. 置信度路由

    Args:
        parsed: ParsedReceipt 对象
        auto_pass_threshold: 自动通过置信度阈值
        review_threshold: 人工复核置信度阈值

    Returns:
        ValidationResult
    """
    errors = []
    warnings = []

    # 1. 必填字段检查
    if not parsed.receipt_no:
        errors.append(ValidationError("receipt_no", "单据编号为空"))
    if not parsed.product_name:
        errors.append(ValidationError("product_name", "品名为空"))
    if parsed.quantity is None:
        errors.append(ValidationError("quantity", "数量为空"))

    # 2. 单据编号格式
    if parsed.receipt_no and not _is_valid_receipt_no(parsed.receipt_no):
        warnings.append(ValidationError(
            "receipt_no",
            f"单据编号格式异常: {parsed.receipt_no}",
            severity="warning",
        ))

    # 3. 数量合法性
    if parsed.quantity is not None:
        if parsed.quantity <= 0:
            errors.append(ValidationError("quantity", f"数量必须为正数，当前: {parsed.quantity}"))
        if parsed.quantity != int(parsed.quantity) and parsed.quantity > 10000:
            warnings.append(ValidationError(
                "quantity",
                f"数量疑似 OCR 误读: {parsed.quantity}",
                severity="warning",
            ))

    # 4. 日期格式
    if parsed.date and not _is_valid_date(parsed.date):
        warnings.append(ValidationError(
            "date",
            f"日期格式异常: {parsed.date}",
            severity="warning",
        ))

    # 5. 置信度路由
    confidence = parsed.overall_confidence
    if errors:
        action = ReviewAction.FORCE_REVIEW
        is_valid = False
    elif confidence >= auto_pass_threshold and not warnings:
        action = ReviewAction.AUTO_PASS
        is_valid = True
    elif confidence >= review_threshold:
        action = ReviewAction.MANUAL_REVIEW
        is_valid = True
    else:
        action = ReviewAction.FORCE_REVIEW
        is_valid = len(errors) == 0

    result = ValidationResult(
        action=action,
        errors=errors,
        warnings=warnings,
        confidence=confidence,
        is_valid=is_valid,
    )

    logger.info(
        "校验结果: %s (置信度 %.2f%%, %d 错误, %d 警告)",
        action.value, confidence * 100, len(errors), len(warnings),
        extra={"confidence": confidence, "action": action.value},
    )
    return result


def _is_valid_receipt_no(receipt_no: str) -> bool:
    """校验单据编号格式"""
    patterns = [
        r'^[A-Z]{2,4}[\-]?\d{6,}[\-]?\d*$',  # RK-20240101-001
        r'^\d{8,}$',                            # 纯数字
        r'^[A-Za-z]+\d+$',                      # 字母+数字
    ]
    return any(re.match(p, receipt_no) for p in patterns)


def _is_valid_date(date_str: str) -> bool:
    """校验日期格式"""
    patterns = [
        r'^\d{4}[\-/]\d{1,2}[\-/]\d{1,2}$',
        r'^\d{4}年\d{1,2}月\d{1,2}日$',
    ]
    return any(re.match(p, date_str) for p in patterns)
