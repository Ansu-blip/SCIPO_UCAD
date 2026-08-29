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

    # Création des tables
    with app.app_context():
        from scipo import models  # noqa: F401
        db.create_all()

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
