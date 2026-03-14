"""测试: data_source Excel 数据源"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature1_inventory.data_source import ExcelDataSource, InventoryRecord


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestExcelDataSource:
    def test_read_inventory_from_fixture(self):
        """测试从 fixture Excel 读取库存"""
        excel_path = FIXTURES_DIR / "test_inventory.xlsx"
        if not excel_path.exists():
            pytest.skip("测试 fixture 不存在，请先创建 tests/fixtures/test_inventory.xlsx")

        ds = ExcelDataSource(str(excel_path), sheet_name="库存")
        records = ds.read_inventory()
        assert len(records) > 0
        assert isinstance(records[0], InventoryRecord)
        assert records[0].sku != ""

    def test_file_not_found(self):
        ds = ExcelDataSource("nonexistent.xlsx")
        with pytest.raises(FileNotFoundError):
            ds.read_inventory()

    def test_column_mapping(self):
        """验证中文列名映射"""
        mapping = ExcelDataSource.COLUMN_MAP
        assert mapping["SKU"] == "sku"
        assert mapping["品名"] == "name"
        assert mapping["库存"] == "current_stock"
        assert mapping["当前库存"] == "current_stock"

    def test_inventory_record_repr(self):
        record = InventoryRecord("SKU-001", "螺丝", 100.0)
        assert "SKU-001" in repr(record)
        assert "100" in repr(record)
