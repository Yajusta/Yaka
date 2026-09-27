"""Service pour l'export des cartes en CSV et Excel."""

import csv
import io
import re
from datetime import datetime
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font
from sqlalchemy.orm import Session, joinedload

from ..models import Card, CardItem, User
from .card import apply_card_access_filter


def get_cards_for_export(db: Session, user: Optional[User] = None) -> List[Card]:
    """
    Récupère toutes les cartes non archivées triées par position de liste puis position de carte.

    Args:
        db: Session de base de données
        user: Utilisateur dont le périmètre de vue filtre les cartes exportées
            (les admins exportent toutes les cartes)

    Returns:
        Liste des cartes triées
    """
    from ..models import KanbanList

    query = db.query(Card).filter(Card.is_archived.is_(False))
    if user is not None:
        query = apply_card_access_filter(query, user)

    cards = (
        query.options(
            joinedload(Card.kanban_list),
            joinedload(Card.items),
            joinedload(Card.labels),
            joinedload(Card.assignee),
        )
        .join(KanbanList, Card.list_id == KanbanList.id)
        .order_by(KanbanList.order, Card.position)
        .all()
    )

    return cards


def format_checklist(items: List[CardItem]) -> str:
    """
    Formate la checklist d'une carte.

    Args:
        items: Liste des éléments de checklist

    Returns:
        Chaîne formatée avec [ ] ou [x] et retours chariots
    """
    if not items:
        return ""

    # Trier par position
    sorted_items = sorted(items, key=lambda item: item.position)

    formatted_items = []
    for item in sorted_items:
        checkbox = "[x]" if item.is_done else "[ ]"
        formatted_items.append(f"{checkbox} {item.text}")

    return "\n".join(formatted_items)


def format_labels(card: Card) -> str:
    """
    Formate les étiquettes d'une carte.

    Args:
        card: Carte avec ses étiquettes

    Returns:
        Chaîne avec les étiquettes séparées par " + "
    """
    if not card.labels:
        return ""

    label_names = [label.name for label in card.labels]
    return " + ".join(label_names)


def format_due_date(due_date) -> str:
    """
    Formate la date d'échéance.

    Args:
        due_date: Date d'échéance

    Returns:
        Date au format YYYY-MM-DD ou chaîne vide
    """
    if due_date is None:
        return ""

    if isinstance(due_date, str):
        return due_date

    return due_date.strftime("%Y-%m-%d")


def format_priority(priority) -> str:
    """
    Formate la priorité.

    Args:
        priority: Priorité de la carte

    Returns:
        Nom de la priorité
    """
    if priority is None:
        return ""

    if hasattr(priority, "value"):
        return priority.value

    return str(priority)


# Caractères qui font interpréter une cellule comme formule par un tableur,
# y compris après des blancs de tête
FORMULA_CHARS = ("=", "+", "-", "@")
# Caractères de contrôle traités comme déclencheurs dès la première position
LEADING_CONTROL_CHARS = ("\t", "\r")
FORMULA_TRIGGER_CHARS = FORMULA_CHARS + LEADING_CONTROL_CHARS


def neutralize_formula(text: str) -> str:
    """
    Neutralise l'injection de formules (CSV/Excel) en préfixant d'une apostrophe
    toute valeur commençant par une tabulation ou un retour chariot, ou dont le
    premier caractère non blanc est un caractère de formule.

    Args:
        text: Texte à neutraliser

    Returns:
        Texte préfixé d'une apostrophe si nécessaire, inchangé sinon
    """
    if text.startswith(LEADING_CONTROL_CHARS) or text.lstrip().startswith(
        FORMULA_CHARS
    ):
        return "'" + text
    return text


def neutralize_csv_field(text: str) -> str:
    """
    Neutralise les formules d'un champ CSV, y compris après chaque ";" : un tableur
    qui découpe sur ";" (séparateur par défaut des locales européennes, dont le
    français) peut faire démarrer une cellule au milieu du champ ("x;=HYPERLINK(...)"),
    quel que soit le guillemetage.

    Args:
        text: Texte du champ

    Returns:
        Texte dont chaque segment délimité par ";" est neutralisé
    """
    return ";".join(neutralize_formula(part) for part in text.split(";"))


