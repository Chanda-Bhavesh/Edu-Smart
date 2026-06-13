import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.config import settings

_template_dir = Path(__file__).parent.parent / "templates" / "email"
_jinja_env = Environment(loader=FileSystemLoader(str(_template_dir)), autoescape=True)


def _render(template_name: str, context: dict) -> str:
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


def _send(to_email: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.emails_from_name} <{settings.emails_from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.emails_from_email, to_email, msg.as_string())


def send_verification_email(to_email: str, full_name: str, token: str) -> None:
    verify_url = f"{settings.frontend_url}/verify-email?token={token}"
    html = _render("verification.html", {"full_name": full_name, "verify_url": verify_url})
    _send(to_email, "Verify your SCMS account", html)


def send_password_reset_email(to_email: str, full_name: str, token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    html = _render("reset_password.html", {"full_name": full_name, "reset_url": reset_url})
    _send(to_email, "Reset your SCMS password", html)


def send_welcome_email(to_email: str, full_name: str) -> None:
    html = _render("welcome.html", {"full_name": full_name, "login_url": f"{settings.frontend_url}/login"})
    _send(to_email, "Welcome to SCMS!", html)
