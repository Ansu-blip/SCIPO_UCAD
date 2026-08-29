"""Modèles de données : utilisateurs et documents."""
import os
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from scipo import db, login_manager

# Libellés français des catégories et des niveaux
CATEGORIES = {
    "cours": "Cours",
    "td": "Travaux Dirigés",
    "bibliotheque": "Bibliothèque numérique",
    "oeuvres": "Œuvres",
}

LEVELS = {
    "licence1": "Licence 1",
    "licence2": "Licence 2",
    "licence3": "Licence 3",
    "master1": "Master 1",
}

# Icônes Bootstrap selon l'extension : (icône, couleur)
ICONES = {
    ".pdf": ("bi-file-earmark-pdf", "danger"),
    ".doc": ("bi-file-earmark-word", "primary"),
    ".docx": ("bi-file-earmark-word", "primary"),
    ".ppt": ("bi-file-earmark-ppt", "warning"),
    ".pptx": ("bi-file-earmark-ppt", "warning"),
    ".txt": ("bi-file-earmark-text", "secondary"),
    ".epub": ("bi-book", "info"),
    ".zip": ("bi-file-zip", "secondary"),
}


def _maintenant():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """Étudiant ou administrateur du site."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    nom_complet = db.Column(db.String(120))
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=_maintenant)

    def set_password(self, mot_de_passe):
        self.password_hash = generate_password_hash(mot_de_passe)

    def check_password(self, mot_de_passe):
        return check_password_hash(self.password_hash, mot_de_passe)

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Resource(db.Model):
    """Document mis en ligne par l'administrateur (cours, TD, livre...)."""
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    auteur = db.Column(db.String(120), default="")
    categorie = db.Column(db.String(20), nullable=False, index=True)   # clé de CATEGORIES
    niveau = db.Column(db.String(20), index=True)                      # clé de LEVELS (vide = tous niveaux)
    nom_fichier = db.Column(db.String(255), nullable=False)            # nom sur le disque
    nom_original = db.Column(db.String(255), nullable=False)           # nom visible par l'étudiant
    telechargements = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=_maintenant)
    updated_at = db.Column(db.DateTime, default=_maintenant, onupdate=_maintenant)

    @property
    def categorie_nom(self):
        return CATEGORIES.get(self.categorie, self.categorie)

    @property
    def niveau_nom(self):
        return LEVELS.get(self.niveau, "Tous niveaux") if self.niveau else "Tous niveaux"

    @property
    def extension(self):
        return os.path.splitext(self.nom_original)[1].lower()

    @property
    def icone(self):
        return ICONES.get(self.extension, ("bi-file-earmark", "secondary"))

    def __repr__(self):
        return f"<Resource {self.titre!r}>"
