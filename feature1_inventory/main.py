"""Feature 1 入口: 低库存预警与自动询价"""

import asyncio
import sys
from pathlib import Path

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.audit import AuditTrail
from shared.config_loader import load_settings, load_suppliers, load_thresholds
from shared.logger import get_logger

from feature1_inventory.data_source import create_data_source
from feature1_inventory.threshold_checker import check_thresholds
from feature1_inventory.browser_scraper import scrape_1688
from feature1_inventory.report_generator import generate_comparison_report
from feature1_inventory.notifier import notify

logger = get_logger("feature1_main")


def run():
    """Feature 1 主流程

    流程:
    1. 加载配置
    2. 读取库存数据
    3. 阈值检查
    4. 对低库存 SKU 抓取供应商报价
    5. 生成比价报表
    6. 发送通知
    """
    logger.info("=" * 60)
    logger.info("Feature 1: 低库存预警与自动询价 — 开始运行")
    logger.info("=" * 60)

    # 1. 加载配置
    settings = load_settings()
    thresholds = load_thresholds()
    suppliers = load_suppliers()
    audit = AuditTrail(settings.audit.db_path)

    audit.log("feature1_inventory", "run_started")

    try:
        # 2. 读取库存数据
        logger.info("步骤 1/5: 读取库存数据")
        data_source = create_data_source(settings)
        inventory = data_source.read_inventory()
        audit.log("feature1_inventory", "read_inventory", details={"count": len(inventory)})

        # 3. 阈值检查
        logger.info("步骤 2/5: 检查库存阈值")
        alert_result = check_thresholds(inventory, thresholds)
        audit.log(
            "feature1_inventory", "check_thresholds",
            details={
                "total": alert_result.total_skus,
                "critical": len(alert_result.critical_alerts),
                "warning": len(alert_result.warning_alerts),
            },
        )

        if not alert_result.has_alerts:
            logger.info("所有 SKU 库存正常，无需告警")
            audit.log("feature1_inventory", "run_completed", details={"result": "no_alerts"})
            return

        logger.info(
            "发现 %d 条告警 (%d 严重, %d 预警)",
            len(alert_result.all_alerts),
            len(alert_result.critical_alerts),
            len(alert_result.warning_alerts),
        )

        # 4. 从 1688 公开平台抓取报价
        logger.info("步骤 3/5: 从 1688 抓取供应商报价")
        quotes = asyncio.run(scrape_1688(
            alert_items=alert_result.all_alerts,
            max_concurrent=settings.feature1.max_concurrent_scrapers,
        ))
        audit.log(
            "feature1_inventory", "scrape_prices",
            details={"skus_queried": len(quotes)},
        )

        # 5. 生成比价报表
        logger.info("步骤 4/5: 生成比价报表")
        report_path = generate_comparison_report(
            alert_items=alert_result.all_alerts,
            quotes=quotes,
            output_dir=settings.feature1.report_output_dir,
        )
        audit.log(
            "feature1_inventory", "generate_report",
            details={"path": str(report_path)},
        )

        # 6. 发送通知
        logger.info("步骤 5/5: 发送通知")
        notify(settings, suppliers, alert_result, report_path)
        audit.log("feature1_inventory", "notify_sent")

        logger.info("Feature 1 运行完成")
        audit.log("feature1_inventory", "run_completed", details={"result": "success"})

    except Exception as e:
        logger.exception("Feature 1 运行失败: %s", e)
        audit.log("feature1_inventory", "run_failed", status="failure", details={"error": str(e)})
        raise


if __name__ == "__main__":
    run()
