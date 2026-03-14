"""测试 Excel 台账录入"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature2_receipt.rpa_engine import RPAEngine
from shared.config_loader import load_wms_mapping


def main():
    print("=" * 60)
    print("测试 Excel 台账录入")
    print("=" * 60)

    wms_config = load_wms_mapping()
    rpa = RPAEngine(wms_config)

    # 模拟 3 张单据录入
    test_receipts = [
        {
            "receipt_no": "RK-20260311-115",
            "receipt_type": "入库",
            "product_name": "螺丝 M6x20",
            "quantity": "2303",
            "date": "2026-03-11",
            "warehouse": "A区2号库",
            "supplier": "上海标准件制造厂",
            "remark": "",
        },
        {
            "receipt_no": "CK-20260301-293",
            "receipt_type": "出库",
            "product_name": "密封圈 OR-25",
            "quantity": "3839",
            "date": "2026-03-01",
            "warehouse": "B区1号库",
            "supplier": "",
            "remark": "紧急出库",
        },
        {
            "receipt_no": "RK-20260307-533",
            "receipt_type": "入库",
            "product_name": "Bearing SKF-6208",
            "quantity": "1005",
            "date": "2026-03-07",
            "warehouse": "C区3号库",
            "supplier": "进口轴承代理商",
            "remark": "",
        },
    ]

    for i, data in enumerate(test_receipts, 1):
        print(f"\n[{i}/3] 录入: {data['receipt_no']} ({data['product_name']})")
        success = rpa.entry_receipt(data, source_image=f"receipt_00{i}.png")
        print(f"  结果: {'成功' if success else '失败'}")

    # 验证台账内容
    print(f"\n--- 台账验证 ---")
    print(f"文件: {rpa.get_ledger_path()}")

    entries = rpa.get_all_entries()
    print(f"记录数: {len(entries)}")
    for entry in entries:
        print(f"  #{entry['序号']}: {entry['单据编号']} | {entry['品名']} | 数量{entry['数量']} | {entry['录入时间']}")

    print(f"\n台账文件大小: {rpa.get_ledger_path().stat().st_size:,} bytes")
    print("=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
