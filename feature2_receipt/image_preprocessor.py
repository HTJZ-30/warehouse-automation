"""图像预处理模块: 旋转校正、对比度增强、格式转换"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance

from shared.logger import get_logger

logger = get_logger("image_preprocessor")


def preprocess_image(image_path: Path, output_path: Path = None) -> Path:
    """预处理单据图像

    步骤:
    1. 格式转换 (HEIF -> JPEG)
    2. 旋转校正 (基于 EXIF 或文本方向检测)
    3. 灰度化
    4. 对比度增强
    5. 降噪
    6. 二值化 (自适应阈值)

    Args:
        image_path: 输入图片路径
        output_path: 输出路径 (None 则覆盖原文件)

    Returns:
        处理后的图片路径
    """
    if output_path is None:
        output_path = image_path.with_name(f"{image_path.stem}_processed.png")

    logger.info("预处理图像: %s", image_path.name)

    # 1. 加载图片 (处理 HEIF 格式)
    img = _load_image(image_path)

    # 2. EXIF 旋转校正
    img = _fix_orientation(img)

    # 3. 转为 OpenCV 格式处理
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # 4. 灰度化
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 5. 对比度增强 (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # 6. 降噪
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

    # 7. 自适应二值化
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=8,
    )

    # 8. 轻微膨胀 (增强文字连通性)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    processed = cv2.dilate(binary, kernel, iterations=1)

    cv2.imwrite(str(output_path), processed)
    logger.info("预处理完成: %s -> %s", image_path.name, output_path.name)

    return output_path


def _load_image(image_path: Path) -> Image.Image:
    """加载图片，支持 HEIF 格式"""
    suffix = image_path.suffix.lower()
    if suffix in (".heif", ".heic"):
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            logger.warning("pillow-heif 未安装，无法处理 HEIF 格式")
            raise
    return Image.open(image_path).convert("RGB")


def _fix_orientation(img: Image.Image) -> Image.Image:
    """根据 EXIF 数据修正旋转方向"""
    try:
        exif = img.getexif()
        orientation = exif.get(0x0112)  # Orientation tag
        rotations = {
            3: 180,
            6: 270,
            8: 90,
        }
        if orientation in rotations:
            img = img.rotate(rotations[orientation], expand=True)
            logger.info("EXIF 旋转校正: %d°", rotations[orientation])
    except Exception:
        pass  # 无 EXIF 数据，跳过
    return img


def enhance_for_ocr(image_path: Path) -> Path:
    """简化版增强: 仅做对比度提升 + 锐化 (给 OCR 用原彩色图)"""
    img = Image.open(image_path)
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    out = image_path.with_name(f"{image_path.stem}_enhanced.png")
    img.save(out)
    return out
