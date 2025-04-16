from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import PyPDF2
import os
from dotenv import load_dotenv
import json
from decimal import Decimal
from openai import AsyncOpenAI
import logging
import decimal
import pdf2image
import tempfile
from PIL import Image
import io
import base64
import asyncio

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
    vision_analysis: Optional[str] = Field(description="Analyse de l'image avec OpenAI Vision", default=None)

# Configuration du client OpenAI
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY n'est pas définie dans le fichier .env")
    
    client = AsyncOpenAI(
        api_key=api_key,
        timeout=30.0
    )
    logger.info("Client OpenAI configuré avec succès")
except Exception as e:
    logger.error(f"Erreur lors de la configuration du client OpenAI: {str(e)}")
    raise

async def transform_response(response_data: dict) -> dict:
    """Transforme la réponse de l'API Vision dans le format attendu."""
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

        # Formater l'analyse Vision
        vision_analysis = ""
        if "vision_analysis" in response_data:
            vision_data = response_data["vision_analysis"]
            vision_analysis = f"Orientation du document : {vision_data.get('orientation_document', 'Non spécifiée')}"

        # Construire le nouveau format
        transformed_data = {
            "type_bien": response_data.get("type_de_bien", "Non spécifié"),
            "surfaces": {
                "surface_totale": Decimal(str(response_data.get("surface_totale", 0))),
                "pieces": pieces
            },
            "caracteristiques": response_data.get("caracteristiques", []),
            "vision_analysis": vision_analysis
        }

        logger.debug(f"Données transformées: {transformed_data}")
        return transformed_data
    except Exception as e:
        logger.error(f"Erreur lors de la transformation des données: {str(e)}")
        raise

async def analyze_image_with_vision(image_bytes: bytes) -> dict:
    """Analyse une image avec OpenAI Vision pour extraire toutes les informations du plan."""
    try:
        logger.info("Début de l'analyse de l'image avec OpenAI Vision")
        
        # Créer le message pour OpenAI Vision
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analysez cette image de plan d'appartement ou de maison et extrayez toutes les informations suivantes :

                        1. Type de bien :
                        - Identifiez s'il s'agit d'un appartement ou d'une maison
                        - Si c'est un appartement :
                          * Cherchez la typologie (T2, T3, T4, etc.) qui est généralement indiquée sur le plan
                          * Identifiez l'étage (RDC, R+1, R+2, etc.) qui est indiqué sur le plan
                          * Retournez le type sous la forme "Appartement T3 - RDC" ou "Appartement T4 - R+1"
                        - Si c'est une maison, retournez simplement "Maison"
                        2. Surface totale en m²
                        3. Liste des pièces avec leurs surfaces en m²
                        4. Caractéristiques spéciales du bien :
                        - IMPORTANT : Les caractéristiques sont listées dans la légende en bas à droite du plan
                        - Cherchez les symboles et leurs significations : PL (Placard), Etg (Étagère), EV (Évier), Ch (Chaudière gaz)
                        - Si vous trouvez d'autres symboles dans la légende, ajoutez-les également avec leur signification
                        - Listez toutes les caractéristiques présentes dans le plan en vous basant sur ces symboles
                        5. Orientation :
                        - IMPORTANT : Cherchez la boussole/rose des vents sur le plan. C'est un cercle divisé en quatre parties avec la lettre "N" (Nord)
                        - Cette boussole se trouve généralement en haut à droite du plan
                        - La lettre "N" dans la boussole indique la direction du Nord
                        - Pour déterminer l'orientation du document :
                          * Si le "N" de la boussole est à droite du cercle, le document est orienté vers l'OUEST
                          * Si le "N" de la boussole est à gauche du cercle, le document est orienté vers l'EST
                          * Si le "N" de la boussole est en haut du cercle, le document est orienté vers le NORD
                          * Si le "N" de la boussole est en bas du cercle, le document est orienté vers le SUD
                        - ATTENTION : Ne pas confondre avec d'autres symboles ou flèches sur le plan
                        - ATTENTION : L'orientation à retourner est celle vers laquelle le document est orienté, PAS la direction du Nord

                        Retournez les informations au format JSON suivant :
                        {
                            "type_de_bien": "Appartement T3 - RDC/Appartement T4 - 1er étage/Maison",
                            "surface_totale": nombre,
                            "surface_entree": nombre,
                            "surface_sejour": nombre,
                            "surface_suite_parentale": nombre,
                            "surface_chambre2": nombre,
                            "surface_chambre3": nombre,
                            "surface_sdb": nombre,
                            "surface_wc": number,
                            "surface_dgt": number,
                            "surface_terrasse": number,
                            "caracteristiques": ["Placard dans [pièce]", "Étagère dans [pièce]", "Évier dans [pièce]", "Chaudière gaz dans [pièce]"],
                            "vision_analysis": {
                                "orientation_document": "Nord/Sud/Est/Ouest"
                            }
                        }

                        Règles strictes :
                        1. Utilisez des points (.) et non des virgules (,) pour les nombres décimaux
                        2. Toutes les surfaces doivent être en m²
                        3. Capturez toutes les pièces mentionnées dans le plan
                        4. Ne fusionnez pas les pièces, gardez-les séparées
                        5. Pour les pièces avec des notes (comme "dont 2.4m² SDE"), incluez la surface totale
                        6. Pour toute pièce supplémentaire non listée, ajoutez-la avec le préfixe "surface_" suivi du nom en minuscules avec des underscores
                        7. IMPORTANT : Pour les caractéristiques, précisez la pièce où se trouve chaque équipement (PL, Etg, EV, Ch)"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                        }
                    }
                ]
            }
        ]
        
        # Appeler l'API OpenAI Vision avec un timeout
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4.1",
                    messages=messages,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="L'analyse de l'image a pris trop de temps")
        
        # Extraire et parser la réponse JSON
        response_data = json.loads(response.choices[0].message.content)
        logger.info("Analyse Vision réussie")
        
        # Transformer la réponse dans le format attendu
        transformed_data = await transform_response(response_data)
        
        # Créer l'objet ExtractedData
        result = ExtractedData(**transformed_data)
        logger.info("Données structurées extraites avec succès")
        
        return result.dict()
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse Vision: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse Vision: {str(e)}")

