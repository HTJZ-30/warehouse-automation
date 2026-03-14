"""SQLite 审计追踪模块"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class AuditTrail:
    """记录所有操作的审计日志到 SQLite"""

    def __init__(self, db_path: str = "data/audit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    details TEXT,
                    status TEXT DEFAULT 'success',
                    operator TEXT DEFAULT 'system'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_log(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_feature_action
                ON audit_log(feature, action)
            """)

    def log(
        self,
        feature: str,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[dict] = None,
        status: str = "success",
        operator: str = "system",
    ):
        """写入一条审计记录

        Args:
            feature: 功能标识 (feature1_inventory / feature2_receipt)
            action: 操作类型 (check_threshold / scrape_price / ocr_extract / rpa_entry 等)
            entity_type: 实体类型 (sku / receipt / supplier)
            entity_id: 实体ID
            details: 附加信息字典
            status: success / failure / skipped
            operator: 操作者
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO audit_log
                   (timestamp, feature, action, entity_type, entity_id, details, status, operator)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    feature,
                    action,
                    entity_type,
                    entity_id,
                    json.dumps(details, ensure_ascii=False) if details else None,
                    status,
                    operator,
                ),
            )

    def query(
        self,
        feature: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """查询审计记录"""
        conditions = []
        params = []
        if feature:
            conditions.append("feature = ?")
            params.append(feature)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM audit_log {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
