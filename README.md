# LPPromotion PDF Analyzer

Application Blazor pour l'analyse de plans PDF avec intégration de l'API OpenAI.

## Prérequis

- .NET 8.0 SDK
- Docker et Docker Compose
- Visual Studio 2022

## Configuration

1. Créer un fichier `.env` à la racine du projet avec la clé API OpenAI :

```
OPENAI_API_KEY=votre_clé_api_ici
```

## Installation et lancement

### Backend (Docker)

1. Lancer le backend avec Docker Compose :

```bash
docker compose up --build
```

2. Pour arrêter le backend :

```bash
docker compose down
```

3. Pour relancer le backend :

```bash
docker compose up
```

Le backend sera accessible sur `http://localhost:8000`

### Frontend (Blazor)

1. Ouvrir le projet dans Visual Studio 2022
2. Lancer l'application avec F5 ou le bouton de démarrage

Le frontend sera accessible sur `http://localhost:7293` ou l'URL affichée dans Visual Studio

## Structure du projet

- `LPPromotion_PDF2/` : Application Blazor frontend
- `docker-compose.yml` : Configuration Docker pour le backend
- `plan/` : Dossier pour les fichiers PDF à analyser

## Fonctionnalités

- Upload de fichiers PDF
- Analyse automatique des plans via l'API OpenAI
- Export des résultats en CSV
