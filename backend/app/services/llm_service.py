import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI
from sqlalchemy.orm import selectinload

from ..database import SessionLocal
from ..models.card import Card, CardPriority
from ..models.card_item import CardItem
from ..models.kanban_list import KanbanList
from ..models.label import Label
from ..models.response_model import ResponseModel
from ..models.user import User, UserStatus

# Charger les variables d'environnement depuis .env
load_dotenv(override=True)
DEFAULT_MODEL = "gpt-5-nano"


class LLMService:
    """
    Service pour l'analyse de transcripts via OpenAI ou Azure OpenAI.
    """

    def __init__(self, model: str = ""):
        """
        Initialise le service LLM avec le provider configuré (OpenAI ou Azure).

        Args:
            model: Nom du modèle à utiliser (optionnel)
        """
        self._init_openai(model)

    def _init_openai(self, model: str):
        """Initialise le service pour OpenAI standard."""
        # Vérifier la clé API OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Clé API OpenAI manquante. Veuillez définir OPENAI_API_KEY dans .env")

        # Utiliser le modèle fourni ou celui de l'environnement, ou la valeur par défaut
        self.model_name = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)

        # Initialiser le client OpenAI
        self.client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_API_BASE_URL", ""))

    def analyze_transcript(self, transcript: str, user_context: str, instructions: str = "") -> str:
        """
        Analyse un transcript de réunion et extrait les informations selon le modèle ResponseModel.

        Args:
            transcript: Le texte du transcript à analyser
            user_context: Contexte utilisateur au format JSON
            instructions: Instructions préformatées pour le LLM (optionnel)

        Returns:
            Un dictionnaire contenant les informations extraites au format JSON
        """
        try:
            # Construire les instructions pour le LLM
            if not instructions:
                instructions = self._build_instructions_from_model(user_context)

            return self._analyze_with_openai(transcript, instructions)

        except Exception as e:
            print(f"Erreur lors de l'analyse du transcript: {str(e)}")
            return "{}"

    def _analyze_with_openai(self, transcript: str, instructions: str) -> str:
        """Analyse avec OpenAI standard."""
        temp_param = os.getenv("MODEL_TEMPERATURE", None)
        temperature: Optional[float] = float(temp_param) if temp_param else None
        if not self.client:
            raise ValueError("Client OpenAI non initialisé. Assurez-vous que la clé API est définie.")

        completion = self._get_completion(transcript, instructions, temperature)

        # Extraire la réponse parsée
        message = completion.choices[0].message
        if message.parsed:
            return message.parsed.model_dump_json(indent=2)
        elif message.refusal:
            print(f"Refus du modèle: {message.refusal}")
            return "{}"
        else:
            print("Aucune réponse parsée disponible")
            return "{}"

    def _get_completion(self, transcript: str, instructions: str, temperature: Optional[float] = None) -> Any:

        args = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": f"DEMANDE UTILISATEUR :\n\n{transcript}",
                },
            ],
            "response_format": ResponseModel,
        }
        if temperature is not None:
            args["temperature"] = temperature

        try:
            completion = self.client.chat.completions.parse(**args)
        except BadRequestError as e:
            if e.param == "temperature":
                print("Le modèle ne supporte pas le paramètre 'temperature', réessai sans ce paramètre.")
                return self._get_completion(transcript, instructions, temperature=None)
            else:
                raise e
        return completion

    def _build_instructions_from_model(self, user_context: str) -> str:
        """
        Construit les instructions pour le LLM basées sur le modèle ResponseModel

        Args:
            user_context: Contexte utilisateur au format JSON

        Returns:
            Les instructions formatées pour le LLM
        """

        instructions = f"""
### CONTEXTE EXISTANT ###
Tu es un assistant de gestion de tâches intelligent. Voici les données actuelles de l'application :

1.  **Utilisateurs existants :**
```json
{get_users()}
```

2.  **Listes possibles :**
```json
{get_lists()}
```

Les "listes" peuvent être aussi appelées "statuts", "états", "colonnes" ou "étapes".

3.  **Priorités possibles :**
```json
{get_priorities()}
```
Les "priorités" peuvent être aussi appelées "niveaux de priorité" ou "importances".

4.  **Tâches déjà existantes (pour éviter les doublons et comprendre le contexte) :**
```json
{get_tasks()}
```

La "tâche" peut aussi être appelée "élément", "item", "carte", "chose à faire" ou "action".
Les éléments de la checklist peuvent aussi être appelés "sous-tâches", "étapes", "items", "subtasks" ou "actions".

5. **Libellés possibles :**
```json
{get_labels()}
```

Le "libellé" peut aussi être appelé "étiquette", "flag" ou "tag".

6. **Date et heure actuelles :** {datetime.now().strftime("%Y-%m-%d %H:%M")}

7. **Utilisateur actuel, qui fait la demande :**
```json
{user_context}
```

### INSTRUCTION ###
Ton rôle est d'analyser la "DEMANDE UTILISATEUR" ci-dessous. 
En te basant UNIQUEMENT sur les informations fournies dans le CONTEXTE EXISTANT, tu dois déduire :
- s'il faut mettre à jour une tâche existante
OU
- s'il faut créer une nouvelle tâche.

Dans les deux cas : 
- Tu dois extraire les informations nécessaires pour remplir les champs du format de sortie attendu.
- Essaye de voir s'il y a des libellés pertinents en fonction du contexte, mais sans en inventer. Ils sont factultatifs.
- Ne mets jamais 2 fois le même libellé.
- Ne mets jamais 2 fois le même élément dans la checklist.

Dans le cas d'une mise à jour: 
- Utilise l'ID de la tâche existante et ne modfie que les parties nécessaires (il ne faut pas modifier le titre ou la description si c'est pour mettre un titre ou une description équivalente).
- Ne modifie pas les champs qui ne sont pas mentionnés dans la demande utilisateur.
- Essaye de trouver la liste la plus appropriée pour la tâche modifiée en te basant sur les noms et les descriptions des liste. 
    Exemple: si la modification coche un élément de la checklist et qu'il existe une liste "tâches en cours", il faut aussi modifier la liste à laquelle la tâche est affectée.
Attention : n'invente jamais d'identifiants lorsque tu rajoutes un élément, mais laisse le vide. 

Dans le cas d'une création : 
- Si la description n'apporte pas d'information supplémentaire au titre de la tâche, garde la description vide.

Génère UN SEUL objet JSON représentant la tâche en respectant le format demandé.
        """
        return instructions


