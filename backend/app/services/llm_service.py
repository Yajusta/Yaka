import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI
from sqlalchemy.orm import selectinload

from ..models.card import Card, CardPriority
from ..models.card_item import CardItem
from ..models.global_dictionary import GlobalDictionary
from ..models.kanban_list import KanbanList
from ..models.label import Label
from ..models.personal_dictionary import PersonalDictionary
from ..models.response_model import (
    AutoIntentResponse,
    CardEditResponse,
    CardFilterResponse,
    ResponseType,
    UnknownResponse,
)
from ..models.user import User, UserStatus
from ..multi_database import get_board_db

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

    def analyze_transcript(
        self,
        transcript: str,
        user_context: str,
        instructions: str = "",
        response_type: ResponseType = ResponseType.AUTO_INTENT,
    ) -> str:
        """
        Analyse un transcript de réunion et extrait les informations selon le modèle spécifié.

        Args:
            transcript: Le texte du transcript à analyser
            user_context: Contexte utilisateur au format JSON
            instructions: Instructions préformatées pour le LLM (optionnel)
            response_type: Type de réponse attendu ("card_update", "filter", ou "auto")

        Returns:
            Un dictionnaire contenant les informations extraites au format JSON
        """
        try:
            if response_type == ResponseType.AUTO_INTENT:
                intent_instructions = self._build_intent_analysis_instructions(user_context)
                intent_response: AutoIntentResponse = AutoIntentResponse.model_validate_json(
                    self._analyze_with_openai(transcript, intent_instructions, response_type)
                )
                if intent_response.action == ResponseType.CARD_UPDATE:
                    response_type = ResponseType.CARD_UPDATE
                elif intent_response.action == ResponseType.FILTER:
                    response_type = ResponseType.FILTER
                else:
                    unknown_response = UnknownResponse()
                    return unknown_response.model_dump_json(indent=2)

            # Construire les instructions pour le LLM selon le type de réponse
            if not instructions:
                if response_type == ResponseType.FILTER:
                    instructions = self._build_filter_instructions(user_context)
                if response_type == ResponseType.CARD_UPDATE:
                    instructions = self._build_card_edit_instructions(user_context)

            return self._analyze_with_openai(transcript, instructions, response_type)

        except Exception as e:
            print(f"Erreur lors de l'analyse du transcript: {str(e)}")
            return "{}"

    def _analyze_with_openai(
        self, transcript: str, instructions: str, response_type: ResponseType = ResponseType.AUTO_INTENT
    ) -> str:
        """Analyse avec OpenAI standard."""
        temp_param = os.getenv("MODEL_TEMPERATURE", None)
        temperature: Optional[float] = float(temp_param) if temp_param else None
        if not self.client:
            raise ValueError("Client OpenAI non initialisé. Assurez-vous que la clé API est définie.")

        completion = self._get_completion(transcript, instructions, temperature, response_type)

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

    def _get_completion(
        self,
        transcript: str,
        instructions: str,
        temperature: Optional[float] = None,
        response_type: ResponseType = ResponseType.AUTO_INTENT,
    ) -> Any:

        # Choisir le modèle de réponse selon le type
        response_format = AutoIntentResponse
        if response_type == ResponseType.FILTER:
            response_format = CardFilterResponse
        if response_type == ResponseType.CARD_UPDATE:
            response_format = CardEditResponse

        args = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": f"DEMANDE UTILISATEUR :\n\n{transcript}",
                },
            ],
            "response_format": response_format,
        }
        if temperature is not None:
            args["temperature"] = temperature

        try:
            completion = self.client.chat.completions.parse(**args)
        except BadRequestError as e:
            if e.param == "temperature":
                print("Le modèle ne supporte pas le paramètre 'temperature', réessai sans ce paramètre.")
                return self._get_completion(transcript, instructions, temperature=None, response_type=response_type)
            else:
                raise e
        return completion

    def _build_card_edit_instructions(self, user_context: str) -> str:
        """
        Construit les instructions pour le LLM basées sur le modèle CardEditResponse

        Args:
            user_context: Contexte utilisateur au format JSON

        Returns:
            Les instructions formatées pour le LLM
        """

        # Parse user context to extract user_id for view scope filtering
        user_dict = {}
        try:
            user_dict = json.loads(user_context) if user_context else {}
        except json.JSONDecodeError:
            user_dict = {}

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
{get_tasks(user_dict)}
```

La "tâche" peut aussi être appelée "élément", "item", "carte", "chose à faire" ou "action".
Les éléments de la checklist peuvent aussi être appelés "sous-tâches", "étapes", "items", "subtasks" ou "actions".

5. **Libellés possibles :**
```json
{get_labels()}
```

Le "libellé" peut aussi être appelé "étiquette", "flag" ou "tag".

6. **Vocabulaire spécifique (pour mieux comprendre le contexte et corriger les erreurs de transcription) :**
```json
{get_vocabulary(user_dict)}
```

7. **Date et heure actuelles :** {datetime.now().strftime("%Y-%m-%d %H:%M")}

8. **Utilisateur actuel, qui fait la demande :**
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
- Quand tu comprends qu'un élement de la demande correspond à un terme du dictionnaire, utilise le terme tel qu'il est écrit dans le dictionnaire.

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

    def _build_filter_instructions(self, user_context: str) -> str:
        """
        Construit les instructions pour le LLM basées sur le modèle CardFilterResponse

        Args:
            user_context: Contexte utilisateur au format JSON

        Returns:
            Les instructions formatées pour le LLM pour les filtres
        """

        # Parse user context to extract user_id for view scope filtering
        user_dict = {}
        try:
            user_dict = json.loads(user_context) if user_context else {}
        except json.JSONDecodeError:
            user_dict = {}

        instructions = f"""
### CONTEXTE EXISTANT ###
Tu es un assistant de gestion de tâches intelligent. Voici les données actuelles de l'application :

1.  **Tâches existantes :**
```json
{get_tasks(user_dict)}
```

La "tâche" peut aussi être appelée "élément", "item", "carte", "chose à faire" ou "action".

2. **Vocabulaire spécifique (pour mieux comprendre le contexte et corriger les erreurs de transcription) :**
```json
{get_vocabulary(user_dict)}
```

3. **Utilisateur actuel, qui fait la demande :**
```json
{user_context}
```

4. **Date et heure actuelles :** {datetime.now().strftime("%Y-%m-%d %H:%M")}

### INSTRUCTION ###
Ton rôle est d'analyser la "DEMANDE UTILISATEUR" ci-dessous.
Tu dois identifier toutes les tâches qui correspondent à la demande et retourner une liste avec les identifiants de ces tâches.

Exemple de demandes :
- "Montre-moi mes tâches haute priorité" → retourne les identifiants des tâches haute priorité
- "Toutes les tâches de Pierre" → retourne les identifiants des tâches de Pierre
- "Les cartes terminées" → retourne les identifiants des tâches terminées
- "Tâches avec le libellé 'urgent'" → retourne les identifiants des tâches avec le libellé 'urgent'
- "Ce qui est dû cette semaine" → retourne les identifiants des tâches dûes cette semaine
- "Cherche les tâches qui parlent de facturation" → retourne les identifiants des tâches qui parlent de facturation
- Combinaisons de critères

IMPORTANT :
- Analyse attentivement le titre, la description, les libellés, la priorité, l'assignee, la date d'échéance et le statut de chaque tâche
- Utilise le vocabulaire spécifique pour comprendre les termes techniques
- Sois très précis et exhaustif : si une tâche correspond au critère, inclus-la
- Pour les recherches textuelles, cherche dans le titre, la description ET dans les éléments de checklist
- Quand tu comprends qu'un élément correspond à un terme du dictionnaire, utilise le terme tel qu'il est écrit dans le dictionnaire

INSTRUCTIONS CRITIQUES POUR cards :

1. NE JAMAIS utiliser un tableau d'IDs directement (ex: [27, 31, 33])
2. TOUJOURS utiliser une liste d'objets, chaque objet contient l'ID d'une carte

EXEMPLES CORRECTS :
- 3 cartes (IDs: 27, 31, 33) → {{"cards": [{{"id": 27}}, {{"id": 31}}, {{"id": 33}}], "description": "..."}}
- 2 cartes (IDs: 5, 12) → {{"cards": [{{"id": 5}}, {{"id": 12}}], "description": "..."}}
- 1 carte (ID: 88) → {{"cards": [{{"id": 88}}], "description": "..."}}

STRUCTURE STRICTEMENT REQUISE :
- "cards" : liste d'objets avec clé "id" contenant l'identifiant de la carte
- "description" : résumé du filtre appliqué

Format final exact à utiliser :
```json
{{
  "cards": [{{"id": 27}}, {{"id": 31}}, {{"id": 33}}],
  "description": "Résumé concis du filtre"
}}
```
        """
        return instructions

    def _build_intent_analysis_instructions(self, user_context: str) -> str:
        """
        Construit les instructions pour analyser l'intention de l'utilisateur.

        Args:
            user_context: Contexte utilisateur au format JSON

        Returns:
            Les instructions formatées pour le LLM
        """
        # Parse user context
        instructions = f"""
### CONTEXTE EXISTANT ###
Tu es un assistant intelligent de gestion de tâches. Tu dois analyser l'intention de l'utilisateur pour déterminer s'il souhaite:
1. ÉDITER UNE CARTE (card_update) : créer une nouvelle tâche ou modifier une tâche existante
2. APPLIQUER UN FILTRE (filter) : rechercher et filtrer des cartes existantes

Exemples d'actions "card_update" (édition de carte) :
- "Crée une nouvelle tâche pour appeler Pierre demain"
- "Ajoute une checklist 'Préparer réunion' à la tâche 'Projet X'"
- "Modifie la priorité de ma tâche à 'urgent'"
- "Assigne cette tâche à Marie"
- "Change le statut de la tâche 'Facturation' à 'terminé'"
- "Ajoute une date d'échéance de demain à la tâche"
- "Marque l'élément 'Appeler fournisseur' comme terminé"
- "Il faut faire les courses et acheter du pain"

Exemples d'actions "filter" (filtre) :
- "Montre-moi mes tâches haute priorité"
- "Toutes les tâches de Pierre"
- "Les cartes terminées"
- "Tâches avec le libellé 'urgent'"
- "Ce qui est dû cette semaine"
- "Cherche les tâches qui parlent de facturation"
- "Affiche mes tâches assignées à moi"
- "Trouve les cartes dans la liste 'En cours'"

### INSTRUCTION ###
Analyse la demande ci-dessous et décide quelle est l'intention de l'utilisateur.

Règles importantes :
- Si la demande mentionne explicitement "cherche", "affiche", "montre", "filtre", ou "trouve" → c'est généralement un filtre ("FILTER")
- Si la demande parle de "créer", "ajouter", "modifier", "changer", "assigner", "marquer" → c'est généralement une édition de carte ("CARD_UPDATE")
- Si l'utilisateur demande des informations sur des tâches existantes → c'est un filtre ("FILTER")
- Si l'utilisateur veut créer ou modifier une tâche → c'est une édition de carte ("CARD_UPDATE")


Utilisateur actuel :
```json
{user_context}
```

Date et heure actuelles : {datetime.now().strftime("%Y-%m-%d %H:%M")}

Analyse la DEMANDE UTILISATEUR et décide de l'intention la plus probable.
        """
        return instructions


def get_lists() -> str:
    """Retourne les statuts possibles depuis la base de données."""
    with get_board_db() as db:
        lists = db.query(KanbanList).order_by(KanbanList.order).all()
        result = [{"list_id": lst.id, "list_name": lst.name, "list_description": lst.description} for lst in lists]
        return json.dumps(result, ensure_ascii=False, indent=2)


def get_users() -> str:
    """Retourne les utilisateurs actifs depuis la base de données."""
    with get_board_db() as db:
        users = db.query(User).filter(User.status != UserStatus.DELETED).all()
        result = [{"user_id": user.id, "user_name": user.display_name or user.email} for user in users]
        return json.dumps(result, ensure_ascii=False, indent=2)


def get_tasks(user_context: Optional[Dict] = None) -> str:
    """Retourne les tâches existantes depuis la base de données."""
    with get_board_db() as db:
        # Build base query
        query = (
            db.query(Card)
            .join(KanbanList)
            .options(selectinload(Card.items), selectinload(Card.labels), selectinload(Card.assignee))
            .filter(Card.is_archived == False)
        )

        # Apply view scope filtering if user context is provided
        if user_context and "user_id" in user_context:
            user_id = user_context["user_id"]
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # Import here to avoid circular imports
                from . import card as card_service

                query = card_service.apply_view_scope_filter(query, user)

        cards = query.all()
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


def get_priorities() -> str:
    """Retourne les priorités possibles."""
    return f'["{CardPriority.LOW.value}", "{CardPriority.MEDIUM.value}", "{CardPriority.HIGH.value}"]'


def get_labels() -> str:
    """Retourne les libellés depuis la base de données."""
    with get_board_db() as db:
        labels = db.query(Label).all()
        result = [
            {"label_id": label.id, "label_name": label.name, "label_description": label.description}
            for label in labels
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)


def get_vocabulary(user_context: Optional[Dict] = None) -> str:
    """Retourne le vocabulaire combiné (global + personnel de l'utilisateur)."""
    with get_board_db() as db:
        # Get global dictionary entries
        global_entries = db.query(GlobalDictionary).all()
        result = [{"term": entry.term, "definition": entry.definition} for entry in global_entries]

        # Get personal dictionary entries if user context is provided
        if user_context and "user_id" in user_context:
            user_id = user_context["user_id"]
            personal_entries = db.query(PersonalDictionary).filter(PersonalDictionary.user_id == user_id).all()
            result.extend([{"term": entry.term, "definition": entry.definition} for entry in personal_entries])

        return json.dumps(result, ensure_ascii=False, indent=2)
