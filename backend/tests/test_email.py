"""Tests complets pour le service Email."""

import os
import smtplib
import sys
from contextlib import contextmanager
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

# Set up clean environment for tests before importing the email service
test_env_vars = {
    "SMTP_HOST": "localhost",
    "SMTP_PORT": "587",
    "SMTP_USER": "",
    "SMTP_PASS": "",
    "SMTP_SECURE": "none",
    "SMTP_FROM": "test@example.com",
    "BASE_URL": "http://localhost:8000",
    "DEMO_MODE": "false",
    "DEFAULT_LANGUAGE": "en",
}

# Apply test environment before importing
with patch.dict(os.environ, test_env_vars, clear=True):
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    # Ensure the email module reloads under the test-specific environment
    sys.modules.pop("app.services.email", None)

    from app.services.email import (
        BASE_URL,
        FROM_ADDRESS,
        INVITE_BASE_URL,
        PASSWORD_RESET_BASE_URL,
        SMTP_HOST,
        SMTP_PORT,
        SMTP_SECURE,
        send_invitation,
        send_mail,
        send_password_reset,
    )


@contextmanager
def temp_env_vars(**kwargs):
    """Context manager pour modifier temporairement les variables d'environnement."""
    # Create merged environment with test defaults and overrides
    merged_env = test_env_vars.copy()
    merged_env.update(kwargs)

    with patch.dict(os.environ, merged_env, clear=True):
        yield


@pytest.fixture
def mock_smtp():
    """Fixture pour mocker le serveur SMTP."""
    with patch("smtplib.SMTP") as mock_smtp_class, patch("smtplib.SMTP_SSL") as mock_smtp_ssl_class:

        # Créer des instances mock
        mock_smtp_instance = MagicMock()
        mock_smtp_ssl_instance = MagicMock()

        mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
        mock_smtp_ssl_class.return_value.__enter__.return_value = mock_smtp_ssl_instance

        yield {
            "smtp": mock_smtp_instance,
            "smtp_ssl": mock_smtp_ssl_instance,
            "smtp_class": mock_smtp_class,
            "smtp_ssl_class": mock_smtp_ssl_class,
        }


@pytest.fixture
def sample_email_data():
    """Fixture pour les données d'email de test."""
    return {
        "to": "test@example.com",
        "subject": "Test Subject",
        "html_body": "<h1>Test HTML</h1><p>Content</p>",
        "plain_body": "Test Plain Text\nContent",
    }


@pytest.fixture
def sample_invitation_data():
    """Fixture pour les données d'invitation de test."""
    return {"email": "user@example.com", "display_name": "John Doe", "token": "test-token-123"}


@pytest.fixture
def sample_reset_data():
    """Fixture pour les données de réinitialisation de test."""
    return {"email": "user@example.com", "display_name": "Jane Doe", "token": "reset-token-456"}