@app.post("/extract", response_model=ExtractedData)
async def extract_pdf_data(file: UploadFile = File(...)):
    """
    Endpoint pour extraire les données structurées d'un PDF de plan.
    """
    try:
        logger.info(f"Requête reçue pour le fichier: {file.filename}")
        
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")

        # Lire le contenu du fichier une seule fois
        content = await file.read()
        
        # Créer un BytesIO pour PyPDF2
        pdf_stream = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        
        # Vérifier si le PDF est valide
        if len(pdf_reader.pages) == 0:
            raise HTTPException(status_code=400, detail="Le fichier PDF est vide ou corrompu")
        
        # Réinitialiser le stream pour la conversion en PNG
        pdf_stream.seek(0)
        
        # Créer un dossier temporaire pour stocker les fichiers
        with tempfile.TemporaryDirectory() as temp_dir:
            # Sauvegarder le fichier PDF temporairement
            temp_pdf_path = os.path.join(temp_dir, "temp.pdf")
            with open(temp_pdf_path, "wb") as temp_pdf:
                temp_pdf.write(content)
            
            # Convertir le PDF en image de manière asynchrone
            loop = asyncio.get_event_loop()
            images = await loop.run_in_executor(
                None,
                lambda: pdf2image.convert_from_path(temp_pdf_path, first_page=1, last_page=1)
            )
            
            # Convertir la première page en PNG
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            logger.info("Conversion PDF en PNG réussie")
            
            # Analyse Vision
            result = await analyze_image_with_vision(img_byte_arr)
            
            logger.info("Traitement terminé avec succès")
            return ExtractedData(**result)
            
    except Exception as e:
        logger.error(f"Erreur globale: {str(e)}")
        logger.error(f"Type d'erreur: {type(e).__name__}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
