"""Service d'envoi d'emails via SMTP (configurable par variables d'environnement)."""

import logging
import os
import smtplib
import urllib.parse
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .email_templates import (
    get_invitation_html,
    get_invitation_plain,
    get_password_reset_html,
    get_password_reset_plain,
)

logger = logging.getLogger(__name__)

# Charger le .env situé à la racine du dossier `backend`
# Ce fichier est : backend/.env (on remonte de app/services -> parents[2])
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=str(_env_path))
else:
    # essayer de charger un .env si trouvé ailleurs (silencieux sinon)
    load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "0.0.0.0")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SECURE = os.getenv("SMTP_SECURE", "starttls").lower()  # values: 'ssl'|'starttls'|'none'
FROM_ADDRESS = os.getenv("SMTP_FROM", "no-reply@kanban.local")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
INVITE_BASE_URL = f"{BASE_URL}/invite"
PASSWORD_RESET_BASE_URL = f"{BASE_URL}/invite"


def send_mail(to: str, subject: str, html_body: str, plain_body: str = ""):
    if not plain_body:
        raise ValueError("plain_body must be provided to avoid unreadable plain text emails.")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_ADDRESS
    msg["To"] = to
    msg.set_content(plain_body, subtype="plain")
    msg.add_alternative(html_body, subtype="html")

    try:
        if SMTP_SECURE == "ssl":
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                if SMTP_SECURE == "starttls":
                    server.starttls()
                    server.ehlo()
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
    except smtplib.SMTPException as e:
        logger.error(f"Failed to connect to SMTP server: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error occurred while sending email: {e}")
        raise e


def send_invitation(email: str, display_name: Optional[str], token: str, board_uid: Optional[str] = None):
    encoded_token = urllib.parse.quote_plus(token)
    if board_uid:
        invite_link = f"{BASE_URL}/board/{board_uid}/invite?token={encoded_token}"
        board_url = f"{BASE_URL}/board/{board_uid}"
    else:
        invite_link = f"{INVITE_BASE_URL}?token={encoded_token}"
        board_url = BASE_URL
    
    name = display_name or "User"
    subject = "Invitation to Join Yaka (Yet Another Kanban App)"
    html = get_invitation_html(name, invite_link, board_url)
    plain = get_invitation_plain(name, invite_link, board_url)
    send_mail(to=email, subject=subject, html_body=html, plain_body=plain)


def send_password_reset(email: str, display_name: Optional[str], token: str, board_uid: Optional[str] = None):
    encoded_token = urllib.parse.quote_plus(token)
    if board_uid:
        reset_link = f"{BASE_URL}/board/{board_uid}/invite?token={encoded_token}&reset=true"
        board_url = f"{BASE_URL}/board/{board_uid}"
    else:
        reset_link = f"{PASSWORD_RESET_BASE_URL}?token={encoded_token}&reset=true"
        board_url = BASE_URL
    
    name = display_name or "User"
    subject = "Password Reset - Yaka (Yet Another Kanban App)"
    html = get_password_reset_html(name, reset_link, board_url)
    plain = get_password_reset_plain(name, reset_link, board_url)
    send_mail(to=email, subject=subject, html_body=html, plain_body=plain)