def get_lists() -> str:
    """Retourne les statuts possibles depuis la base de données."""
    db = SessionLocal()
    try:
        lists = db.query(KanbanList).order_by(KanbanList.order).all()
        result = [{"list_id": lst.id, "list_name": lst.name, "list_description": lst.description} for lst in lists]
        return json.dumps(result, ensure_ascii=False, indent=2)
    finally:
        db.close()


def get_users() -> str:
    """Retourne les utilisateurs actifs depuis la base de données."""
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.status != UserStatus.DELETED).all()
        result = [{"user_id": user.id, "user_name": user.display_name or user.email} for user in users]
        return json.dumps(result, ensure_ascii=False, indent=2)
    finally:
        db.close()


def get_tasks() -> str:
    """Retourne les tâches existantes depuis la base de données."""
    db = SessionLocal()
    try:
        # Utiliser selectinload pour charger les items et labels en une seule requête supplémentaire
        # au lieu d'une requête par carte (évite le N+1 problem)
        cards = (
            db.query(Card)
            .join(KanbanList)
            .options(selectinload(Card.items), selectinload(Card.labels), selectinload(Card.assignee))
            .filter(Card.is_archived == False)
            .all()
        )
        result = []
        for card in cards:
            # Construire la checklist à partir des card_items
            checklist = [
                {"item_id": item.id, "item_name": item.text, "is_done": item.is_done}
                for item in sorted(card.items, key=lambda x: x.position)
            ]

            # Construire la liste des labels
            labels = [{"label_id": label.id, "label_name": label.name} for label in card.labels]

            # Obtenir le nom de l'assignee
            assignee_name = None
            if card.assignee:
                assignee_name = card.assignee.display_name or card.assignee.email

            task = {
                "task_id": card.id,
                "title": card.title,
                "description": card.description,
                "list_id": card.list_id,
                "list_name": card.kanban_list.name,
                "priority": card.priority.value.lower(),
                "assignee_id": card.assignee_id,
                "assignee_name": assignee_name,
                "due_date": card.due_date.isoformat() if card.due_date else None,
                "checklist": checklist,
                "labels": labels,
            }
            result.append(task)
        return json.dumps(result, ensure_ascii=False, indent=2)
    finally:
        db.close()


def get_priorities() -> str:
    """Retourne les priorités possibles."""
    return f'["{CardPriority.LOW.value}", "{CardPriority.MEDIUM.value}", "{CardPriority.HIGH.value}"]'


def get_labels() -> str:
    """Retourne les libellés depuis la base de données."""
    db = SessionLocal()
    try:
        labels = db.query(Label).all()
        result = [
            {"label_id": label.id, "label_name": label.name, "label_description": label.description}
            for label in labels
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)
    finally:
        db.close()
