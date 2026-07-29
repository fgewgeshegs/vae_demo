"""邮件发送服务 - 发送密码重置验证码等"""

from __future__ import annotations

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger("app.email")


def send_reset_code(recipient_email: str, code: str) -> bool:
    """发送密码重置验证码

    如果 SMTP 已配置，发送真实邮件；
    否则将验证码打印到日志。

    Returns:
        bool: 是否成功发送（或成功记录日志）
    """
    name = settings.SMTP_FROM_NAME or "知境"
    subject = f"{name} - 密码重置验证码"
    body = f"""\
<div style="font-family:sans-serif;max-width:480px;margin:40px auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px">
  <h2 style="color:#1D2129;margin:0 0 16px">密码重置</h2>
  <p style="color:#6B7280;font-size:14px;line-height:1.6">
    您收到此邮件是因为您请求重置 <strong>{name}</strong> 的登录密码。<br>
    请在 15 分钟内输入以下验证码完成重置：
  </p>
  <div style="text-align:center;margin:24px 0;font-size:36px;font-weight:700;letter-spacing:8px;color:#1877F2">
    {code}
  </div>
  <p style="color:#9CA3AF;font-size:12px;margin:16px 0 0">
    如果您没有请求重置密码，请忽略此邮件。
  </p>
</div>
"""

    if not settings.smtp_configured:
        logger.warning(
            "SMTP 未配置，无法发送邮件。验证码 %s 已记录到日志。"
            "请设置 SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD 启用邮件发送。",
            code,
        )
        logger.info("密码重置验证码 [%s] -> %s", code, recipient_email)
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))

        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)

        logger.info("密码重置验证码已发送至 %s", recipient_email)
        return True

    except Exception as e:
        logger.error("发送邮件失败 [%s]: %s", recipient_email, e)
        return False
