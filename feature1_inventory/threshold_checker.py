"""阈值比较 + 趋势预警模块"""

from dataclasses import dataclass, field

from shared.config_loader import ThresholdsConfig, SKUThreshold
from shared.logger import get_logger

logger = get_logger("threshold_checker")


@dataclass
class AlertItem:
    """一条低库存告警"""
    sku: str
    name: str
    current_stock: float
    safety_stock: int
    warning_threshold: int
    reorder_quantity: int
    alert_level: str  # "critical" | "warning"
    deficit: float = 0.0  # 低于安全库存的差额

    @property
    def is_critical(self) -> bool:
        return self.alert_level == "critical"


@dataclass
class ThresholdCheckResult:
    """阈值检查汇总结果"""
    total_skus: int = 0
    critical_alerts: list[AlertItem] = field(default_factory=list)
    warning_alerts: list[AlertItem] = field(default_factory=list)

    @property
    def all_alerts(self) -> list[AlertItem]:
        return self.critical_alerts + self.warning_alerts

    @property
    def has_alerts(self) -> bool:
        return len(self.critical_alerts) > 0 or len(self.warning_alerts) > 0


def _get_threshold(sku: str, config: ThresholdsConfig) -> SKUThreshold:
    """获取 SKU 阈值 (优先用 override，否则用默认值)"""
    if sku in config.overrides:
        return config.overrides[sku]
    return SKUThreshold(
        name="",
        safety_stock=config.defaults.safety_stock,
        warning_threshold=config.defaults.warning_threshold,
        reorder_quantity=config.defaults.reorder_quantity,
    )


def check_thresholds(inventory_records, thresholds_config: ThresholdsConfig) -> ThresholdCheckResult:
    """对库存记录逐一检查阈值

    Args:
        inventory_records: InventoryRecord 列表
        thresholds_config: 阈值配置

    Returns:
        ThresholdCheckResult 汇总结果
    """
    result = ThresholdCheckResult(total_skus=len(inventory_records))

    for record in inventory_records:
        threshold = _get_threshold(record.sku, thresholds_config)

        if record.current_stock <= threshold.safety_stock:
            alert = AlertItem(
                sku=record.sku,
                name=record.name,
                current_stock=record.current_stock,
                safety_stock=threshold.safety_stock,
                warning_threshold=threshold.warning_threshold,
                reorder_quantity=threshold.reorder_quantity,
                alert_level="critical",
                deficit=threshold.safety_stock - record.current_stock,
            )
            result.critical_alerts.append(alert)
            logger.warning(
                "严重: %s (%s) 库存 %.0f <= 安全库存 %d",
                record.sku, record.name, record.current_stock, threshold.safety_stock,
                extra={"sku": record.sku, "action": "critical_alert"},
            )

        elif record.current_stock <= threshold.warning_threshold:
            alert = AlertItem(
                sku=record.sku,
                name=record.name,
                current_stock=record.current_stock,
                safety_stock=threshold.safety_stock,
                warning_threshold=threshold.warning_threshold,
                reorder_quantity=threshold.reorder_quantity,
                alert_level="warning",
                deficit=0,
            )
            result.warning_alerts.append(alert)
            logger.info(
                "预警: %s (%s) 库存 %.0f <= 预警线 %d",
                record.sku, record.name, record.current_stock, threshold.warning_threshold,
                extra={"sku": record.sku, "action": "warning_alert"},
            )

    logger.info(
        "检查完成: %d SKU, %d 严重, %d 预警",
        result.total_skus, len(result.critical_alerts), len(result.warning_alerts),
    )
    return result
