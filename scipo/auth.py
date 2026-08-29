"""Inscription, connexion et déconnexion des étudiants."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from scipo import db
from scipo.models import User

auth = Blueprint("auth", __name__)


@auth.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        nom = request.form.get("nom_complet", "").strip()
        mot_de_passe = request.form.get("password", "")
        confirmation = request.form.get("password2", "")

        if "@" not in email or "." not in email:
            flash("Veuillez saisir une adresse email valide.", "danger")
        elif len(mot_de_passe) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
        elif mot_de_passe != confirmation:
            flash("Les deux mots de passe ne correspondent pas.", "danger")
        elif db.session.query(User).filter_by(email=email).first():
            flash("Un compte existe déjà avec cet email.", "warning")
        else:
            utilisateur = User(email=email, nom_complet=nom or None)
            utilisateur.set_password(mot_de_passe)
            db.session.add(utilisateur)
            db.session.commit()
            login_user(utilisateur)
            flash(f"Bienvenue sur SciPo UCAD, {nom or email} ! Votre compte est prêt. 🎓", "success")
            return redirect(url_for("main.index"))

    return render_template("auth/inscription.html")


@auth.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        mot_de_passe = request.form.get("password", "")
        utilisateur = db.session.query(User).filter_by(email=email).first()

        if utilisateur and utilisateur.check_password(mot_de_passe):
            login_user(utilisateur, remember=bool(request.form.get("remember")))
            flash("Connexion réussie. Bon travail ! 📚", "success")
            destination = request.args.get("next")
            if destination and destination.startswith("/"):
                return redirect(destination)
            return redirect(url_for("main.index"))

        flash("Email ou mot de passe incorrect.", "danger")

    return render_template("auth/connexion.html")


@auth.route("/deconnexion")
@login_required
def deconnexion():
    logout_user()
    flash("Vous êtes déconnecté. À bientôt ! 👋", "info")
    return redirect(url_for("main.index"))
