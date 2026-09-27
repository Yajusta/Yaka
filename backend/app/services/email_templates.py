"""Email templates loader for invitation and password reset emails."""

import html
import re
from functools import lru_cache
from pathlib import Path

_PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


@lru_cache(maxsize=None)
def _load_template(template_name: str) -> str:
    """Load a template file from the templates directory (cached: files are static)."""
    template_path = Path(__file__).parent / "templates" / template_name
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def _render(template_name: str, values: dict[str, str]) -> str:
    """Substitute placeholders in a single pass (values are never re-interpreted).

    Values are HTML-escaped (quotes included) for .html templates only.
    """
    escape = template_name.endswith(".html")
    template = _load_template(template_name)

    def _replace(match: re.Match) -> str:
        value = values.get(match.group(1))
        if value is None:
            return match.group(0)
        return html.escape(value, quote=True) if escape else value

    return _PLACEHOLDER.sub(_replace, template)


def get_invitation_html(display_name: str, invite_link: str, board_url: str) -> str:
    """Generate HTML for invitation email."""
    return _render(
        "invitation.html",
        {
            "DISPLAY_NAME": display_name,
            "INVITE_LINK": invite_link,
            "BOARD_URL": board_url,
        },
    )


def get_invitation_plain(display_name: str, invite_link: str, board_url: str) -> str:
    """Generate plain text for invitation email."""
    return _render(
        "invitation.txt",
        {
            "DISPLAY_NAME": display_name,
            "INVITE_LINK": invite_link,
            "BOARD_URL": board_url,
        },
    )


def get_password_reset_html(display_name: str, reset_link: str, board_url: str) -> str:
    """Generate HTML for password reset email."""
    return _render(
        "password_reset.html",
        {
            "DISPLAY_NAME": display_name,
            "RESET_LINK": reset_link,
            "BOARD_URL": board_url,
        },
    )


def get_password_reset_plain(display_name: str, reset_link: str, board_url: str) -> str:
    """Generate plain text for password reset email."""
    return _render(
        "password_reset.txt",
        {
            "DISPLAY_NAME": display_name,
            "RESET_LINK": reset_link,
            "BOARD_URL": board_url,
        },
    )
