"""Inscription, connexion, déconnexion et vérification de l'email."""
import smtplib
from email.message import EmailMessage

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from scipo import db
from scipo.models import User

auth = Blueprint("auth", __name__)

# Durée de validité d'un lien de vérification : 24 heures
JETON_MAX_AGE = 24 * 60 * 60
SALT_VERIFICATION = "scipo-verification-email"


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
            try:
                _envoyer_email_verification(utilisateur)
                message_verification = "Un lien de vérification vient d'être envoyé à votre adresse email."
            except Exception:
                message_verification = ("L'email de vérification n'a pas pu être envoyé : utilisez "
                                        "le bouton « Renvoyer le lien » en haut du site.")
            login_user(utilisateur)
            flash(f"Bienvenue sur SciPo UCAD, {nom or email} ! {message_verification} 🎓", "success")
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


def lien_verification(email):
    """Construit le lien unique de vérification d'une adresse email (valable 24 h)."""
    serialiseur = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT_VERIFICATION)
    jeton = serialiseur.dumps(email)
    return url_for("auth.verifier_email", jeton=jeton, _external=True)


def _envoyer_email_verification(utilisateur):
    """Envoie l'email de vérification par SMTP, ou affiche le lien en console."""
    lien = lien_verification(utilisateur.email)

    if not current_app.config["SMTP_HOTE"]:
        # Aucun serveur SMTP configuré : mode développement, le lien s'affiche en console.
        message = f"[SciPo UCAD - DEV] Lien de vérification pour {utilisateur.email} : {lien}"
        print(message)
        current_app.logger.info(message)
        return

    email = EmailMessage()
    email["From"] = current_app.config["EMAIL_EXPEDITEUR"]
    email["To"] = utilisateur.email
    email["Subject"] = "Vérifiez votre adresse email — SciPo UCAD"
    email.set_content(
        f"Bonjour {utilisateur.nom_complet or ''}\n\n"
        "Bienvenue sur SciPo UCAD ! Pour activer votre compte, cliquez sur ce lien :\n"
        f"{lien}\n\n"
        "Ce lien est valable 24 heures. À bientôt sur la plateforme !\n"
        "— L'équipe SciPo UCAD"
    )
    with smtplib.SMTP(current_app.config["SMTP_HOTE"], current_app.config["SMTP_PORT"]) as serveur:
        serveur.starttls()
        serveur.login(current_app.config["SMTP_UTILISATEUR"], current_app.config["SMTP_MOT_DE_PASSE"])
        serveur.send_message(email)


@auth.route("/verification/<jeton>")
def verifier_email(jeton):
    """Vérifie l'adresse email d'un étudiant depuis le lien reçu par email."""
    try:
        email = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"], salt=SALT_VERIFICATION
        ).loads(jeton, max_age=JETON_MAX_AGE)
    except SignatureExpired:
        flash("Ce lien de vérification a expiré. Connectez-vous pour en recevoir un nouveau.", "warning")
        return redirect(url_for("auth.connexion"))
    except BadSignature:
        flash("Ce lien de vérification est invalide.", "danger")
        return redirect(url_for("main.index"))

    utilisateur = db.session.query(User).filter_by(email=email).first()
    if utilisateur is None:
        flash("Ce lien de vérification est invalide.", "danger")
    elif utilisateur.email_verifie:
        flash("Votre adresse email est déjà vérifiée. Tout est en ordre ! ✅", "info")
    else:
        utilisateur.email_verifie = True
        db.session.commit()
        flash("Merci ! Votre adresse email est vérifiée. 🎉", "success")
    return redirect(url_for("main.index"))


@auth.route("/verification/renvoyer", methods=["POST"])
@login_required
def renvoyer_verification():
    """Renvoie un lien de vérification au membre connecté."""
    if current_user.email_verifie:
        flash("Votre adresse email est déjà vérifiée.", "info")
    else:
        try:
            _envoyer_email_verification(current_user)
            flash(f"Un nouveau lien de vérification a été envoyé à {current_user.email}.", "success")
        except Exception:
            flash("L'envoi de l'email a échoué. Réessayez dans quelques minutes.", "danger")
    return redirect(url_for("main.index"))
