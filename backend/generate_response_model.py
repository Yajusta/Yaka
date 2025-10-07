import json
import os
import re
import sys
import tempfile
from pathlib import Path

from datamodel_code_generator import InputFileType, PythonVersion, generate
from unidecode import unidecode

OUTPUT_FILE = "autofill/response_model.py"


def normalize_field_name(name):
    """
    Normalise un nom de champ en supprimant les accents et caractères spéciaux.
    """
    # Supprimer les accents
    normalized = unidecode(name)
    # Convertir en snake_case si nécessaire
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", normalized)
    return normalized


def normalize_json_schema(schema):
    """
    Normalise récursivement tous les noms de champs dans un schéma JSON.
    """
    if isinstance(schema, dict):
        # Normaliser le titre si présent
        if "title" in schema:
            schema["title"] = unidecode(schema["title"])

        # Normaliser les propriétés
        if "properties" in schema:
            normalized_properties = {}
            for key, value in schema["properties"].items():
                normalized_key = normalize_field_name(key)
                normalized_properties[normalized_key] = normalize_json_schema(value)
            schema["properties"] = normalized_properties

        # Traiter les autres champs qui pourraient contenir des objets ou tableaux
        for key, value in schema.items():
            if key != "properties":  # Déjà traité
                schema[key] = normalize_json_schema(value)

    elif isinstance(schema, list):
        # Normaliser chaque élément de la liste
        for i, item in enumerate(schema):
            schema[i] = normalize_json_schema(item)

    return schema


def generate_response_model(input_file):
    """
    Génère un modèle Pydantic à partir d'un fichier JSON Schema.
    """
    # Vérifier si le fichier existe
    if not os.path.exists(input_file):
        print(f"Erreur: Le fichier '{input_file}' n'existe pas.")
        return False

    try:
        # Charger le schéma JSON
        with open(input_file, "r", encoding="utf-8") as f:
            json_schema = json.load(f)

        # Normaliser tous les noms de champs
        normalized_schema = normalize_json_schema(json_schema)

        # Créer un fichier temporaire pour le schéma normalisé
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as temp_file:
                json.dump(normalized_schema, temp_file)
                temp_file_path = temp_file.name

            # Générer le modèle Pydantic
            output_file = Path(OUTPUT_FILE)
            generate(
                input_=Path(temp_file_path),
                input_file_type=InputFileType.JsonSchema,
                output=output_file,
                class_name="ResponseModel",
                snake_case_field=True,
            )

            print(f"Modèle Pydantic généré avec succès dans '{output_file}'")
            return True
        finally:
            # Supprimer le fichier temporaire
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        print(f"Erreur lors de la génération du modèle: {str(e)}")
        return False


if __name__ == "__main__":
    # Demander le nom du fichier en entrée
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("Entrez le nom du fichier JSON Schema: ")

    # Générer le modèle
    generate_response_model(input_file)
