"""测试 Tkinter 复核界面

使用模拟数据启动复核窗口，无需 WMS 和 RPA。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature2_receipt.ocr_engine import recognize
from feature2_receipt.field_parser import parse_ocr_result
from feature2_receipt.validator import validate_receipt, ReviewAction
from feature2_receipt.review_ui import open_review


def main():
    # 用一张模拟单据
    img_path = Path("tests/fixtures/receipts/receipt_001.png")
    if not img_path.exists():
        print(f"图片不存在: {img_path}")
        return

    print("1. OCR 识别...")
    ocr_result = recognize(img_path, lang="ch")
    print(f"   {len(ocr_result.lines)} 行, 置信度 {ocr_result.avg_confidence:.1%}")

    print("2. 字段解析...")
    parsed = parse_ocr_result(ocr_result)
    print(f"   单号={parsed.receipt_no}, 品名={parsed.product_name}, 数量={parsed.quantity}")

    print("3. 校验...")
    # 强制降低阈值，让它进入复核流程
    validation = validate_receipt(parsed, auto_pass_threshold=0.999, review_threshold=0.70)
    print(f"   动作={validation.action.value}, 置信度={validation.confidence:.1%}")

    print("4. 打开 Tkinter 复核界面...")
    print("   (请在弹出窗口中操作: 可修改字段，然后点 确认录入/驳回/跳过)")
    result = open_review(img_path, parsed, validation)

    if result:
        print("\n=== 复核结果: 已确认 ===")
        for k, v in result.items():
            print(f"   {k}: {v}")
    else:
        print("\n=== 复核结果: 驳回/跳过 ===")


if __name__ == "__main__":
    main()
