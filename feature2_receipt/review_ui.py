"""Tkinter 人工复核界面"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

from shared.logger import get_logger

logger = get_logger("review_ui")


class ReviewResult:
    """复核结果"""

    def __init__(self):
        self.approved = False
        self.fields: dict[str, str] = {}


class ReviewWindow:
    """双栏界面: 左侧原图 + 右侧可编辑字段"""

    FIELD_LABELS = {
        "receipt_no": "单据编号",
        "receipt_type": "单据类型",
        "product_name": "品名",
        "quantity": "数量",
        "unit": "单位",
        "date": "日期",
        "warehouse": "仓库",
        "supplier": "供应商",
        "remark": "备注",
    }

    def __init__(self, image_path: Path, parsed_receipt, validation_result):
        self.image_path = image_path
        self.parsed = parsed_receipt
        self.validation = validation_result
        self.result = ReviewResult()
        self.entries: dict[str, tk.Entry] = {}

    def show(self) -> ReviewResult:
        """显示复核窗口，阻塞直到用户操作完成"""
        self.root = tk.Tk()
        self.root.title("单据复核 — 仓库自动化系统")
        self.root.geometry("1200x700")
        self.root.configure(bg="#f5f5f5")

        # ── 顶部信息栏 ────────────────────────────────────────
        info_frame = ttk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        action_text = {
            "review": "建议复核 (置信度 70-90%)",
            "force_review": "强制复核 (置信度 <70% 或有错误)",
        }
        action_str = action_text.get(self.validation.action.value, self.validation.action.value)
        ttk.Label(
            info_frame,
            text=f"置信度: {self.validation.confidence:.1%} | 状态: {action_str}",
            font=("微软雅黑", 11),
        ).pack(side=tk.LEFT)

        if self.validation.errors:
            ttk.Label(
                info_frame,
                text=f"错误: {len(self.validation.errors)}",
                foreground="red",
                font=("微软雅黑", 11, "bold"),
            ).pack(side=tk.LEFT, padx=20)

        # ── 主体: 左右分栏 ────────────────────────────────────
        main_frame = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左栏: 原图
        left_frame = ttk.LabelFrame(main_frame, text="原始单据")
        main_frame.add(left_frame, weight=1)
        self._setup_image_panel(left_frame)

        # 右栏: 字段编辑
        right_frame = ttk.LabelFrame(main_frame, text="识别字段 (可编辑)")
        main_frame.add(right_frame, weight=1)
        self._setup_fields_panel(right_frame)

        # ── 底部按钮 ──────────────────────────────────────────
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            btn_frame, text="确认录入", command=self._on_approve,
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            btn_frame, text="驳回", command=self._on_reject,
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            btn_frame, text="跳过", command=self._on_skip,
        ).pack(side=tk.RIGHT, padx=5)

        self.root.mainloop()
        return self.result

    def _setup_image_panel(self, parent):
        canvas = tk.Canvas(parent, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        try:
            img = Image.open(self.image_path)
            # 缩放到面板大小
            img.thumbnail((550, 600))
            self._photo = ImageTk.PhotoImage(img)
            canvas.create_image(5, 5, anchor=tk.NW, image=self._photo)
        except Exception as e:
            canvas.create_text(200, 300, text=f"无法加载图片:\n{e}", fill="red")

    def _setup_fields_panel(self, parent):
        # 错误/警告提示
        if self.validation.errors or self.validation.warnings:
            alert_frame = ttk.Frame(parent)
            alert_frame.pack(fill=tk.X, padx=5, pady=5)
            for err in self.validation.errors:
                ttk.Label(
                    alert_frame,
                    text=f"[错误] {self.FIELD_LABELS.get(err.field, err.field)}: {err.message}",
                    foreground="red",
                ).pack(anchor=tk.W)
            for warn in self.validation.warnings:
                ttk.Label(
                    alert_frame,
                    text=f"[警告] {self.FIELD_LABELS.get(warn.field, warn.field)}: {warn.message}",
                    foreground="orange",
                ).pack(anchor=tk.W)

        # 字段输入
        fields_frame = ttk.Frame(parent)
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        for row_idx, (field_key, label) in enumerate(self.FIELD_LABELS.items()):
            ttk.Label(
                fields_frame, text=f"{label}:", font=("微软雅黑", 10),
            ).grid(row=row_idx, column=0, sticky=tk.E, padx=5, pady=3)

            entry = ttk.Entry(fields_frame, width=40, font=("微软雅黑", 10))
            entry.grid(row=row_idx, column=1, sticky=tk.W, padx=5, pady=3)

            # 预填 OCR 识别值
            value = getattr(self.parsed, field_key, None)
            if value is not None:
                entry.insert(0, str(value))

            # 低置信度字段标红
            conf = self.parsed.field_confidences.get(field_key, 1.0)
            if conf < 0.7:
                entry.configure(foreground="red")

            self.entries[field_key] = entry

        # OCR 原文
        ttk.Label(
            fields_frame, text="OCR原文:", font=("微软雅黑", 10),
        ).grid(row=len(self.FIELD_LABELS), column=0, sticky=tk.NE, padx=5, pady=3)

        text_widget = tk.Text(fields_frame, width=40, height=8, font=("Consolas", 9))
        text_widget.grid(
            row=len(self.FIELD_LABELS), column=1, sticky=tk.W, padx=5, pady=3,
        )
        text_widget.insert(tk.END, self.parsed.raw_text)
        text_widget.configure(state=tk.DISABLED)

    def _collect_fields(self):
        for key, entry in self.entries.items():
            self.result.fields[key] = entry.get().strip()

    def _on_approve(self):
        self._collect_fields()
        self.result.approved = True
        logger.info("复核通过: %s", self.result.fields.get("receipt_no", "N/A"))
        self.root.destroy()

    def _on_reject(self):
        self._collect_fields()
        self.result.approved = False
        logger.info("复核驳回: %s", self.result.fields.get("receipt_no", "N/A"))
        self.root.destroy()

    def _on_skip(self):
        self.result.approved = False
        self.result.fields = {}
        logger.info("复核跳过")
        self.root.destroy()


def open_review(
    image_path: Path,
    parsed_receipt,
    validation_result,
) -> Optional[dict]:
    """打开复核窗口

    Returns:
        修正后的字段 dict (如果用户确认), 或 None (驳回/跳过)
    """
    window = ReviewWindow(image_path, parsed_receipt, validation_result)
    result = window.show()
    if result.approved:
        return result.fields
    return None
