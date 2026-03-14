"""生成模拟出入库单据图片 — 用于测试 OCR 流水线"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent

# 字体
FONT_PATH_BOLD = "C:/Windows/Fonts/simhei.ttf"    # 黑体 (标题)
FONT_PATH_REGULAR = "C:/Windows/Fonts/simsun.ttc"  # 宋体 (正文)
FONT_PATH_EN = "C:/Windows/Fonts/consola.ttf"      # 等宽英文


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ── 模拟数据 ───────────────────────────────────────────────────

PRODUCTS = [
    ("螺丝 M6x20", "个", "SKU-001"),
    ("轴承 6205-2RS", "个", "SKU-002"),
    ("密封圈 OR-25", "个", "SKU-003"),
    ("弹簧垫圈 M8", "个", "SKU-004"),
    ("六角螺母 M10", "个", "SKU-005"),
    ("不锈钢管 DN25", "米", "SKU-006"),
    ("铜接头 1/2 inch", "个", "SKU-007"),
    ("橡胶密封垫 50x70", "片", "SKU-008"),
    ("Bearing SKF-6208", "pcs", "SKU-009"),
    ("O-Ring NBR-30", "pcs", "SKU-010"),
]

SUPPLIERS = [
    "东莞精密五金有限公司",
    "上海标准件制造厂",
    "深圳新材料科技有限公司",
    "Precision Parts Co., Ltd.",
]

WAREHOUSES = ["A区1号库", "A区2号库", "B区1号库", "C区3号库"]


def generate_receipt_image(
    output_path: Path,
    receipt_type: str = "入库",
    seed: int = None,
) -> dict:
    """生成一张模拟单据图片

    Args:
        output_path: 输出路径
        receipt_type: "入库" 或 "出库"
        seed: 随机种子 (可复现)

    Returns:
        dict 包含所有字段的真值 (ground truth)
    """
    if seed is not None:
        random.seed(seed)

    # 生成随机数据
    prefix = "RK" if receipt_type == "入库" else "CK"
    date = datetime(2026, 3, random.randint(1, 14))
    receipt_no = f"{prefix}-{date.strftime('%Y%m%d')}-{random.randint(1, 999):03d}"
    product_name, unit, sku = random.choice(PRODUCTS)
    quantity = random.randint(50, 5000)
    supplier = random.choice(SUPPLIERS)
    warehouse = random.choice(WAREHOUSES)
    remark = random.choice(["正常到货", "急件补货", "Quality OK", "抽检合格", ""])

    ground_truth = {
        "receipt_type": receipt_type,
        "receipt_no": receipt_no,
        "product_name": product_name,
        "quantity": quantity,
        "unit": unit,
        "date": date.strftime("%Y-%m-%d"),
        "supplier": supplier,
        "warehouse": warehouse,
        "remark": remark,
    }

    # 画布
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    title_font = _font(FONT_PATH_BOLD, 32)
    label_font = _font(FONT_PATH_BOLD, 18)
    value_font = _font(FONT_PATH_REGULAR, 18)
    small_font = _font(FONT_PATH_REGULAR, 14)

    # 外框
    draw.rectangle([20, 20, width - 20, height - 20], outline="#000000", width=2)

    # 标题
    title = f"{receipt_type}单"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) / 2, 35), title, fill="#000000", font=title_font)

    # 副标题
    subtitle = "WAREHOUSE RECEIPT" if receipt_type == "入库" else "WAREHOUSE SHIPMENT"
    bbox2 = draw.textbbox((0, 0), subtitle, font=small_font)
    sw = bbox2[2] - bbox2[0]
    draw.text(((width - sw) / 2, 75), subtitle, fill="#666666", font=small_font)

    # 分隔线
    draw.line([40, 100, width - 40, 100], fill="#000000", width=1)

    # 字段区域
    y = 120
    line_height = 45
    left_x = 60
    val_x = 200

    fields = [
        ("单据编号:", receipt_no),
        ("日期 Date:", date.strftime("%Y-%m-%d")),
        ("品名 Product:", product_name),
        (f"数量 Qty:", f"{quantity} {unit}"),
        ("供应商 Supplier:", supplier),
        ("仓库 Warehouse:", warehouse),
    ]

    for label, value in fields:
        draw.text((left_x, y), label, fill="#333333", font=label_font)
        draw.text((val_x, y), str(value), fill="#000000", font=value_font)
        # 下划线
        draw.line([val_x, y + 28, width - 60, y + 28], fill="#CCCCCC", width=1)
        y += line_height

    # 备注
    if remark:
        y += 10
        draw.text((left_x, y), "备注 Remark:", fill="#333333", font=label_font)
        draw.text((val_x, y), remark, fill="#000000", font=value_font)
        y += line_height

    # 底部
    draw.line([40, height - 80, width - 40, height - 80], fill="#000000", width=1)
    draw.text((left_x, height - 65), "制单人:________", fill="#333333", font=small_font)
    draw.text((350, height - 65), "审核人:________", fill="#333333", font=small_font)
    draw.text((left_x, height - 40), f"打印时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill="#999999", font=small_font)

    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    return ground_truth


def generate_test_set(output_dir: Path, count: int = 6) -> list[dict]:
    """生成一组测试单据图片

    Returns:
        list of {path, ground_truth}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for i in range(count):
        receipt_type = "入库" if i % 2 == 0 else "出库"
        filename = f"receipt_{i+1:03d}.png"
        filepath = output_dir / filename
        gt = generate_receipt_image(filepath, receipt_type=receipt_type, seed=42 + i)
        results.append({"path": str(filepath), "ground_truth": gt})
        print(f"  [{i+1}/{count}] {filename} — {gt['receipt_type']}单 {gt['receipt_no']} {gt['product_name']}")

    return results


if __name__ == "__main__":
    print("生成模拟单据图片...")
    fixtures_dir = ROOT / "tests" / "fixtures" / "receipts"
    results = generate_test_set(fixtures_dir, count=6)

    # 也复制一份到监控文件夹供 Feature 2 使用
    watch_dir = ROOT / "data" / "receipts"
    print(f"\n复制到监控文件夹: {watch_dir}")
    import shutil
    for r in results[:2]:  # 只放 2 张到监控文件夹
        src = Path(r["path"])
        dst = watch_dir / src.name
        shutil.copy2(src, dst)
        print(f"  -> {dst.name}")

    print(f"\n共生成 {len(results)} 张模拟单据")
    print("真值数据:")
    for r in results:
        gt = r["ground_truth"]
        print(f"  {Path(r['path']).name}: {gt['receipt_no']} | {gt['product_name']} | {gt['quantity']} {gt['unit']}")
