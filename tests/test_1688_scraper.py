"""测试 1688 公开平台抓价"""

import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@dataclass
class MockAlertItem:
    sku: str
    name: str
    current_stock: int = 0
    threshold: int = 0
    level: str = "critical"


def main():
    from feature1_inventory.browser_scraper import scrape_1688

    # 用真实产品名称测试
    items = [
        MockAlertItem(sku="SKU-001", name="螺丝 M6x20"),
        MockAlertItem(sku="SKU-002", name="轴承 6205"),
    ]

    print("=" * 60)
    print("测试 1688 公开平台抓价")
    print("=" * 60)

    results = asyncio.run(scrape_1688(items, max_concurrent=2))

    for sku, quotes in results.items():
        print(f"\n--- {sku} ---")
        for q in quotes:
            if q.success:
                print(f"  {q.supplier_name}: CNY {q.unit_price:.2f}, {q.delivery_days or '?'}天交期")
            else:
                print(f"  {q.supplier_name}: 错误 - {q.error}")

    # 统计
    total_quotes = sum(len(qs) for qs in results.values())
    success_quotes = sum(1 for qs in results.values() for q in qs if q.success)
    print(f"\n总计: {total_quotes} 条报价, {success_quotes} 条成功")


if __name__ == "__main__":
    main()
