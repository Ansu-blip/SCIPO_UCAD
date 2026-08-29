import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Configuration centrale de l'application SciPo UCAD."""

    # Clé secrète : à remplacer par une valeur unique en production
    SECRET_KEY = os.environ.get("SCIPO_SECRET_KEY", "scipo-ucad-2026-change-moi-en-production")

    # Base de données SQLite (créée automatiquement)
    DB_PATH = BASE_DIR / "instance" / "scipo.db"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DB_PATH.as_posix()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Dossier où sont stockés les documents téléversés
    UPLOAD_FOLDER = BASE_DIR / "uploads"

    # Taille maximale d'un fichier : 25 Mo
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024

    # Types de fichiers acceptés
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "epub", "zip"}

    # Envoi des emails de vérification (SMTP). Sans configuration, le lien de
    # vérification est simplement affiché dans la console (mode développement).
    SMTP_HOTE = os.environ.get("SCIPO_SMTP_HOTE", "")
    SMTP_PORT = int(os.environ.get("SCIPO_SMTP_PORT", "587"))
    SMTP_UTILISATEUR = os.environ.get("SCIPO_SMTP_UTILISATEUR", "")
    SMTP_MOT_DE_PASSE = os.environ.get("SCIPO_SMTP_MOT_DE_PASSE", "")
    EMAIL_EXPEDITEUR = os.environ.get("SCIPO_EMAIL_EXPEDITEUR", "SciPo UCAD <no-reply@scipo-ucad.sn>")
