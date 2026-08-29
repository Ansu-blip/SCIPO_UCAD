"""Fabrique de l'application SciPo UCAD (pattern application factory)."""
import os

from flask import Flask, render_template
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
    with db.engine.connect() as connexion:
        colonnes = {ligne[1] for ligne in connexion.exec_driver_sql("PRAGMA table_info(users)")}
    if "email_verifie" not in colonnes:
        with db.engine.connect() as connexion:
            # Les comptes créés avant cette fonctionnalité sont considérés comme vérifiés.
            connexion.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN email_verifie BOOLEAN NOT NULL DEFAULT 1")
            connexion.commit()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Dossiers nécessaires (base de données et documents téléversés)
    os.makedirs(app.config["DB_PATH"].parent, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

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

    # Création des tables + petites migrations
    with app.app_context():
        from scipo import models  # noqa: F401
        db.create_all()
        _mettre_a_jour_base()

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
