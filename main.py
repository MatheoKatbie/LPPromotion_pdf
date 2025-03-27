from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import PyPDF2
import os
from dotenv import load_dotenv
import json
from decimal import Decimal
from openai import OpenAI
import httpx
import logging
import decimal

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

app = FastAPI(title="PDF Extraction API")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À ajuster selon vos besoins de sécurité
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles de données pour la sortie structurée
class Piece(BaseModel):
    nom: str = Field(description="Nom de la pièce")
    surface: Decimal = Field(description="Surface de la pièce en m²")

class Surfaces(BaseModel):
    surface_totale: Decimal = Field(description="Surface totale du bien en m²")
    pieces: List[Piece] = Field(description="Liste des pièces avec leurs surfaces")

class ExtractedData(BaseModel):
    type_bien: str = Field(description="Type de bien (appartement, maison, etc.)")
    surfaces: Surfaces = Field(description="Informations sur les surfaces")
    caracteristiques: List[str] = Field(description="Liste des caractéristiques spéciales du bien")

# Configuration du client OpenAI pour Grok
try:
    api_key = os.getenv("GROK_API_KEY")
    if not api_key:
        raise ValueError("GROK_API_KEY n'est pas définie dans le fichier .env")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
        http_client=httpx.Client(
            base_url="https://api.x.ai/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )
    )
    logger.info("Client OpenAI configuré avec succès")
except Exception as e:
    logger.error(f"Erreur lors de la configuration du client OpenAI: {str(e)}")
    raise

async def extract_text_from_pdf(pdf_file: UploadFile) -> str:
    """Extrait le texte d'un fichier PDF."""
    try:
        logger.info(f"Début de l'extraction du texte du PDF: {pdf_file.filename}")
        pdf_reader = PyPDF2.PdfReader(pdf_file.file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        logger.info(f"Texte extrait avec succès, longueur: {len(text)} caractères")
        return text
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du texte: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erreur lors de l'extraction du texte: {str(e)}")

def transform_response(response_data: dict) -> dict:
    """Transforme la réponse de l'API Grok dans le format attendu."""
    try:
        # Créer la liste des pièces à partir des surfaces individuelles
        pieces = []
        
        # Mapping des noms de pièces connues
        piece_mapping = {
            "surface_entree": "Entrée",
            "surface_sejour": "Séjour / Cuisine",
            "surface_suite_parentale": "Suite parentale",
            "surface_chambre2": "Chambre 2",
            "surface_chambre3": "Chambre 3",
            "surface_sdb": "Salle de bain",
            "surface_wc": "WC",
            "surface_dgt": "Dégagement",
            "surface_terrasse": "Terrasse"
        }

        # Ajouter chaque pièce mappée si elle existe et n'a pas une surface de 0 ou None
        for key, nom in piece_mapping.items():
            if key in response_data and response_data[key] is not None:
                try:
                    surface = Decimal(str(response_data[key]))
                    if surface > 0:  # N'ajouter que si la surface est supérieure à 0
                        pieces.append({
                            "nom": nom,
                            "surface": surface
                        })
                except (ValueError, decimal.InvalidOperation):
                    logger.warning(f"Surface invalide pour {key}: {response_data[key]}")
                    continue

        # Ajouter les pièces supplémentaires qui ne sont pas dans le mapping
        for key, value in response_data.items():
            if key.startswith("surface_") and key not in piece_mapping and value is not None:
                try:
                    surface = Decimal(str(value))
                    if surface > 0:  # N'ajouter que si la surface est supérieure à 0
                        # Convertir le nom de la clé en nom lisible (ex: surface_bureau -> Bureau)
                        nom = key.replace("surface_", "").replace("_", " ").title()
                        pieces.append({
                            "nom": nom,
                            "surface": surface
                        })
                except (ValueError, decimal.InvalidOperation):
                    logger.warning(f"Surface invalide pour {key}: {value}")
                    continue

        # Construire le nouveau format
        transformed_data = {
            "type_bien": response_data.get("type_de_bien", "Non spécifié"),
            "surfaces": {
                "surface_totale": Decimal(str(response_data.get("surface_totale", 0))),
                "pieces": pieces
            },
            "caracteristiques": response_data.get("caracteristiques", [])
        }

        logger.debug(f"Données transformées: {transformed_data}")
        return transformed_data
    except Exception as e:
        logger.error(f"Erreur lors de la transformation des données: {str(e)}")
        raise

async def extract_structured_data(text: str) -> ExtractedData:
    """Utilise l'API Grok pour extraire les données structurées du texte."""
    system_prompt = """Tu es un expert en analyse de plans d'appartements. Ton rôle est d'analyser le texte fourni et d'extraire les informations pertinentes selon le schéma défini.
    
    Règles strictes :
    1. Utilise des points (.) et non des virgules (,) pour les nombres décimaux
    2. Les surfaces doivent être des nombres, pas des chaînes de caractères
    3. Assure-toi que toutes les surfaces sont en m²
    4. Les caractéristiques doivent être une liste de chaînes de caractères
    5. Le type de bien doit être une description claire (appartement, maison, etc.)
    6. IMPORTANT : Capture toutes les pièces mentionnées dans le texte
    7. Ne fusionne pas les pièces, garde-les séparées
    8. Pour les pièces avec des notes (comme "dont 2.4m² SDE"), inclure la surface totale
    9. Pour toute pièce supplémentaire non listée dans le format de base, ajoute-la avec le préfixe "surface_" suivi du nom en minuscules avec des underscores
    
    Format de sortie attendu :
    {
        "type_de_bien": "type de bien",
        "surface_totale": nombre,
        "surface_entree": nombre,
        "surface_sejour": nombre,
        "surface_suite_parentale": nombre,
        "surface_chambre2": nombre,
        "surface_chambre3": nombre,
        "surface_sdb": nombre,
        "surface_wc": nombre,
        "surface_dgt": nombre,
        "surface_terrasse": nombre,
        // Pièces supplémentaires si présentes dans le texte
        "surface_bureau": nombre,  // Exemple de pièce supplémentaire
        "surface_buanderie": nombre,  // Exemple de pièce supplémentaire
        "caracteristiques": ["liste des caractéristiques"]
    }"""

    try:
        logger.info("Début de l'appel à l'API Grok")
        completion = client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        logger.info("Réponse reçue de l'API Grok")

        # Parse la réponse JSON
        response_data = json.loads(completion.choices[0].message.content)
        logger.debug(f"Réponse JSON brute: {response_data}")
        
        # Transformer la réponse dans le format attendu
        transformed_data = transform_response(response_data)
        
        # Créer l'objet ExtractedData
        result = ExtractedData(**transformed_data)
        logger.info("Données structurées extraites avec succès")
        return result
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du texte: {str(e)}")
        logger.error(f"Type d'erreur: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse du texte: {str(e)}")

@app.post("/extract", response_model=ExtractedData)
async def extract_pdf_data(file: UploadFile = File(...)):
    """
    Endpoint pour extraire les données structurées d'un PDF de plan.
    """
    try:
        logger.info(f"Requête reçue pour le fichier: {file.filename}")
        
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")

        # Extraction du texte
        text = await extract_text_from_pdf(file)
        
        # Extraction des données structurées
        structured_data = await extract_structured_data(text)
        
        logger.info("Traitement terminé avec succès")
        return structured_data
    except Exception as e:
        logger.error(f"Erreur globale: {str(e)}")
        logger.error(f"Type d'erreur: {type(e).__name__}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 