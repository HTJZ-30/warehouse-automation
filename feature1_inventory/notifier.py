"""邮件 + Webhook 通知模块"""

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

from shared.crypto import decrypt_value
from shared.logger import get_logger

logger = get_logger("notifier")


def send_email(
    smtp_server: str,
    smtp_port: int,
    sender: str,
    password_encrypted: str,
    recipients: list[str],
    subject: str,
    body_html: str,
    attachments: list[Path] = None,
    use_tls: bool = True,
):
    """发送带附件的邮件通知

    Args:
        smtp_server: SMTP 服务器
        smtp_port: 端口
        sender: 发件人
        password_encrypted: 加密后的密码
        recipients: 收件人列表
        subject: 邮件主题
        body_html: HTML 正文
        attachments: 附件路径列表
        use_tls: 是否使用 TLS
    """
    password = decrypt_value(password_encrypted)

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    for filepath in (attachments or []):
        filepath = Path(filepath)
        if filepath.exists():
            part = MIMEBase("application", "octet-stream")
            part.set_payload(filepath.read_bytes())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={filepath.name}",
            )
            msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        logger.info("邮件已发送到: %s", recipients)
    except Exception as e:
        logger.error("邮件发送失败: %s", e)
        raise


def send_dingtalk_webhook(webhook_url: str, title: str, content: str):
    """发送钉钉机器人通知 (Markdown 格式)"""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": content,
        },
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("钉钉通知已发送: %s", title)
    except Exception as e:
        logger.error("钉钉通知失败: %s", e)
        raise


def send_wecom_webhook(webhook_url: str, content: str):
    """发送企业微信机器人通知"""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": content,
        },
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("企微通知已发送")
    except Exception as e:
        logger.error("企微通知失败: %s", e)
        raise


def build_alert_email_body(alert_result, report_path: Path) -> str:
    """构建低库存告警邮件 HTML 正文"""
    critical_rows = ""
    for a in alert_result.critical_alerts:
        critical_rows += (
            f"<tr style='background:#ffe0e0'>"
            f"<td>{a.sku}</td><td>{a.name}</td>"
            f"<td>{a.current_stock:.0f}</td><td>{a.safety_stock}</td>"
            f"<td>{a.deficit:.0f}</td></tr>"
        )

    warning_rows = ""
    for a in alert_result.warning_alerts:
        warning_rows += (
            f"<tr style='background:#fff8dc'>"
            f"<td>{a.sku}</td><td>{a.name}</td>"
            f"<td>{a.current_stock:.0f}</td><td>{a.warning_threshold}</td>"
            f"<td>—</td></tr>"
        )

    return f"""
    <h2>仓库低库存预警报告</h2>
    <p>检查时间: {Path(report_path).stem.split('_', 1)[-1] if report_path else 'N/A'}</p>
    <p>严重告警: <b style="color:red">{len(alert_result.critical_alerts)}</b> 项 |
       预警: <b style="color:orange">{len(alert_result.warning_alerts)}</b> 项</p>

    <h3>严重 (低于安全库存)</h3>
    <table border="1" cellpadding="5" cellspacing="0">
    <tr><th>SKU</th><th>品名</th><th>当前库存</th><th>安全库存</th><th>缺口</th></tr>
    {critical_rows}
    </table>

    <h3>预警 (低于预警线)</h3>
    <table border="1" cellpadding="5" cellspacing="0">
    <tr><th>SKU</th><th>品名</th><th>当前库存</th><th>预警线</th><th>缺口</th></tr>
    {warning_rows}
    </table>

    <p>详细比价表见附件。</p>
    <hr>
    <p style="color:gray;font-size:12px">此邮件由仓库自动化系统自动发送</p>
    """


def build_webhook_content(alert_result) -> str:
    """构建 Webhook 通知 Markdown 内容"""
    lines = ["## 仓库低库存预警", ""]
    lines.append(f"**严重告警**: {len(alert_result.critical_alerts)} 项")
    lines.append(f"**预警**: {len(alert_result.warning_alerts)} 项")
    lines.append("")

    if alert_result.critical_alerts:
        lines.append("### 严重")
        for a in alert_result.critical_alerts:
            lines.append(f"- **{a.sku}** {a.name}: 库存 {a.current_stock:.0f} (安全线 {a.safety_stock})")

    if alert_result.warning_alerts:
        lines.append("")
        lines.append("### 预警")
        for a in alert_result.warning_alerts:
            lines.append(f"- **{a.sku}** {a.name}: 库存 {a.current_stock:.0f} (预警线 {a.warning_threshold})")

    return "\n".join(lines)


def notify(settings, suppliers_config, alert_result, report_path: Path):
    """统一通知入口"""
    # 邮件通知
    if settings.email.recipients:
        email_pwd = (suppliers_config.email or {}).get("password_encrypted", "")
        body = build_alert_email_body(alert_result, report_path)
        send_email(
            smtp_server=settings.email.smtp_server,
            smtp_port=settings.email.smtp_port,
            sender=settings.email.sender,
            password_encrypted=email_pwd,
            recipients=settings.email.recipients,
            subject=f"[低库存预警] 严重 {len(alert_result.critical_alerts)} / 预警 {len(alert_result.warning_alerts)}",
            body_html=body,
            attachments=[report_path] if report_path else [],
            use_tls=settings.email.use_tls,
        )

    # Webhook 通知
    if settings.webhook.enabled and settings.webhook.url:
        content = build_webhook_content(alert_result)
        if settings.webhook.type == "dingtalk":
            send_dingtalk_webhook(settings.webhook.url, "低库存预警", content)
        elif settings.webhook.type == "wecom":
            send_wecom_webhook(settings.webhook.url, content)
