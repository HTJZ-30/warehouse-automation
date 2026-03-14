"""PaddleOCR 中英混合识别引擎"""

from dataclasses import dataclass
from pathlib import Path

from shared.logger import get_logger

logger = get_logger("ocr_engine")


@dataclass
class OCRLine:
    """单行 OCR 识别结果"""
    text: str
    confidence: float
    bbox: list  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

    @property
    def x_center(self) -> float:
        return sum(p[0] for p in self.bbox) / 4

    @property
    def y_center(self) -> float:
        return sum(p[1] for p in self.bbox) / 4


@dataclass
class OCRResult:
    """整张图的 OCR 结果"""
    lines: list[OCRLine]
    image_path: str
    avg_confidence: float = 0.0

    def __post_init__(self):
        if self.lines:
            self.avg_confidence = sum(l.confidence for l in self.lines) / len(self.lines)

    @property
    def full_text(self) -> str:
        return "\n".join(line.text for line in self.lines)


# 延迟初始化 PaddleOCR (首次加载较慢)
_ocr_instance = None


def _get_ocr(lang: str = "ch"):
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        logger.info("初始化 PaddleOCR (lang=%s)...", lang)
        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            show_log=False,
        )
        logger.info("PaddleOCR 初始化完成")
    return _ocr_instance


def recognize(image_path: Path, lang: str = "ch") -> OCRResult:
    """对单张图片执行 OCR 识别

    Args:
        image_path: 图片路径
        lang: 语言 ('ch' 同时支持中英文)

    Returns:
        OCRResult 包含所有识别行
    """
    ocr = _get_ocr(lang)
    logger.info("OCR 识别: %s", image_path.name)

    raw_result = ocr.ocr(str(image_path), cls=True)

    lines = []
    if raw_result and raw_result[0]:
        for item in raw_result[0]:
            bbox = item[0]
            text = item[1][0]
            confidence = item[1][1]
            lines.append(OCRLine(text=text, confidence=confidence, bbox=bbox))

    result = OCRResult(lines=lines, image_path=str(image_path))

    logger.info(
        "识别完成: %d 行, 平均置信度 %.2f%%",
        len(lines), result.avg_confidence * 100,
    )
    return result


def recognize_batch(image_paths: list[Path], lang: str = "ch") -> list[OCRResult]:
    """批量 OCR 识别"""
    return [recognize(p, lang) for p in image_paths]
