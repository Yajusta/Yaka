"""Service d'envoi d'emails via SMTP (configurable par variables d'environnement)."""

from email.message import EmailMessage
import smtplib
import os

from pathlib import Path
from dotenv import load_dotenv

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


def send_mail(to: str, subject: str, html_body: str, plain_body: str = ""):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_ADDRESS
    msg["To"] = to
    msg.set_content(plain_body or html_body, subtype="plain")
    msg.add_alternative(html_body, subtype="html")

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


def send_invitation(email: str, display_name: str | None, token: str):
    link = f"{INVITE_BASE_URL}?token={token}"
    subject = "Invitation à rejoindre Yaka (Yet Another Kanban App)"
    html = f"<p>Bonjour {display_name or 'Utilisateur'},</p><p>Vous avez été invité à rejoindre Yaka (Yet Another Kanban App). Cliquez <a href=\"{link}\">ici</a> pour définir votre mot de passe et activer votre compte.</p><br/>Si le lien ne s'affiche pas correctement, copiez-collez-le dans votre navigateur : <br/>{link}"
    plain = f"Bonjour {display_name or 'Utilisateur'},\n\nVous avez été invité à rejoindre Yaka (Yet Another Kanban App). Visitez {link} pour définir votre mot de passe et activer votre compte."
    send_mail(to=email, subject=subject, html_body=html, plain_body=plain)


def send_password_reset(email: str, display_name: str | None, token: str):
    link = f"{INVITE_BASE_URL}?token={token}&reset=true"
    subject = "Réinitialisation de votre mot de passe Yaka (Yet Another Kanban App)"
    html = f"<p>Bonjour {display_name or 'Utilisateur'},</p><p>Vous avez demandé une réinitialisation de votre mot de passe. Cliquez <a href=\"{link}\">ici</a> pour définir un nouveau mot de passe.</p><p>Si le lien ne s'affiche pas correctement, copiez-collez-le dans votre navigateur : <br/>{link}</p><p>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>"
    plain = f"Bonjour {display_name or 'Utilisateur'},\n\nVous avez demandé une réinitialisation de votre mot de passe. Visitez {link} pour définir un nouveau mot de passe.\n\nSi vous n'avez pas demandé cette réinitialisation, ignorez cet email."
    send_mail(to=email, subject=subject, html_body=html, plain_body=plain)
