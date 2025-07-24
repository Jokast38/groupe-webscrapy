# Projet WuxiaWorld Scraper & eBook Generator

## 📋 Membres du groupe
- [Nom du membre 1]
- [Nom du membre 2]
- [Nom du membre 3]

## 📖 Description du projet

Ce projet est un scraper avancé pour wuxiaworld.com qui permet de :
- Rechercher des livres par titre avec autocomplétion
- Scraper les chapitres de manière asynchrone et optimisée
- Générer des ebooks au format EPUB avec une structure complète
- Interface web moderne et intuitive
- Base de données pour stocker les données en temps réel
- Pipeline de traitement optimisé

## 🏗️ Structure du projet

```
groupe-webscrapy/
├── backend/
│   ├── app.py                 # API Flask
│   ├── database.py            # Configuration base de données
│   ├── models.py              # Modèles de données
│   └── requirements.txt       # Dépendances backend
├── scraper/
│   ├── wuxia_scraper/
│   │   ├── __init__.py
│   │   ├── spiders/
│   │   │   ├── __init__.py
│   │   │   └── wuxia_spider.py
│   │   ├── items.py           # Définition des items
│   │   ├── pipelines.py       # Pipeline de traitement
│   │   ├── settings.py        # Configuration Scrapy
│   │   └── middlewares.py     # Middlewares personnalisés
│   ├── epub_generator.py      # Générateur EPUB
│   ├── scrapy.cfg
│   └── requirements.txt       # Dépendances scraper
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── script.js
│   └── assets/
└── docker-compose.yml         # Configuration Docker

```

## 🚀 Instructions d'exécution

### Prérequis
- Python 3.8+
- PostgreSQL ou MongoDB
- Node.js (optionnel pour le développement frontend)

### 1. Installation des dépendances

#### Backend
```bash
cd backend
pip install -r requirements.txt
```

#### Scraper
```bash
cd scraper
pip install -r requirements.txt
```

### 2. Configuration de la base de données

1. Créer un cluster MongoDB (par exemple via MongoDB Atlas)
2. Configurer les variables d'environnement dans `.env`

### 3. Lancement des composants

#### Backend API
```bash
cd backend
python app.py
```

#### Interface Web
Ouvrir `frontend/index.html` dans un navigateur ou servir avec un serveur web local.

#### Scraper (manuel)
```bash
cd scraper
scrapy crawl wuxia -a search_query="titre_du_livre"
```

## 🔧 Configuration

Les paramètres de configuration se trouvent dans :
- `backend/.env` : Configuration base de données et API
- `scraper/wuxia_scraper/settings.py` : Configuration Scrapy

## 📚 Utilisation

1. Rechercher un livre via l'interface web
2. Sélectionner parmi les 3 propositions
3. Cliquer sur "Télécharger EPUB"
4. Le système lance automatiquement le scraping et génère l'ebook

## ⚡ Optimisations

- Requêtes asynchrones pour le scraping
- Mise en cache des résultats
- Pipeline de traitement en temps réel
- Gestion des erreurs et retry automatique
- Rate limiting pour éviter les blocages
