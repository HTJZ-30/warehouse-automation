"""测试: threshold_checker 阈值检查"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature1_inventory.data_source import InventoryRecord
from feature1_inventory.threshold_checker import check_thresholds
from shared.config_loader import ThresholdsConfig, ThresholdDefault, SKUThreshold, TrendAlert


def _make_config(safety=100, warning=150, reorder=500, overrides=None):
    return ThresholdsConfig(
        defaults=ThresholdDefault(
            safety_stock=safety,
            warning_threshold=warning,
            reorder_quantity=reorder,
        ),
        overrides=overrides or {},
        trend_alert=TrendAlert(enabled=False),
    )


def _make_record(sku, name, stock):
    return InventoryRecord(sku=sku, name=name, current_stock=stock)


class TestThresholdChecker:
    def test_no_alerts_when_stock_sufficient(self):
        records = [_make_record("SKU-001", "螺丝", 200)]
        config = _make_config(safety=100, warning=150)
        result = check_thresholds(records, config)
        assert not result.has_alerts
        assert len(result.critical_alerts) == 0
        assert len(result.warning_alerts) == 0

    def test_critical_alert_below_safety_stock(self):
        records = [_make_record("SKU-001", "螺丝", 50)]
        config = _make_config(safety=100, warning=150)
        result = check_thresholds(records, config)
        assert result.has_alerts
        assert len(result.critical_alerts) == 1
        assert result.critical_alerts[0].alert_level == "critical"
        assert result.critical_alerts[0].deficit == 50

    def test_warning_alert_below_threshold(self):
        records = [_make_record("SKU-001", "螺丝", 120)]
        config = _make_config(safety=100, warning=150)
        result = check_thresholds(records, config)
        assert result.has_alerts
        assert len(result.warning_alerts) == 1
        assert result.warning_alerts[0].alert_level == "warning"

    def test_exact_safety_stock_is_critical(self):
        records = [_make_record("SKU-001", "螺丝", 100)]
        config = _make_config(safety=100, warning=150)
        result = check_thresholds(records, config)
        assert len(result.critical_alerts) == 1

    def test_exact_warning_threshold_is_warning(self):
        records = [_make_record("SKU-001", "螺丝", 150)]
        config = _make_config(safety=100, warning=150)
        result = check_thresholds(records, config)
        assert len(result.warning_alerts) == 1

    def test_override_thresholds(self):
        records = [_make_record("SKU-001", "特殊件", 180)]
        config = _make_config(
            safety=100, warning=150,
            overrides={
                "SKU-001": SKUThreshold(name="特殊件", safety_stock=200, warning_threshold=300, reorder_quantity=1000)
            },
        )
        result = check_thresholds(records, config)
        assert len(result.critical_alerts) == 1
        assert result.critical_alerts[0].safety_stock == 200

    def test_multiple_skus_mixed_alerts(self):
        records = [
            _make_record("SKU-001", "螺丝", 50),   # critical
            _make_record("SKU-002", "轴承", 120),   # warning
            _make_record("SKU-003", "密封圈", 500), # ok
        ]
        config = _make_config(safety=100, warning=150)
        result = check_thresholds(records, config)
        assert result.total_skus == 3
        assert len(result.critical_alerts) == 1
        assert len(result.warning_alerts) == 1

    def test_zero_stock_is_critical(self):
        records = [_make_record("SKU-001", "螺丝", 0)]
        config = _make_config(safety=100, warning=150)
        result = check_thresholds(records, config)
        assert len(result.critical_alerts) == 1
        assert result.critical_alerts[0].deficit == 100

    def test_empty_inventory(self):
        result = check_thresholds([], _make_config())
        assert result.total_skus == 0
        assert not result.has_alerts
