"""Feature 2 入口: 出入库单据自动录入"""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.audit import AuditTrail
from shared.config_loader import load_settings, load_wms_mapping
from shared.logger import get_logger

from feature2_receipt.folder_watcher import start_watching
from feature2_receipt.image_preprocessor import preprocess_image
from feature2_receipt.ocr_engine import recognize
from feature2_receipt.field_parser import parse_ocr_result
from feature2_receipt.validator import validate_receipt, ReviewAction
from feature2_receipt.review_ui import open_review
from feature2_receipt.rpa_engine import RPAEngine

logger = get_logger("feature2_main")


def process_receipt_image(image_path: Path, settings, wms_config, audit: AuditTrail):
    """处理单张单据图片的完整流程"""
    logger.info("处理单据图片: %s", image_path.name)
    audit.log("feature2_receipt", "process_started", entity_type="receipt",
              entity_id=image_path.name)

    try:
        # 1. 图像预处理
        logger.info("步骤 1/6: 图像预处理")
        processed_path = preprocess_image(image_path)

        # 2. OCR 识别
        logger.info("步骤 2/6: OCR 识别")
        ocr_result = recognize(processed_path, lang=settings.feature2.ocr_lang)
        audit.log("feature2_receipt", "ocr_complete", entity_id=image_path.name,
                  details={"lines": len(ocr_result.lines),
                           "avg_confidence": ocr_result.avg_confidence})

        # 3. 字段解析
        logger.info("步骤 3/6: 字段解析")
        parsed = parse_ocr_result(ocr_result)
        audit.log("feature2_receipt", "fields_parsed", entity_id=image_path.name,
                  details={"receipt_no": parsed.receipt_no,
                           "product_name": parsed.product_name,
                           "quantity": parsed.quantity})

        # 4. 校验
        logger.info("步骤 4/6: 字段校验")
        validation = validate_receipt(
            parsed,
            auto_pass_threshold=settings.feature2.confidence_auto_pass,
            review_threshold=settings.feature2.confidence_review,
        )
        audit.log("feature2_receipt", "validation_complete", entity_id=image_path.name,
                  details={"action": validation.action.value,
                           "confidence": validation.confidence,
                           "errors": len(validation.errors)})

        # 5. 人工复核 (按置信度)
        entry_data = None
        if validation.action == ReviewAction.AUTO_PASS:
            logger.info("步骤 5/6: 自动通过 (置信度 %.1f%%)", validation.confidence * 100)
            entry_data = _parsed_to_dict(parsed)
        else:
            logger.info("步骤 5/6: 需要人工复核 (%s)", validation.action.value)
            reviewed = open_review(image_path, parsed, validation)
            if reviewed:
                entry_data = reviewed
                audit.log("feature2_receipt", "review_approved", entity_id=image_path.name)
            else:
                logger.info("人工复核: 驳回/跳过")
                audit.log("feature2_receipt", "review_rejected", entity_id=image_path.name)
                _move_to_failed(image_path, settings)
                return

        # 6. 录入 Excel 台账
        logger.info("步骤 6/6: 录入 Excel 台账")
        rpa = RPAEngine(wms_config, field_delay=settings.feature2.rpa_delay_between_fields)
        success = rpa.entry_receipt(entry_data, source_image=str(image_path.name))

        if success:
            audit.log("feature2_receipt", "rpa_entry_success", entity_id=image_path.name,
                      details=entry_data)
            _move_to_processed(image_path, settings)
            logger.info("单据处理完成: %s", entry_data.get("receipt_no", image_path.name))
        else:
            audit.log("feature2_receipt", "rpa_entry_failed", entity_id=image_path.name,
                      status="failure")
            _move_to_failed(image_path, settings)

    except Exception as e:
        logger.exception("处理失败: %s — %s", image_path.name, e)
        audit.log("feature2_receipt", "process_failed", entity_id=image_path.name,
                  status="failure", details={"error": str(e)})
        _move_to_failed(image_path, settings)


def _parsed_to_dict(parsed) -> dict:
    """将 ParsedReceipt 转为 RPA 输入 dict"""
    return {
        "receipt_no": parsed.receipt_no or "",
        "receipt_type": parsed.receipt_type or "入库",
        "product_name": parsed.product_name or "",
        "quantity": str(parsed.quantity) if parsed.quantity else "",
        "date": parsed.date or "",
        "warehouse": parsed.warehouse or "",
        "supplier": parsed.supplier or "",
        "remark": parsed.remark or "",
    }


def _move_to_processed(image_path: Path, settings):
    dest = Path(settings.feature2.processed_folder)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(image_path), str(dest / image_path.name))
    # 同时移动预处理文件
    processed = image_path.with_name(f"{image_path.stem}_processed.png")
    if processed.exists():
        shutil.move(str(processed), str(dest / processed.name))


def _move_to_failed(image_path: Path, settings):
    dest = Path(settings.feature2.failed_folder)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(image_path), str(dest / image_path.name))


def run():
    """Feature 2 主流程: 启动文件夹监控"""
    logger.info("=" * 60)
    logger.info("Feature 2: 出入库单据自动录入 — 启动")
    logger.info("=" * 60)

    settings = load_settings()
    wms_config = load_wms_mapping()
    audit = AuditTrail(settings.audit.db_path)

    audit.log("feature2_receipt", "service_started")

    def on_new_image(image_path: Path):
        process_receipt_image(image_path, settings, wms_config, audit)

    observer = start_watching(settings.feature2.watch_folder, on_new_image)

    logger.info("监控运行中... 按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号")
        observer.stop()
    observer.join()

    audit.log("feature2_receipt", "service_stopped")
    logger.info("Feature 2 已停止")


if __name__ == "__main__":
    run()
