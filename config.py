import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Dossier des données persistantes (base de données + documents téléversés).
# En développement : simplement le dossier du projet. En production (Render,
# PythonAnywhere…), définissez SCIPO_DATA_DIR pour pointer vers un disque
# persistant (ex. /var/data) — sinon les données sont perdues au redémarrage.
_dossier_donnees = os.environ.get("SCIPO_DATA_DIR", "").strip()
DATA_DIR = Path(_dossier_donnees).resolve() if _dossier_donnees else BASE_DIR


class Config:
    """Configuration centrale de l'application SciPo UCAD."""

    # Clé secrète : à remplacer par une valeur unique en production
    SECRET_KEY = os.environ.get("SCIPO_SECRET_KEY", "scipo-ucad-2026-change-moi-en-production")

    # Base de données SQLite (créée automatiquement)
    DB_PATH = DATA_DIR / "instance" / "scipo.db"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DB_PATH.as_posix()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Dossier où sont stockés les documents téléversés
    UPLOAD_FOLDER = DATA_DIR / "uploads"

    # Taille maximale d'un fichier : 25 Mo
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024

    # Types de fichiers acceptés
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "epub", "zip"}

    # Comptes administrateurs autorisés (séparés par des virgules si plusieurs)
    ADMIN_EMAILS = set(filter(None, os.environ.get(
        "SCIPO_ADMIN_EMAILS", "ansoucamara668@gmail.com").replace(";", ",").split(",")))

    # Code OTP à la connexion : actif uniquement si l'envoi d'emails est configuré
    # (sans SMTP, le code ne pourrait pas être remis aux utilisateurs).
    OTP_ACTIVE = bool(os.environ.get("SCIPO_SMTP_HOTE", "")) \
        and os.environ.get("SCIPO_OTP_ACTIF", "1") != "0"

    # Envoi des emails de vérification (SMTP). Sans configuration, le lien de
    # vérification est simplement affiché dans la console (mode développement).
    SMTP_HOTE = os.environ.get("SCIPO_SMTP_HOTE", "")
    SMTP_PORT = int(os.environ.get("SCIPO_SMTP_PORT", "587"))
    SMTP_UTILISATEUR = os.environ.get("SCIPO_SMTP_UTILISATEUR", "")
    SMTP_MOT_DE_PASSE = os.environ.get("SCIPO_SMTP_MOT_DE_PASSE", "")
    EMAIL_EXPEDITEUR = os.environ.get("SCIPO_EMAIL_EXPEDITEUR", "SciPo UCAD <no-reply@scipo-ucad.sn>")
