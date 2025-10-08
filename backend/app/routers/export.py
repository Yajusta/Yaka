"""Routeur pour l'export des cartes."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services import export_service
from ..utils.dependencies import get_current_active_user

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/")
async def export_cards(
    format: str = Query(..., description="Format d'export: 'csv' ou 'xlsx'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Exporte toutes les cartes non archivées au format CSV ou Excel.

    Accessible à tous les utilisateurs authentifiés (visiteur et plus).

    Args:
        format: Format d'export ('csv' ou 'xlsx')
        db: Session de base de données
        current_user: Utilisateur authentifié

    Returns:
        Fichier CSV ou Excel à télécharger
    """
    # Valider le format
    if format not in ["csv", "xlsx"]:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Format invalide. Utilisez 'csv' ou 'xlsx'."
        )

    # Générer le contenu selon le format
    if format == "csv":
        content = export_service.generate_csv_export(db)
        media_type = "text/csv"
    else:  # xlsx
        content = export_service.generate_excel_export(db)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Générer le nom de fichier
    filename = export_service.get_export_filename(format)

    # Retourner la réponse avec le fichier
    return StreamingResponse(
        iter([content]), media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
