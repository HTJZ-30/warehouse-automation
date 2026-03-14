"""Feature 2 端到端测试 (不启动 RPA，不需要 WMS)

跑通链路: 模拟图片 → 预处理 → OCR → 字段解析 → 校验
对比 OCR 解析结果与 ground truth
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.logger import get_logger
from feature2_receipt.image_preprocessor import preprocess_image
from feature2_receipt.ocr_engine import recognize
from feature2_receipt.field_parser import parse_ocr_result
from feature2_receipt.validator import validate_receipt

logger = get_logger("e2e_feature2")

# 生成时的 ground truth (seed 42+i)
GROUND_TRUTH = {
    "receipt_001.png": {
        "receipt_type": "入库", "receipt_no": "RK-20260311-115",
        "product_name": "螺丝 M6x20", "quantity": 2303, "unit": "个",
        "date": "2026-03-11", "supplier": "上海标准件制造厂", "warehouse": "A区2号库",
    },
    "receipt_002.png": {
        "receipt_type": "出库", "receipt_no": "CK-20260301-293",
        "product_name": "密封圈 OR-25", "quantity": 3839, "unit": "个",
        "date": "2026-03-01", "supplier": "深圳新材料科技有限公司", "warehouse": "B区1号库",
    },
    "receipt_003.png": {
        "receipt_type": "入库", "receipt_no": "RK-20260307-533",
        "product_name": "Bearing SKF-6208", "quantity": 1005, "unit": "pcs",
        "date": "2026-03-07", "supplier": "上海标准件制造厂", "warehouse": "C区3号库",
    },
    "receipt_004.png": {
        "receipt_type": "出库", "receipt_no": "CK-20260305-428",
        "product_name": "橡胶密封垫 50x70", "quantity": 2160, "unit": "片",
        "date": "2026-03-05", "supplier": "东莞精密五金有限公司", "warehouse": "A区2号库",
    },
    "receipt_005.png": {
        "receipt_type": "入库", "receipt_no": "RK-20260302-410",
        "product_name": "螺丝 M6x20", "quantity": 4871, "unit": "个",
        "date": "2026-03-02", "supplier": "Precision Parts Co., Ltd.", "warehouse": "A区1号库",
    },
    "receipt_006.png": {
        "receipt_type": "出库", "receipt_no": "CK-20260306-065",
        "product_name": "铜接头 1/2 inch", "quantity": 4585, "unit": "个",
        "date": "2026-03-06", "supplier": "深圳新材料科技有限公司", "warehouse": "A区1号库",
    },
}


def compare_field(parsed_val, truth_val, field_name: str) -> tuple[bool, str]:
    """比较单个字段，返回 (match, detail)"""
    if parsed_val is None:
        return False, f"未提取到"
    parsed_str = str(parsed_val).strip()
    truth_str = str(truth_val).strip()
    # 数值字段: 只比较数值
    if field_name == "quantity":
        try:
            return float(parsed_str) == float(truth_str), f"{parsed_str} vs {truth_str}"
        except ValueError:
            return False, f"无法比较: {parsed_str} vs {truth_str}"
    # 字符串字段: 去空格+大小写不敏感比较
    norm_parsed = parsed_str.replace(" ", "").lower()
    norm_truth = truth_str.replace(" ", "").lower()
    if norm_parsed == norm_truth or norm_truth in norm_parsed or norm_parsed in norm_truth:
        return True, f"OK"
    return False, f"'{parsed_str}' vs '{truth_str}'"


def run_e2e():
    receipts_dir = Path("tests/fixtures/receipts")
    images = sorted(receipts_dir.glob("receipt_*.png"))

    if not images:
        print("未找到测试图片，请先运行 tests/generate_mock_receipts.py")
        return

    results_log = []
    total_fields = 0
    matched_fields = 0

    print("=" * 70)
    print("Feature 2 端到端测试: OCR -> 字段解析 -> 校验")
    print("=" * 70)

    for img_path in images:
        gt = GROUND_TRUTH.get(img_path.name, {})
        if not gt:
            continue

        print(f"\n--- {img_path.name} ({gt['receipt_type']}单 {gt['receipt_no']}) ---")

        # 1. 预处理
        processed = preprocess_image(img_path)

        # 2. OCR (用原图，预处理图二值化后有时反而不利于 OCR)
        ocr_result = recognize(img_path, lang="ch")
        print(f"  OCR: {len(ocr_result.lines)} 行, 平均置信度 {ocr_result.avg_confidence:.1%}")

        # 3. 字段解析
        parsed = parse_ocr_result(ocr_result)

        # 4. 校验
        validation = validate_receipt(parsed, auto_pass_threshold=0.90, review_threshold=0.70)
        print(f"  校验: {validation.action.value} (置信度 {validation.confidence:.1%})")

        # 5. 对比 ground truth
        fields_to_check = ["receipt_type", "receipt_no", "product_name", "quantity", "date"]
        img_result = {"image": img_path.name, "fields": {}}

        for field in fields_to_check:
            parsed_val = getattr(parsed, field, None)
            truth_val = gt.get(field)
            match, detail = compare_field(parsed_val, truth_val, field)
            total_fields += 1
            if match:
                matched_fields += 1
                status = "PASS"
            else:
                status = "FAIL"
            print(f"  {field:15s}: {status:4s}  {detail}")
            img_result["fields"][field] = {"match": match, "parsed": str(parsed_val), "truth": str(truth_val)}

        results_log.append(img_result)

    # 汇总
    accuracy = matched_fields / total_fields * 100 if total_fields > 0 else 0
    print("\n" + "=" * 70)
    print(f"汇总: {matched_fields}/{total_fields} 字段匹配 ({accuracy:.1f}%)")
    print(f"测试图片: {len(results_log)}")
    print("=" * 70)

    # 保存详细结果
    output_file = Path("tests/e2e_feature2_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_log, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_file}")


if __name__ == "__main__":
    run_e2e()
