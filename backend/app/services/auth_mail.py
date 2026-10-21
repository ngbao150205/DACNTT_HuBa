"""Transactional reset email; Mailpit is the local Compose default."""
import html
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_reset_email(address, name, reset_url):
    message = EmailMessage()
    message["Subject"] = "Đặt lại mật khẩu DuanCNTT"
    message["From"] = os.getenv("SMTP_FROM", "DuanCNTT <no-reply@duancntt.local>")
    message["To"] = address
    message.set_content(f"Xin chào {name},\n\nMở liên kết sau để đặt lại mật khẩu (hết hạn sau 15 phút, dùng một lần):\n{reset_url}\n\nNếu bạn không yêu cầu, hãy bỏ qua email này.\n")
    message.add_alternative(
        f'<p>Xin chào {html.escape(name)},</p><p>Bạn đã yêu cầu đặt lại mật khẩu DuanCNTT.</p>'
        f'<p><a href="{html.escape(reset_url, quote=True)}">Đặt lại mật khẩu</a></p>'
        '<p>Liên kết hết hạn sau 15 phút và chỉ sử dụng được một lần.</p>'
        '<p>Nếu bạn không yêu cầu, hãy bỏ qua email này.</p>', subtype="html")
    try:
        host = os.getenv("SMTP_HOST", "localhost")
        port = int(os.getenv("SMTP_PORT", "1025"))
        use_ssl = os.getenv("SMTP_SSL", "false").lower() == "true"
        factory = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        options = {"context": ssl.create_default_context()} if use_ssl else {}
        with factory(host, port, timeout=10, **options) as smtp:
            if not use_ssl and os.getenv("SMTP_STARTTLS", "false").lower() == "true":
                smtp.starttls(context=ssl.create_default_context())
            username = os.getenv("SMTP_USERNAME", "")
            if username:
                smtp.login(username, os.getenv("SMTP_PASSWORD", ""))
            smtp.send_message(message)
    except Exception:
        # Never log reset URLs, mail bodies or SMTP credentials.
        logger.error("Password reset email delivery failed; check SMTP configuration.")
