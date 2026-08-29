# SciPo UCAD 🎓

Plateforme web de ressources pédagogiques dédiée aux **étudiants en Science Politique
de l'Université Cheikh Anta Diop de Dakar (UCAD)**.

## ✨ Fonctionnalités

- **Cours** classés par niveau : Licence 1, Licence 2, Licence 3, Master 1
- **Travaux Dirigés** par niveau
- **Bibliothèque numérique** (documents et ressources numériques)
- **Œuvres** : livres, syllabus et articles de référence
- Comptes étudiants (inscription avec email personnel, connexion sécurisée)
- Téléchargement **réservé aux membres connectés**, avec compteur
- **Interface d'administration** : ajouter / modifier / supprimer les documents
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
├── scipo/
│   ├── __init__.py         # Fabrique de l'application
│   ├── models.py           # Modèles : User, Resource
│   ├── auth.py             # Inscription / connexion / déconnexion
│   ├── main.py             # Pages publiques + téléchargement
│   ├── admin.py            # Interface d'administration
│   ├── templates/          # Pages HTML (Jinja2)
│   └── static/css/         # Feuille de style du thème
├── instance/               # Base de données SQLite (auto)
└── uploads/                # Documents téléversés (auto)
```

## 🗺️ Idées pour la suite (feuille de route)

- [ ] Favoris / signets pour les étudiants
- [ ] Vérification de l'email à l'inscription
- [ ] Espace commentaires et notations des documents
- [ ] Statistiques détaillées pour l'administrateur
- [ ] Déploiement en ligne (Render, PythonAnywhere...)

---
Fait avec ❤️ pour la communauté Science Po de l'UCAD.
