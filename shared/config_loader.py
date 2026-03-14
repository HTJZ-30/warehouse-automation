"""YAML 配置加载 + Pydantic 校验"""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


# ── Pydantic 配置模型 ──────────────────────────────────────────

class SQLConfig(BaseModel):
    driver: str = "ODBC Driver 17 for SQL Server"
    server: str = "localhost"
    database: str = "warehouse"
    table: str = "inventory"


class Feature1Config(BaseModel):
    schedule_cron: str = "0 2 * * *"
    data_source_type: str = "excel"
    excel_path: str = "data/inventory.xlsx"
    excel_sheet: str = "库存"
    sql: SQLConfig = SQLConfig()
    report_output_dir: str = "output/reports/"
    max_concurrent_scrapers: int = 3


class Feature2Config(BaseModel):
    watch_folder: str = "data/receipts/"
    processed_folder: str = "data/receipts_done/"
    failed_folder: str = "data/receipts_failed/"
    ocr_lang: str = "ch"
    confidence_auto_pass: float = 0.90
    confidence_review: float = 0.70
    rpa_delay_between_fields: float = 0.3


class EmailConfig(BaseModel):
    smtp_server: str = "smtp.example.com"
    smtp_port: int = 587
    use_tls: bool = True
    sender: str = ""
    recipients: list[str] = []


class WebhookConfig(BaseModel):
    enabled: bool = False
    type: str = "dingtalk"
    url: str = ""


class AuditConfig(BaseModel):
    db_path: str = "data/audit.db"


class AppConfig(BaseModel):
    name: str = "仓库自动化系统"
    version: str = "1.0.0"
    log_level: str = "INFO"
    log_dir: str = "logs/"


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    feature1: Feature1Config = Feature1Config()
    feature2: Feature2Config = Feature2Config()
    email: EmailConfig = EmailConfig()
    webhook: WebhookConfig = WebhookConfig()
    audit: AuditConfig = AuditConfig()


# ── Threshold 配置模型 ─────────────────────────────────────────

class ThresholdDefault(BaseModel):
    safety_stock: int = 100
    warning_threshold: int = 150
    reorder_quantity: int = 500


class SKUThreshold(BaseModel):
    name: str = ""
    safety_stock: int = 100
    warning_threshold: int = 150
    reorder_quantity: int = 500


class TrendAlert(BaseModel):
    enabled: bool = True
    lookback_days: int = 7
    decline_threshold: float = 0.15


class ThresholdsConfig(BaseModel):
    defaults: ThresholdDefault = ThresholdDefault()
    overrides: dict[str, SKUThreshold] = {}
    trend_alert: TrendAlert = TrendAlert()


# ── Supplier 配置模型 ──────────────────────────────────────────

class SupplierSelectors(BaseModel):
    username_input: str = ""
    password_input: str = ""
    login_button: str = ""
    price_table: str = ""
    price_cell: str = ""
    delivery_cell: str = ""


class SupplierEntry(BaseModel):
    name: str
    url: str
    login_url: str
    username: str
    password_encrypted: str = ""
    scraper_class: str = ""
    price_page: str = ""
    selectors: SupplierSelectors = SupplierSelectors()


class SuppliersConfig(BaseModel):
    suppliers: dict[str, SupplierEntry] = {}
    email: Optional[dict] = None
    webhook: Optional[dict] = None
    sql: Optional[dict] = None


# ── WMS 映射配置模型 ───────────────────────────────────────────

class Coordinate(BaseModel):
    x: int
    y: int
    desc: str = ""


class WMSField(BaseModel):
    x: int
    y: int
    desc: str = ""
    type: str = "text"
    format: str = ""


class WMSConfig(BaseModel):
    """简化加载，保留原始 dict 结构供 RPA 使用"""
    raw: dict = {}


# ── 配置加载器 ─────────────────────────────────────────────────

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_yaml(filename: str) -> dict:
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"配置文件不存在: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_settings() -> Settings:
    return Settings(**_load_yaml("settings.yaml"))


def load_thresholds() -> ThresholdsConfig:
    return ThresholdsConfig(**_load_yaml("thresholds.yaml"))


def load_suppliers() -> SuppliersConfig:
    return SuppliersConfig(**_load_yaml("suppliers.yaml"))


def load_wms_mapping() -> dict:
    """WMS 映射保持原始 dict，供 RPA 引擎直接使用"""
    return _load_yaml("wms_mapping.yaml")
