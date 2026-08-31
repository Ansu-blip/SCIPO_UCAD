"""Fabrique de l'application SciPo UCAD (pattern application factory)."""
import os

from flask import Flask, current_app, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.connexion"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"


def _mettre_a_jour_base():
    """Petites migrations SQLite : ajoute les colonnes apparues après la v1.

    db.create_all() ne modifie pas les tables existantes : on ajoute donc
    manuellement les nouvelles colonnes aux anciennes bases de données.
    """
    colonnes_requises = {
        # Les comptes créés avant la vérification d'email sont considérés comme vérifiés.
        "email_verifie": "BOOLEAN NOT NULL DEFAULT 1",
        "niveau": "VARCHAR(20)",
        "otp_hash": "VARCHAR(256)",
        "otp_expiration": "DATETIME",
    }
    with db.engine.connect() as connexion:
        presentes = {ligne[1] for ligne in connexion.exec_driver_sql("PRAGMA table_info(users)")}
    for nom, definition in colonnes_requises.items():
        if nom not in presentes:
            with db.engine.connect() as connexion:
                connexion.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {nom} {definition}")
                connexion.commit()


def _creer_admin_initial():
    """Crée le premier administrateur au démarrage (utile pour la mise en ligne).

    Sur Render, il n'y a pas de console interactive : définissez les variables
    d'environnement SCIPO_ADMIN_EMAIL et SCIPO_ADMIN_MOT_DE_PASSE et le compte
    est créé automatiquement au premier lancement (email déjà vérifié). Le
    compte n'est jamais créé deux fois ni écrasé.
    """
    from scipo.models import User

    email = os.environ.get("SCIPO_ADMIN_EMAIL", "").strip().lower()
    mot_de_passe = os.environ.get("SCIPO_ADMIN_MOT_DE_PASSE", "")
    if not email or not mot_de_passe:
        return
    if "@" not in email or len(mot_de_passe) < 6:
        print("⚠️ SCIPO_ADMIN_EMAIL / SCIPO_ADMIN_MOT_DE_PASSE invalides : "
              "administrateur initial non créé.")
        return
    # L'administrateur créé automatiquement doit toujours accéder à /admin
    current_app.config["ADMIN_EMAILS"] = set(current_app.config["ADMIN_EMAILS"]) | {email}

    if db.session.query(User).filter_by(email=email).first() is None:
        administrateur = User(email=email, is_admin=True, email_verifie=True)
        administrateur.set_password(mot_de_passe)
        db.session.add(administrateur)
        db.session.commit()
        print(f"✅ Administrateur initial créé : {email}")
    else:
        print(f"ℹ️ Un compte existe déjà pour {email} : administrateur initial ignoré.")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Dossiers nécessaires (base de données et documents téléversés)
    os.makedirs(app.config["DB_PATH"].parent, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Derrière le proxy HTTPS de Render : URLs absolues en https et cookies sécurisés.
    # (Render définit automatiquement la variable d'environnement RENDER.)
    if os.environ.get("RENDER") or os.environ.get("SCIPO_PROXY_FIX") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
        app.config["SESSION_COOKIE_SECURE"] = True

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Blueprints
    from scipo.main import main
    from scipo.auth import auth
    from scipo.admin import admin

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin, url_prefix="/admin")

    # Création des tables + petites migrations + administrateur initial
    with app.app_context():
        from scipo import models  # noqa: F401
        db.create_all()
        _mettre_a_jour_base()
        _creer_admin_initial()

    # Pages d'erreur élégantes
    @app.errorhandler(403)
    def interdit(e):
        return render_template("erreurs.html", code=403,
                               message="Accès réservé à l'administrateur du site."), 403

    @app.errorhandler(404)
    def introuvable(e):
        return render_template("erreurs.html", code=404,
                               message="Oups ! Cette page n'existe pas ou a été déplacée."), 404

    @app.errorhandler(413)
    def trop_volumineux(e):
        return render_template("erreurs.html", code=413,
                               message="Fichier trop volumineux (maximum : 25 Mo)."), 413

    return app
