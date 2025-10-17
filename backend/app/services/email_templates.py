"""Email templates loader for invitation and password reset emails."""

from pathlib import Path


def _load_template(template_name: str) -> str:
    """Load a template file from the templates directory."""
    template_path = Path(__file__).parent / "templates" / template_name
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def get_invitation_html(display_name: str, invite_link: str, board_url: str) -> str:
    """Generate HTML for invitation email."""
    template = _load_template("invitation.html")
    return template.replace("{{DISPLAY_NAME}}", display_name) \
                   .replace("{{INVITE_LINK}}", invite_link) \
                   .replace("{{BOARD_URL}}", board_url)


def get_invitation_plain(display_name: str, invite_link: str, board_url: str) -> str:
    """Generate plain text for invitation email."""
    template = _load_template("invitation.txt")
    return template.replace("{{DISPLAY_NAME}}", display_name) \
                   .replace("{{INVITE_LINK}}", invite_link) \
                   .replace("{{BOARD_URL}}", board_url)


def get_password_reset_html(display_name: str, reset_link: str, board_url: str) -> str:
    """Generate HTML for password reset email."""
    template = _load_template("password_reset.html")
    return template.replace("{{DISPLAY_NAME}}", display_name) \
                   .replace("{{RESET_LINK}}", reset_link) \
                   .replace("{{BOARD_URL}}", board_url)


def get_password_reset_plain(display_name: str, reset_link: str, board_url: str) -> str:
    """Generate plain text for password reset email."""
    template = _load_template("password_reset.txt")
    return template.replace("{{DISPLAY_NAME}}", display_name) \
                   .replace("{{RESET_LINK}}", reset_link) \
                   .replace("{{BOARD_URL}}", board_url)

