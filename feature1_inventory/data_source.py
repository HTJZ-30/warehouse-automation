"""库存数据源读取模块 — 支持 Excel 和 SQL 数据库"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd

from shared.logger import get_logger

logger = get_logger("data_source")


class InventoryRecord:
    """单条库存记录"""

    __slots__ = ("sku", "name", "current_stock", "unit", "warehouse", "last_updated")

    def __init__(self, sku: str, name: str, current_stock: float,
                 unit: str = "个", warehouse: str = "", last_updated: str = ""):
        self.sku = sku
        self.name = name
        self.current_stock = current_stock
        self.unit = unit
        self.warehouse = warehouse
        self.last_updated = last_updated

    def __repr__(self):
        return f"<Inventory {self.sku} '{self.name}' stock={self.current_stock}>"


class DataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def read_inventory(self) -> list[InventoryRecord]:
        ...


class ExcelDataSource(DataSource):
    """从 Excel 文件读取库存"""

    # 支持的列名映射 (中文 -> 英文字段名)
    COLUMN_MAP = {
        "SKU": "sku", "sku": "sku", "SKU编号": "sku", "物料编号": "sku",
        "品名": "name", "名称": "name", "物料名称": "name", "product_name": "name",
        "库存": "current_stock", "当前库存": "current_stock", "数量": "current_stock",
        "stock": "current_stock", "quantity": "current_stock",
        "单位": "unit", "unit": "unit",
        "仓库": "warehouse", "warehouse": "warehouse",
        "更新时间": "last_updated", "日期": "last_updated",
    }

    def __init__(self, file_path: str, sheet_name: str = "库存"):
        self.file_path = Path(file_path)
        self.sheet_name = sheet_name

    def read_inventory(self) -> list[InventoryRecord]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel 文件不存在: {self.file_path}")

        logger.info("读取 Excel 库存: %s [%s]", self.file_path, self.sheet_name)
        df = pd.read_excel(self.file_path, sheet_name=self.sheet_name, engine="openpyxl")

        # 自动映射列名
        rename = {}
        for col in df.columns:
            col_str = str(col).strip()
            if col_str in self.COLUMN_MAP:
                rename[col] = self.COLUMN_MAP[col_str]
        df = df.rename(columns=rename)

        required = {"sku", "name", "current_stock"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Excel 缺少必要列: {missing}. 当前列: {list(df.columns)}")

        records = []
        for _, row in df.iterrows():
            records.append(InventoryRecord(
                sku=str(row["sku"]).strip(),
                name=str(row["name"]).strip(),
                current_stock=float(row["current_stock"]),
                unit=str(row.get("unit", "个")).strip(),
                warehouse=str(row.get("warehouse", "")).strip(),
                last_updated=str(row.get("last_updated", "")).strip(),
            ))

        logger.info("读取到 %d 条库存记录", len(records))
        return records


class SQLDataSource(DataSource):
    """从 SQL 数据库读取库存"""

    def __init__(self, connection_string: str, table: str = "inventory",
                 query: Optional[str] = None):
        self.connection_string = connection_string
        self.table = table
        self.query = query

    def read_inventory(self) -> list[InventoryRecord]:
        import pyodbc

        logger.info("连接 SQL 数据库读取库存")
        sql = self.query or f"SELECT * FROM {self.table}"

        conn = pyodbc.connect(self.connection_string)
        try:
            df = pd.read_sql(sql, conn)
        finally:
            conn.close()

        # 尝试标准化列名 (同 Excel 的映射逻辑)
        rename = {}
        for col in df.columns:
            col_lower = str(col).strip().lower()
            mapping = {k.lower(): v for k, v in ExcelDataSource.COLUMN_MAP.items()}
            if col_lower in mapping:
                rename[col] = mapping[col_lower]
        df = df.rename(columns=rename)

        records = []
        for _, row in df.iterrows():
            records.append(InventoryRecord(
                sku=str(row.get("sku", "")).strip(),
                name=str(row.get("name", "")).strip(),
                current_stock=float(row.get("current_stock", 0)),
                unit=str(row.get("unit", "个")).strip(),
                warehouse=str(row.get("warehouse", "")).strip(),
                last_updated=str(row.get("last_updated", "")).strip(),
            ))

        logger.info("从 SQL 读取到 %d 条库存记录", len(records))
        return records


def create_data_source(settings) -> DataSource:
    """工厂函数：根据配置创建数据源"""
    if settings.feature1.data_source_type == "excel":
        return ExcelDataSource(
            file_path=settings.feature1.excel_path,
            sheet_name=settings.feature1.excel_sheet,
        )
    elif settings.feature1.data_source_type == "sql":
        from shared.crypto import decrypt_value
        from shared.config_loader import load_suppliers

        suppliers_cfg = load_suppliers()
        sql_cfg = suppliers_cfg.sql or {}
        password = decrypt_value(sql_cfg.get("password_encrypted", ""))
        username = sql_cfg.get("username", "sa")

        conn_str = (
            f"DRIVER={{{settings.feature1.sql.driver}}};"
            f"SERVER={settings.feature1.sql.server};"
            f"DATABASE={settings.feature1.sql.database};"
            f"UID={username};PWD={password}"
        )
        return SQLDataSource(
            connection_string=conn_str,
            table=settings.feature1.sql.table,
        )
    else:
        raise ValueError(f"不支持的数据源类型: {settings.feature1.data_source_type}")