def sanitize_csv_text(text: Optional[str]) -> str:
    """
    Nettoie le texte pour le format CSV en remplaçant les retours à la ligne par des espaces.

    Args:
        text: Texte à nettoyer

    Returns:
        Texte nettoyé
    """
    if not text:
        return ""

    # Remplacer tous les types de retours à la ligne par des espaces
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

    # Remplacer les espaces multiples par un seul espace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def write_text_cell(ws, row: int, column: int, value: Optional[str]) -> None:
    """
    Écrit une valeur texte dans une cellule Excel en neutralisant les formules
    et en forçant le type chaîne (jamais formule ni code d'erreur).
    Une valeur None (ex. display_name non renseigné) est écrite comme chaîne vide.
    Les caractères de contrôle interdits en XML sont retirés : openpyxl lèverait
    IllegalCharacterError et une seule carte ferait échouer tout l'export.
    """
    text = ILLEGAL_CHARACTERS_RE.sub("", value or "")
    cell = ws.cell(row=row, column=column, value=neutralize_formula(text))
    cell.data_type = "s"


def generate_csv_export(db: Session, user: Optional[User] = None) -> bytes:
    """
    Génère un fichier CSV avec toutes les cartes non archivées.

    Note: Pour le CSV, la checklist n'est pas exportée et les retours à la ligne
    sont remplacés par des espaces pour éviter les problèmes de formatage.

    Args:
        db: Session de base de données
        user: Utilisateur dont le périmètre de vue filtre les cartes exportées
            (les admins exportent toutes les cartes)

    Returns:
        Contenu du fichier CSV en bytes
    """
    cards = get_cards_for_export(db, user)

    # Créer un buffer en mémoire
    output = io.StringIO()
    # QUOTE_ALL : chaque champ est délimité sans ambiguïté pour les lecteurs CSV
    # conformes ; le découpage sur ";" est couvert par neutralize_csv_field
    writer = csv.writer(output, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)

    # En-têtes (sans la colonne Checklist)
    headers = [
        "Liste",
        "Titre",
        "Description",
        "Etiquettes",
        "Priorité",
        "Date d'échéance",
        "Assigné à",
    ]
    writer.writerow(headers)

    # Données
    for card in cards:
        row = [
            sanitize_csv_text(card.kanban_list.name),
            sanitize_csv_text(card.title),
            sanitize_csv_text(card.description or ""),
            sanitize_csv_text(format_labels(card)),
            format_priority(card.priority),
            format_due_date(card.due_date),
            sanitize_csv_text(card.assignee.display_name if card.assignee else ""),
        ]
        # Neutralisation des formules sur chaque cellule, y compris les colonnes futures
        writer.writerow([neutralize_csv_field(value) for value in row])

    # Récupérer le contenu et l'encoder en bytes
    csv_content = output.getvalue()
    output.close()

    return csv_content.encode("utf-8-sig")  # BOM pour Excel


def generate_excel_export(db: Session, user: Optional[User] = None) -> bytes:
    """
    Génère un fichier Excel avec toutes les cartes non archivées.

    Args:
        db: Session de base de données
        user: Utilisateur dont le périmètre de vue filtre les cartes exportées
            (les admins exportent toutes les cartes)

    Returns:
        Contenu du fichier Excel en bytes
    """
    cards = get_cards_for_export(db, user)

    # Créer un workbook
    wb = Workbook()
    ws = wb.active

    # Vérifier que ws n'est pas None (type guard pour pyright)
    if ws is None:
        raise RuntimeError("Failed to create worksheet")

    ws.title = "Export Tâches"

    # En-têtes avec style
    headers = [
        "Liste",
        "Titre",
        "Description",
        "Checklist",
        "Etiquettes",
        "Priorité",
        "Date d'échéance",
        "Assigné à",
    ]

    for col_num, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True)

    # Données
    for row_num, card in enumerate(cards, start=2):
        values = (
            card.kanban_list.name,
            card.title,
            card.description or "",
            format_checklist(card.items),
            format_labels(card),
            format_priority(card.priority),
            format_due_date(card.due_date),
            card.assignee.display_name if card.assignee else "",
        )
        for col_num, value in enumerate(values, start=1):
            write_text_cell(ws, row_num, col_num, value)

    # Ajuster la largeur des colonnes
    ws.column_dimensions["A"].width = 20  # Liste
    ws.column_dimensions["B"].width = 30  # Titre
    ws.column_dimensions["C"].width = 40  # Description
    ws.column_dimensions["D"].width = 30  # Checklist
    ws.column_dimensions["E"].width = 20  # Etiquettes
    ws.column_dimensions["F"].width = 12  # Priorité
    ws.column_dimensions["G"].width = 15  # Date d'échéance
    ws.column_dimensions["H"].width = 20  # Assigné à

    # Sauvegarder dans un buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return output.read()


def get_export_filename(format_type: str) -> str:
    """
    Génère le nom de fichier pour l'export.

    Args:
        format_type: Type de format ('csv' ou 'xlsx')

    Returns:
        Nom de fichier formaté
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"yaka_export_{timestamp}.{format_type}"
