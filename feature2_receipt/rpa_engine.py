"""pyautogui WMS 自动录入引擎"""

import time
from datetime import datetime
from pathlib import Path

import pyautogui
import pygetwindow as gw

from shared.logger import get_logger

logger = get_logger("rpa_engine")

# pyautogui 安全设置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2


class RPAEngine:
    """WMS 自动录入引擎 (基于坐标配置)"""

    def __init__(self, wms_config: dict, field_delay: float = 0.3):
        self.config = wms_config
        self.field_delay = field_delay
        self.screenshot_dir = Path(
            wms_config.get("verification", {}).get("screenshot_dir", "output/screenshots/")
        )
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def activate_wms_window(self) -> bool:
        """激活 WMS 窗口"""
        window_title = self.config.get("wms", {}).get("window_title", "仓库管理系统")
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                logger.error("未找到 WMS 窗口: %s", window_title)
                return False
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            startup_delay = self.config.get("wms", {}).get("startup_delay", 2.0)
            time.sleep(startup_delay)
            logger.info("WMS 窗口已激活: %s", window_title)
            return True
        except Exception as e:
            logger.error("激活 WMS 窗口失败: %s", e)
            return False

    def navigate_to_entry_form(self, form_type: str = "receipt_entry"):
        """通过菜单导航到录入表单"""
        menu_config = self.config.get(form_type, {}).get("menu_path", [])
        for step in menu_config:
            pyautogui.click(step["x"], step["y"])
            time.sleep(0.5)
            logger.info("菜单导航: %s", step.get("desc", ""))

    def fill_fields(self, form_type: str, data: dict):
        """填写表单字段

        Args:
            form_type: 表单类型 (receipt_entry / shipment_entry)
            data: 字段数据 {field_name: value}
        """
        fields_config = self.config.get(form_type, {}).get("fields", {})

        for field_name, value in data.items():
            if value is None or str(value).strip() == "":
                continue

            field_cfg = fields_config.get(field_name)
            if not field_cfg:
                logger.warning("未配置的字段: %s", field_name)
                continue

            x, y = field_cfg["x"], field_cfg["y"]
            field_type = field_cfg.get("type", "text")

            # 点击字段位置
            pyautogui.click(x, y)
            time.sleep(self.field_delay)

            if field_type == "dropdown":
                # 下拉框: 点击后输入文字搜索
                pyautogui.typewrite(str(value), interval=0.05) if value.isascii() else \
                    self._type_chinese(str(value))
                time.sleep(0.3)
                pyautogui.press("enter")
            elif field_type == "date":
                # 日期字段: 全选后输入
                pyautogui.hotkey("ctrl", "a")
                date_format = field_cfg.get("format", "YYYY-MM-DD")
                formatted = self._format_date(str(value), date_format)
                pyautogui.typewrite(formatted, interval=0.05)
            else:
                # 文本/数字: 清空后输入
                pyautogui.hotkey("ctrl", "a")
                if str(value).isascii():
                    pyautogui.typewrite(str(value), interval=0.03)
                else:
                    self._type_chinese(str(value))

            logger.info(
                "填写字段: %s = %s", field_cfg.get("desc", field_name), value,
            )
            time.sleep(self.field_delay)

    def click_button(self, form_type: str, button_name: str):
        """点击表单按钮"""
        buttons = self.config.get(form_type, {}).get("buttons", {})
        btn = buttons.get(button_name)
        if not btn:
            logger.warning("未配置的按钮: %s", button_name)
            return
        pyautogui.click(btn["x"], btn["y"])
        logger.info("点击按钮: %s", btn.get("desc", button_name))

    def take_verification_screenshot(self, receipt_no: str = "") -> Path:
        """截图验证"""
        verify_delay = self.config.get("verification", {}).get("verify_delay", 1.5)
        time.sleep(verify_delay)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.screenshot_dir / f"verify_{receipt_no}_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(str(filename))
        logger.info("验证截图: %s", filename)
        return filename

    def entry_receipt(self, data: dict) -> bool:
        """完整入库单录入流程

        Args:
            data: 包含字段 receipt_no, product_name, quantity, unit, date, warehouse, supplier, remark

        Returns:
            是否成功
        """
        try:
            if not self.activate_wms_window():
                return False

            self.navigate_to_entry_form("receipt_entry")
            time.sleep(1.0)

            self.fill_fields("receipt_entry", data)
            self.click_button("receipt_entry", "save")
            time.sleep(1.0)

            # 截图验证
            should_screenshot = self.config.get("verification", {}).get("screenshot_after_save", True)
            if should_screenshot:
                self.take_verification_screenshot(data.get("receipt_no", ""))

            logger.info("入库单录入完成: %s", data.get("receipt_no", ""))
            return True

        except pyautogui.FailSafeException:
            logger.warning("触发安全中止 (鼠标移至左上角)")
            return False
        except Exception as e:
            logger.error("RPA 录入失败: %s", e)
            return False

    @staticmethod
    def _type_chinese(text: str):
        """通过剪贴板输入中文"""
        import subprocess
        # Windows: 使用 clip 命令写入剪贴板
        process = subprocess.Popen(
            ["clip"], stdin=subprocess.PIPE, shell=True,
        )
        process.communicate(text.encode("utf-16le"))
        pyautogui.hotkey("ctrl", "v")

    @staticmethod
    def _format_date(date_str: str, fmt: str) -> str:
        """将日期格式化为目标格式"""
        # 清理中文日期格式
        clean = date_str.replace("年", "-").replace("月", "-").replace("日", "")
        clean = clean.replace("/", "-")
        return clean
