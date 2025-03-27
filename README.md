# LPPromotion PDF Analyzer

Application Blazor pour l'analyse de plans PDF avec intégration de l'API Grok.

## Prérequis

- .NET 8.0 SDK
- Python 3.8 ou supérieur

## Configuration

1. Créer un fichier `.env` à la racine du projet avec la clé API Grok :

```
GROK_API_KEY=votre_clé_api_ici
```

## Installation et lancement

### Backend (API Python)

1. Créer un environnement virtuel Python :

```bash
python -m venv venv
```

2. Activer l'environnement virtuel :

- Windows :

```bash
.\venv\Scripts\activate
```

- Linux/Mac :

```bash
source venv/bin/activate
```

3. Installer les dépendances :

```bash
pip install -r requirements.txt
```

4. Lancer l'API Python :

```bash
python main.py
```

L'API sera accessible sur `http://localhost:8000`

### Frontend (Blazor)

Lancer avec Visual Studio 2022

## Structure du projet

- `LPPromotion_PDF2/` : Application Blazor frontend
- `main.py` : API Python backend
- `requirements.txt` : Dépendances Python
- `plan/` : Dossier pour les fichiers PDF à analyser

## Fonctionnalités

- Upload de fichiers PDF
- Analyse automatique des plans via l'API Grok
- Export des résultats en CSV
