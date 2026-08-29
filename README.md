# SciPo UCAD 🎓

Plateforme web de ressources pédagogiques dédiée aux **étudiants en Science Politique
de l'Université Cheikh Anta Diop de Dakar (UCAD)**.

## ✨ Fonctionnalités

- **Cours** classés par niveau : Licence 1, Licence 2, Licence 3, Master 1
- **Travaux Dirigés** par niveau
- **Bibliothèque numérique** (documents et ressources numériques)
- **Œuvres** : livres, syllabus et articles de référence
- Comptes étudiants (inscription avec email personnel, connexion sécurisée)
- **Vérification de l'email** à l'inscription (lien signé valable 24 h)
- Téléchargement **réservé aux membres connectés**, avec compteur
- **Favoris** ⭐ : chaque étudiant enregistre ses documents préférés
- **Avis et notes** : les étudiants notent les documents (1 à 5 étoiles) et laissent un commentaire
- **Interface d'administration** : ajouter / modifier / supprimer les documents, modérer les avis
- **Statistiques détaillées** : téléchargements, favoris, avis, top documents, derniers membres
- Recherche de documents, filtres par niveau, pages d'erreur élégantes
- Design académique responsive (bleu nuit & or), mobile friendly

## 🛠️ Technologies

| Composant | Technologie |
|---|---|
| Backend | Python + Flask |
| Base de données | SQLite (via Flask-SQLAlchemy) |
| Authentification | Flask-Login + hachage Werkzeug |
| Sécurité formulaires | Flask-WTF (CSRF) |
| Frontend | Bootstrap 5, Bootstrap Icons, Google Fonts |

## 🚀 Installation et lancement

```powershell
# 1. Créer l'environnement virtuel et installer les dépendances
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# 2. Créer votre compte administrateur (une seule fois)
.\venv\Scripts\python creer_admin.py

# 3. Lancer le site
.\venv\Scripts\python app.py
```

Puis ouvrir **http://127.0.0.1:5000** dans votre navigateur.
L'administration se trouve sur **http://127.0.0.1:5000/admin**.

## 📁 Structure du projet

```
SCIPO_UCAD/
├── app.py                  # Point d'entrée
├── config.py               # Configuration (base de données, uploads)
├── creer_admin.py          # Script de création du compte admin
├── requirements.txt        # Dépendances Python
├── render.yaml             # Blueprint de déploiement Render (un clic)
├── scipo/
│   ├── __init__.py         # Fabrique de l'application
│   ├── models.py           # Modèles : User, Resource, Favori, Commentaire
│   ├── auth.py             # Inscription / connexion / déconnexion
│   ├── main.py             # Pages publiques + téléchargement
│   ├── admin.py            # Interface d'administration
│   ├── templates/          # Pages HTML (Jinja2)
│   └── static/css/         # Feuille de style du thème
├── instance/               # Base de données SQLite (auto)
└── uploads/                # Documents téléversés (auto)
```

## ✉️ Vérification des emails (optionnel)

Par défaut (développement), le lien de vérification est affiché dans la console du serveur.
Pour envoyer réellement les emails, définissez ces variables d'environnement avant de lancer
le site (exemple avec Gmail, qui demande un « mot de passe d'application ») :

```powershell
$env:SCIPO_SMTP_HOTE = "smtp.gmail.com"
$env:SCIPO_SMTP_PORT = "587"
$env:SCIPO_SMTP_UTILISATEUR = "votre.adresse@gmail.com"
$env:SCIPO_SMTP_MOT_DE_PASSE = "mot-de-passe-d-application"
$env:SCIPO_EMAIL_EXPEDITEUR = "SciPo UCAD <votre.adresse@gmail.com>"
```

## 🚀 Mise en ligne

Le projet est prêt à être déployé. Deux options gratuites :

### Option A — PythonAnywhere (recommandée : disque persistant gratuit)

La base de données et les documents téléversés **restent en place** — idéal pour ce projet.

1. Créez un compte gratuit sur [pythonanywhere.com](https://www.pythonanywhere.com) :
   votre site sera accessible à l'adresse `votre-nom.pythonanywhere.com`.
2. Onglet **Consoles** → ouvrez une console **Bash**, puis :
   ```bash
   git clone https://github.com/votre-compte/SCIPO_UCAD.git
   cd SCIPO_UCAD
   mkvirtualenv scipo --python=python3.13
   pip install -r requirements.txt
   python creer_admin.py
   ```
3. Onglet **Web** → **Add a new web app** → *Manual configuration* → même version
   de Python que le virtualenv.
4. Section **Virtualenv** : `/home/votre-nom/.virtualenvs/scipo`
5. Section **Static files** : URL `/static/` → répertoire
   `/home/votre-nom/SCIPO_UCAD/scipo/static`
6. Cliquez sur le lien **WSGI configuration file** et remplacez son contenu par :
   ```python
   import os

   os.environ["SCIPO_SECRET_KEY"] = "une-longue-chaine-aleatoire-unique"
   os.environ["SCIPO_DATA_DIR"] = "/home/votre-nom/donnees-scipo"

   from app import app as application
   ```
7. Bouton vert **Reload** : le site est en ligne ! 🎉

> 💡 La clé secrète peut être générée avec `python -c "import secrets; print(secrets.token_hex(32))"`.
> Le plan gratuit de PythonAnywhere bloque l'envoi d'emails vers les serveurs SMTP
> non autorisés (smtp.gmail.com fait partie des serveurs autorisés).

### Option B — Render (blueprint prêt : `render.yaml`)

1. Poussez le projet sur GitHub, puis sur [render.com](https://render.com) :
   **New + → Blueprint** et sélectionnez le dépôt — le fichier `render.yaml` est
   détecté automatiquement.
2. Renseignez `SCIPO_ADMIN_EMAIL` et `SCIPO_ADMIN_MOT_DE_PASSE` quand Render le
   demande : le compte administrateur est **créé automatiquement au premier
   démarrage** (jamais dupliqué aux redémarrages suivants).
3. ⚠️ Sur le plan **gratuit** de Render, le disque est **éphémère** : la base de
   données et les documents téléversés sont réinitialisés à chaque redémarrage.
   Pour conserver les données, passez au plan *starter* et décommentez le bloc
   `disk` + la variable `SCIPO_DATA_DIR=/var/data` dans `render.yaml`.

## 🗺️ Idées pour la suite (feuille de route)

- [x] Favoris / signets pour les étudiants
- [x] Vérification de l'email à l'inscription
- [x] Espace commentaires et notations des documents
- [x] Statistiques détaillées pour l'administrateur
- [x] Mise en ligne — configuration et procédure prêtes (voir « 🚀 Mise en ligne »)

---
Fait avec ❤️ pour la communauté Science Po de l'UCAD.