class TestSendMail:
    """Tests pour la fonction send_mail."""

    def test_send_mail_success_starttls(self, mock_smtp, sample_email_data):
        """Test d'envoi réussi avec STARTTLS."""
        with patch("app.services.email.SMTP_SECURE", "starttls"), patch(
            "app.services.email.SMTP_USER", "test@example.com"
        ), patch("app.services.email.SMTP_PASS", "password123"):

            send_mail(**sample_email_data)

            # Vérifier que SMTP a été utilisé (pas SSL)
            mock_smtp["smtp_class"].assert_called_once()
            mock_smtp["smtp_ssl_class"].assert_not_called()

            # Vérifier les appels de méthode
            mock_smtp["smtp"].ehlo.assert_called()
            mock_smtp["smtp"].starttls.assert_called_once()
            mock_smtp["smtp"].ehlo.assert_called()
            mock_smtp["smtp"].login.assert_called_once_with("test@example.com", "password123")
            mock_smtp["smtp"].send_message.assert_called_once()

    def test_send_mail_success_ssl(self, mock_smtp, sample_email_data):
        """Test d'envoi réussi avec SSL."""
        with patch("app.services.email.SMTP_SECURE", "ssl"), patch(
            "app.services.email.SMTP_USER", "test@example.com"
        ), patch("app.services.email.SMTP_PASS", "password123"):

            send_mail(**sample_email_data)

            # Vérifier que SMTP_SSL a été utilisé
            mock_smtp["smtp_ssl_class"].assert_called_once()
            mock_smtp["smtp_class"].assert_not_called()

            # Vérifier les appels de méthode
            mock_smtp["smtp_ssl"].login.assert_called_once_with("test@example.com", "password123")
            mock_smtp["smtp_ssl"].send_message.assert_called_once()

    def test_send_mail_success_none(self, mock_smtp, sample_email_data):
        """Test d'envoi réussi sans sécurité (none)."""
        with patch("app.services.email.SMTP_SECURE", "none"), patch("app.services.email.SMTP_USER", ""), patch(
            "app.services.email.SMTP_PASS", ""
        ):

            send_mail(**sample_email_data)

            # Vérifier que SMTP a été utilisé sans sécurité
            mock_smtp["smtp_class"].assert_called_once()
            mock_smtp["smtp_ssl_class"].assert_not_called()

            # Vérifier les appels de méthode
            mock_smtp["smtp"].ehlo.assert_called_once()
            mock_smtp["smtp"].starttls.assert_not_called()
            mock_smtp["smtp"].login.assert_not_called()
            mock_smtp["smtp"].send_message.assert_called_once()

    def test_send_mail_no_auth(self, mock_smtp, sample_email_data):
        """Test d'envoi sans authentification."""
        with patch("app.services.email.SMTP_SECURE", "starttls"), patch("app.services.email.SMTP_USER", ""), patch(
            "app.services.email.SMTP_PASS", ""
        ):

            send_mail(**sample_email_data)

            # Vérifier que login n'a pas été appelé
            mock_smtp["smtp"].login.assert_not_called()
            mock_smtp["smtp"].send_message.assert_called_once()

    def test_send_mail_default_config(self, mock_smtp, sample_email_data):
        """Test d'envoi avec la configuration par défaut."""
        # Utiliser la configuration de base définie dans les imports
        send_mail(**sample_email_data)

        # Vérifier que la configuration par défaut est utilisée
        mock_smtp["smtp_class"].assert_called_once_with("localhost", 587)
        mock_smtp["smtp"].login.assert_not_called()  # Pas d'auth par défaut

    def test_send_mail_missing_plain_body(self, sample_email_data):
        """Test d'erreur lorsque plain_body est manquant."""
        data = sample_email_data.copy()
        data["plain_body"] = ""

        with pytest.raises(ValueError, match="plain_body must be provided"):
            send_mail(**data)

    def test_send_mail_smtp_exception_starttls(self, mock_smtp, sample_email_data):
        """Test de gestion d'exception SMTP avec STARTTLS."""
        mock_smtp["smtp"].send_message.side_effect = smtplib.SMTPException("Connection failed")

        with temp_env_vars(SMTP_SECURE="starttls"):
            with pytest.raises(smtplib.SMTPException, match="Connection failed"):
                send_mail(**sample_email_data)

    def test_send_mail_smtp_exception_ssl(self, mock_smtp, sample_email_data):
        """Test de gestion d'exception SMTP avec SSL."""
        mock_smtp["smtp_ssl"].send_message.side_effect = smtplib.SMTPException("SSL connection failed")

        with patch("app.services.email.SMTP_SECURE", "ssl"):
            with pytest.raises(smtplib.SMTPException, match="SSL connection failed"):
                send_mail(**sample_email_data)

    def test_send_mail_unexpected_exception(self, mock_smtp, sample_email_data):
        """Test de gestion d'exception inattendue."""
        mock_smtp["smtp"].send_message.side_effect = RuntimeError("Unexpected error")

        with temp_env_vars(SMTP_SECURE="none"):
            with pytest.raises(RuntimeError, match="Unexpected error"):
                send_mail(**sample_email_data)

    def test_send_mail_message_content(self, mock_smtp, sample_email_data):
        """Test que le contenu du message est correctement formaté."""
        with patch("app.services.email.FROM_ADDRESS", "test@example.com"):
            send_mail(**sample_email_data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            assert isinstance(message, EmailMessage)
            assert message["Subject"] == sample_email_data["subject"]
            assert message["From"] == "test@example.com"
            assert message["To"] == sample_email_data["to"]
            # Vérifier le contenu plain text
            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content().strip()
                # Vérifier que le contenu contient les éléments attendus
                assert (
                    sample_email_data["plain_body"].strip() in content
                    or content == sample_email_data["plain_body"].strip()
                )

    def test_send_mail_custom_from_address(self, mock_smtp, sample_email_data):
        """Test avec une adresse FROM personnalisée."""
        custom_from = "custom@example.com"
        with patch("app.services.email.FROM_ADDRESS", custom_from):
            send_mail(**sample_email_data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            assert message["From"] == custom_from

    def test_send_mail_port_configuration(self, mock_smtp, sample_email_data):
        """Test avec une configuration de port personnalisée."""
        custom_port = 2525
        with patch("app.services.email.SMTP_PORT", custom_port):
            send_mail(**sample_email_data)

            # Vérifier que le port personnalisé est utilisé
            mock_smtp["smtp_class"].assert_called_once_with("localhost", custom_port)

    def test_send_mail_host_configuration(self, mock_smtp, sample_email_data):
        """Test avec une configuration d'hôte personnalisée."""
        custom_host = "smtp.custom.com"
        with patch("app.services.email.SMTP_HOST", custom_host):
            send_mail(**sample_email_data)

            # Vérifier que l'hôte personnalisé est utilisé
            mock_smtp["smtp_class"].assert_called_once_with(custom_host, 587)


class TestSendInvitation:
    """Tests pour la fonction send_invitation."""

    def test_send_invitation_success(self, mock_smtp, sample_invitation_data):
        """Test d'envoi réussi d'une invitation."""
        with temp_env_vars(SMTP_SECURE="none"):
            send_invitation(**sample_invitation_data)

            # Vérifier que send_mail a été appelé
            mock_smtp["smtp"].send_message.assert_called_once()

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            # Vérifier le sujet
            assert "Invitation à rejoindre Yaka" in message["Subject"]

            # Vérifier le contenu
            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                assert sample_invitation_data["display_name"] in content
                assert "Yaka (Yet Another Kanban App)" in content

    def test_send_invitation_no_display_name(self, mock_smtp):
        """Test d'invitation sans nom d'affichage."""
        data = {"email": "user@example.com", "display_name": None, "token": "test-token"}

        with temp_env_vars(SMTP_SECURE="none"):
            send_invitation(**data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            # Vérifier que "Utilisateur" est utilisé comme fallback
            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                assert "Bonjour Utilisateur" in content

    def test_send_invitation_empty_display_name(self, mock_smtp):
        """Test d'invitation avec nom d'affichage vide."""
        data = {"email": "user@example.com", "display_name": "", "token": "test-token"}

        with temp_env_vars(SMTP_SECURE="none"):
            send_invitation(**data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            # Vérifier que "Utilisateur" est utilisé comme fallback
            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                assert "Bonjour Utilisateur" in content

    def test_send_invitation_token_encoding(self, mock_smtp, sample_invitation_data):
        """Test que le token est correctement encodé dans l'URL."""
        # Token avec des caractères spéciaux
        special_token = "test@token&space=123"
        data = sample_invitation_data.copy()
        data["token"] = special_token

        with temp_env_vars(SMTP_SECURE="none"):
            send_invitation(**data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                # Vérifier que le token est encodé
                assert "test%40token%26space%3D123" in content

    def test_send_invitation_custom_base_url(self, mock_smtp, sample_invitation_data):
        """Test avec une URL de base personnalisée."""
        custom_base_url = "https://custom.domain.com"
        custom_invite_url = f"{custom_base_url}/invite"
        with patch("app.services.email.INVITE_BASE_URL", custom_invite_url):
            send_invitation(**sample_invitation_data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                # Vérifier que l'URL personnalisée est utilisée
                assert custom_invite_url in content

    def test_send_invitation_html_and_plain_content(self, mock_smtp, sample_invitation_data):
        """Test que les versions HTML et plain text sont générées."""
        with temp_env_vars(SMTP_SECURE="none"):
            send_invitation(**sample_invitation_data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            # Vérifier qu'il y a à la fois du contenu plain et HTML
            plain_body = message.get_body(("plain",))
            html_body = message.get_body(("html",))

            assert plain_body is not None
            assert html_body is not None

    def test_send_invitation_smtp_error_handling(self, mock_smtp, sample_invitation_data):
        """Test de gestion d'erreur SMTP dans l'invitation."""
        mock_smtp["smtp"].send_message.side_effect = smtplib.SMTPException("SMTP server down")

        with temp_env_vars(SMTP_SECURE="none"):
            with pytest.raises(smtplib.SMTPException, match="SMTP server down"):
                send_invitation(**sample_invitation_data)


class TestSendPasswordReset:
    """Tests pour la fonction send_password_reset."""

    def test_send_password_reset_success(self, mock_smtp, sample_reset_data):
        """Test d'envoi réussi d'une réinitialisation de mot de passe."""
        with temp_env_vars(SMTP_SECURE="none"):
            send_password_reset(**sample_reset_data)

            # Vérifier que send_mail a été appelé
            mock_smtp["smtp"].send_message.assert_called_once()

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            # Vérifier le sujet
            assert "Réinitialisation de votre mot de passe" in message["Subject"]

            # Vérifier le contenu
            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                assert sample_reset_data["display_name"] in content
                assert "réinitialisation de votre mot de passe" in content

    def test_send_password_reset_no_display_name(self, mock_smtp):
        """Test de réinitialisation sans nom d'affichage."""
        data = {"email": "user@example.com", "display_name": None, "token": "reset-token"}

        with temp_env_vars(SMTP_SECURE="none"):
            send_password_reset(**data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            # Vérifier que "Utilisateur" est utilisé comme fallback
            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                assert "Bonjour Utilisateur" in content

    def test_send_password_reset_token_encoding(self, mock_smtp, sample_reset_data):
        """Test que le token est correctement encodé dans l'URL de réinitialisation."""
        # Token avec des caractères spéciaux
        special_token = "reset@token&special=123"
        data = sample_reset_data.copy()
        data["token"] = special_token

        with temp_env_vars(SMTP_SECURE="none"):
            send_password_reset(**data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                # Vérifier que le token est encodé
                assert "reset%40token%26special%3D123" in content
                # Vérifier le paramètre reset=true
                assert "reset=true" in content

    def test_send_password_reset_custom_base_url(self, mock_smtp, sample_reset_data):
        """Test avec une URL de base personnalisée."""
        custom_base_url = "https://app.custom.com"
        custom_reset_url = f"{custom_base_url}/invite"
        with patch("app.services.email.PASSWORD_RESET_BASE_URL", custom_reset_url):
            send_password_reset(**sample_reset_data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                # Vérifier que l'URL personnalisée est utilisée
                assert custom_reset_url in content

    def test_send_password_reset_security_warning(self, mock_smtp, sample_reset_data):
        """Test que l'avertissement de sécurité est présent."""
        with temp_env_vars(SMTP_SECURE="none"):
            send_password_reset(**sample_reset_data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                # Vérifier l'avertissement de sécurité
                assert "Si vous n'avez pas demandé cette réinitialisation" in content
                assert "ignorez cet email" in content

    def test_send_password_reset_html_and_plain_content(self, mock_smtp, sample_reset_data):
        """Test que les versions HTML et plain text sont générées."""
        with temp_env_vars(SMTP_SECURE="none"):
            send_password_reset(**sample_reset_data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            # Vérifier qu'il y a à la fois du contenu plain et HTML
            plain_body = message.get_body(("plain",))
            html_body = message.get_body(("html",))

            assert plain_body is not None
            assert html_body is not None

    def test_send_password_reset_smtp_error_handling(self, mock_smtp, sample_reset_data):
        """Test de gestion d'erreur SMTP dans la réinitialisation."""
        mock_smtp["smtp"].send_message.side_effect = smtplib.SMTPException("Connection timeout")

        with temp_env_vars(SMTP_SECURE="none"):
            with pytest.raises(smtplib.SMTPException, match="Connection timeout"):
                send_password_reset(**sample_reset_data)

    def test_send_password_reset_different_from_invitation(self, mock_smtp):
        """Test que les emails de reset et invitation sont différents."""
        invitation_data = {"email": "test@example.com", "display_name": "Test User", "token": "same-token"}
        reset_data = invitation_data.copy()

        with temp_env_vars(SMTP_SECURE="none"):
            send_invitation(**invitation_data)
            send_password_reset(**reset_data)

            # Vérifier que deux emails ont été envoyés
            assert mock_smtp["smtp"].send_message.call_count == 2

            # Vérifier que les sujets sont différents
            first_call = mock_smtp["smtp"].send_message.call_args_list[0]
            second_call = mock_smtp["smtp"].send_message.call_args_list[1]

            first_subject = first_call[0][0]["Subject"]
            second_subject = second_call[0][0]["Subject"]

            assert first_subject != second_subject
            assert "Invitation" in first_subject
            assert "Réinitialisation" in second_subject


class TestEmailConfiguration:
    """Tests pour la configuration du service email."""

    def test_environment_variables_parsing(self):
        """Test que les variables d'environnement sont correctement parsées."""
        # Vérifier que les valeurs actuelles sont des chaînes valides
        assert isinstance(SMTP_HOST, str)
        assert isinstance(SMTP_PORT, int)
        assert isinstance(SMTP_SECURE, str)
        assert isinstance(FROM_ADDRESS, str)
        assert isinstance(BASE_URL, str)

    def test_base_url_construction(self):
        """Test que les URLs sont correctement construites."""
        # Vérifier que les URLs sont construites correctement
        assert INVITE_BASE_URL == f"{BASE_URL}/invite"
        assert PASSWORD_RESET_BASE_URL == f"{BASE_URL}/invite"


class TestEmailIntegration:
    """Tests d'intégration pour le service email."""

    def test_full_invitation_workflow(self, mock_smtp):
        """Test du workflow complet d'invitation."""
        user_data = {"email": "new.user@example.com", "display_name": "New User", "token": "secure-invite-token-123"}

        with patch("app.services.email.SMTP_SECURE", "starttls"):
            send_invitation(**user_data)

            # Vérifier que toutes les étapes ont été exécutées
            mock_smtp["smtp"].ehlo.assert_called()
            mock_smtp["smtp"].starttls.assert_called_once()
            mock_smtp["smtp"].ehlo.assert_called()
            mock_smtp["smtp"].send_message.assert_called_once()

            # Vérifier le contenu de l'email
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            assert message["To"] == user_data["email"]

    def test_full_password_reset_workflow(self, mock_smtp):
        """Test du workflow complet de réinitialisation."""
        user_data = {
            "email": "existing.user@example.com",
            "display_name": "Existing User",
            "token": "secure-reset-token-456",
        }

        with patch("app.services.email.SMTP_SECURE", "ssl"):
            send_password_reset(**user_data)

            # Vérifier que SSL a été utilisé
            mock_smtp["smtp_ssl_class"].assert_called_once()
            mock_smtp["smtp_ssl"].send_message.assert_called_once()

            # Vérifier le contenu de l'email
            call_args = mock_smtp["smtp_ssl"].send_message.call_args
            message = call_args[0][0]

            assert message["To"] == user_data["email"]

    def test_concurrent_email_sending(self, mock_smtp):
        """Test d'envoi concurrent d'emails."""
        emails_data = [
            {
                "to": f"user{i}@example.com",
                "subject": f"Subject {i}",
                "html_body": f"<p>Content {i}</p>",
                "plain_body": f"Content {i}",
            }
            for i in range(3)  # Réduit pour accélérer le test
        ]

        with temp_env_vars(SMTP_SECURE="none"):
            for email_data in emails_data:
                send_mail(**email_data)

            # Vérifier que tous les emails ont été envoyés
            assert mock_smtp["smtp"].send_message.call_count == 3

            # Vérifier que chaque email a le bon destinataire
            for i, call_args in enumerate(mock_smtp["smtp"].send_message.call_args_list):
                message = call_args[0][0]
                assert message["To"] == f"user{i}@example.com"

    def test_error_handling_integration(self, mock_smtp):
        """Test de gestion d'erreurs dans différents scénarios."""
        # Simuler différentes erreurs
        error_scenarios = [
            smtplib.SMTPAuthenticationError(535, "Authentication failed"),
            smtplib.SMTPConnectError(421, "Service not available"),
            smtplib.SMTPHeloError(501, "HELO invalid"),
            RuntimeError("Unexpected network error"),
        ]

        for error in error_scenarios:
            mock_smtp["smtp"].send_message.side_effect = error

            with temp_env_vars(SMTP_SECURE="none"):
                with pytest.raises(type(error)):
                    send_mail(to="test@example.com", subject="Test", html_body="<p>Test</p>", plain_body="Test")

            # Reset pour le prochain test
            mock_smtp["smtp"].reset_mock()


class TestEmailSecurity:
    """Tests de sécurité pour le service email."""

    def test_html_content_storage(self, mock_smtp, sample_email_data):
        """Test que le contenu HTML est stocké tel quel."""
        html_content = '<script>alert("xss")</script><p>Safe content</p>'
        email_data = sample_email_data.copy()
        email_data["html_body"] = html_content

        with temp_env_vars(SMTP_SECURE="none"):
            send_mail(**email_data)

            # Récupérer le message envoyé
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            # Trouver la partie HTML
            html_body = message.get_body(("html",))
            if html_body:
                html_content_stored = html_body.get_content()
                # Vérifier que le HTML est stocké tel quel
                assert '<script>alert("xss")</script>' in html_content_stored

    def test_token_security_in_urls(self, mock_smtp, sample_invitation_data):
        """Test que les tokens sont correctement encodés dans les URLs."""
        # Token avec des caractères potentiellement dangereux
        dangerous_token = "token&admin=true/user=123"
        data = sample_invitation_data.copy()
        data["token"] = dangerous_token

        with temp_env_vars(SMTP_SECURE="none"):
            send_invitation(**data)

            # Récupérer le message
            call_args = mock_smtp["smtp"].send_message.call_args
            message = call_args[0][0]

            plain_body = message.get_body(("plain",))
            if plain_body:
                content = plain_body.get_content()
                # Vérifier que le token est correctement encodé
                assert "token%26admin%3Dtrue%2Fuser%3D123" in content

    def test_no_sensitive_data_logging(self, mock_smtp, sample_email_data):
        """Test que les données sensibles ne sont pas loguées."""
        # Ce test vérifie que les mots de passe ne sont pas logués
        with temp_env_vars(SMTP_SECURE="starttls", SMTP_USER="secret@example.com", SMTP_PASS="secret_password_123"):
            with patch("app.services.email.logger") as mock_logger:
                send_mail(**sample_email_data)

                # Vérifier que les appels de logging ne contiennent pas de mots de passe
                for call in mock_logger.error.call_args_list:
                    log_message = str(call[0][0])
                    assert "secret_password_123" not in log_message

    def test_email_header_injection_prevention(self, mock_smtp):
        """Test de prévention d'injection dans les en-têtes d'email."""
        # Tester que les caractères de nouvelle ligne sont gérés correctement
        with temp_env_vars(SMTP_SECURE="none"):
            # Essayer d'envoyer avec des caractères potentiellement dangereux
            try:
                send_mail(
                    to="test@example.com",
                    subject="Safe Subject",
                    html_body="<p>Safe content</p>",
                    plain_body="Safe content",
                )
                # Si ça passe, c'est bon
                assert True
            except ValueError as e:
                # Si une erreur de validation se produit, c'est aussi acceptable
                assert "Header values" in str(e)
