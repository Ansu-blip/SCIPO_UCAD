"""Inscription, connexion (avec code OTP), déconnexion et vérification de l'email."""
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from scipo import db
from scipo.models import LEVELS, User

auth = Blueprint("auth", __name__)

# Durées de validité : 24 h pour un lien de vérification, 10 min pour un code OTP
JETON_MAX_AGE = 24 * 60 * 60
SALT_VERIFICATION = "scipo-verification-email"
DUREE_OTP = timedelta(minutes=10)
ESSAIS_OTP_MAX = 5


@auth.route("/inscription", methods=["GET", "POST"])
def inscription():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        nom = request.form.get("nom_complet", "").strip()
        mot_de_passe = request.form.get("password", "")
        confirmation = request.form.get("password2", "")
        niveau = request.form.get("niveau", "")

        if not email.endswith("@gmail.com") and not email.endswith("@googlemail.com"):
            flash("L'inscription se fait avec une adresse Gmail (@gmail.com).", "danger")
        elif len(mot_de_passe) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
        elif mot_de_passe != confirmation:
            flash("Les deux mots de passe ne correspondent pas.", "danger")
        elif niveau not in LEVELS:
            flash("Veuillez choisir votre niveau d'étude.", "danger")
        elif db.session.query(User).filter_by(email=email).first():
            flash("Un compte existe déjà avec cet email.", "warning")
        else:
            utilisateur = User(email=email, nom_complet=nom or None, niveau=niveau)
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
            flash(f"Bienvenue sur Science Po UCAD, {nom or email} ! {message_verification} 🎓", "success")
            return redirect(url_for("main.index"))

    return render_template("auth/inscription.html", niveaux=LEVELS)


@auth.route("/connexion", methods=["GET", "POST"])
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        mot_de_passe = request.form.get("password", "")
        utilisateur = db.session.query(User).filter_by(email=email).first()

        if utilisateur and utilisateur.check_password(mot_de_passe):
            if current_app.config.get("OTP_ACTIVE"):
                # Étape 2 : un code à 6 chiffres est envoyé par email (valable 10 min)
                code = _generer_otp(utilisateur)
                try:
                    _envoyer_otp(utilisateur, code)
                except Exception:
                    flash("Impossible d'envoyer le code par email. Réessayez dans un instant.", "danger")
                    return render_template("auth/connexion.html")
                session["otp_user_id"] = utilisateur.id
                session["otp_essais"] = 0
                session["otp_remember"] = bool(request.form.get("remember"))
                destination = request.args.get("next")
                if destination and destination.startswith("/"):
                    session["otp_next"] = destination
                return redirect(url_for("auth.connexion_otp"))

            login_user(utilisateur, remember=bool(request.form.get("remember")))
            flash("Connexion réussie. Bon travail ! 📚", "success")
            destination = request.args.get("next")
            if destination and destination.startswith("/"):
                return redirect(destination)
            return redirect(url_for("main.index"))

        flash("Email ou mot de passe incorrect.", "danger")

    return render_template("auth/connexion.html")


@auth.route("/connexion/otp", methods=["GET", "POST"])
def connexion_otp():
    utilisateur = db.session.get(User, session["otp_user_id"]) if session.get("otp_user_id") else None
    if utilisateur is None:
        return redirect(url_for("auth.connexion"))

    if request.method == "POST":
        essais = session.get("otp_essais", 0)
        if essais >= ESSAIS_OTP_MAX:
            _annuler_otp(utilisateur)
            session.pop("otp_user_id", None)
            session.pop("otp_essais", None)
            flash("Trop d'essais. Reconnectez-vous pour recevoir un nouveau code.", "danger")
            return redirect(url_for("auth.connexion"))

        if _otp_valide(utilisateur, request.form.get("code", "")):
            session.pop("otp_user_id", None)
            session.pop("otp_essais", None)
            login_user(utilisateur, remember=bool(session.pop("otp_remember", None)))
            destination = session.pop("otp_next", None)
            flash("Connexion réussie. Bon travail ! 📚", "success")
            if destination and destination.startswith("/"):
                return redirect(destination)
            return redirect(url_for("main.index"))

        session["otp_essais"] = essais + 1
        restantes = ESSAIS_OTP_MAX - (essais + 1)
        flash(f"Code invalide ou expiré. Il vous reste {restantes} tentative(s).", "danger")

    return render_template("auth/otp.html", email=utilisateur.email)


@auth.route("/connexion/otp/renvoyer", methods=["POST"])
def renvoyer_otp():
    utilisateur = db.session.get(User, session["otp_user_id"]) if session.get("otp_user_id") else None
    if utilisateur is None:
        return redirect(url_for("auth.connexion"))
    code = _generer_otp(utilisateur)
    try:
        _envoyer_otp(utilisateur, code)
        session["otp_essais"] = 0
        flash("Un nouveau code vient d'être envoyé à votre adresse email.", "success")
    except Exception:
        flash("Impossible d'envoyer le code par email. Réessayez dans un instant.", "danger")
    return redirect(url_for("auth.connexion_otp"))


@auth.route("/deconnexion")
@login_required
def deconnexion():
    for cle in ("otp_user_id", "otp_essais", "otp_remember", "otp_next"):
        session.pop(cle, None)
    logout_user()
    flash("Vous êtes déconnecté. À bientôt ! 👋", "info")
    return redirect(url_for("main.index"))


def lien_verification(email):
    """Construit le lien unique de vérification d'une adresse email (valable 24 h)."""
    serialiseur = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT_VERIFICATION)
    jeton = serialiseur.dumps(email)
    return url_for("auth.verifier_email", jeton=jeton, _external=True)


def _envoyer_email(destinataire, sujet, contenu):
    """Envoie un email via SMTP, ou l'affiche en console si aucun SMTP n'est configuré."""
    if not current_app.config["SMTP_HOTE"]:
        message = f"[Science Po UCAD - DEV] Email pour {destinataire} — {sujet}\n{contenu}"
        print(message)
        current_app.logger.info(message)
        return

    email = EmailMessage()
    email["From"] = current_app.config["EMAIL_EXPEDITEUR"]
    email["To"] = destinataire
    email["Subject"] = sujet
    email.set_content(contenu)
    with smtplib.SMTP(current_app.config["SMTP_HOTE"], current_app.config["SMTP_PORT"]) as serveur:
        serveur.starttls()
        serveur.login(current_app.config["SMTP_UTILISATEUR"], current_app.config["SMTP_MOT_DE_PASSE"])
        serveur.send_message(email)


def _envoyer_email_verification(utilisateur):
    """Envoie l'email de vérification (lien valable 24 h)."""
    lien = lien_verification(utilisateur.email)
    _envoyer_email(
        utilisateur.email,
        "Vérifiez votre adresse email — Science Po UCAD",
        f"Bonjour {utilisateur.nom_complet or ''}\n\n"
        "Bienvenue sur Science Po UCAD ! Pour activer votre compte, cliquez sur ce lien :\n"
        f"{lien}\n\n"
        "Ce lien est valable 24 heures. À bientôt sur la plateforme !\n"
        "— L'équipe Science Po UCAD",
    )


def _maintenant_naif():
    """Date/heure UTC courante, sans fuseau (format stocké par SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generer_otp(utilisateur):
    """Génère un code à 6 chiffres valable 10 minutes et le mémorise (haché).

    Retourne le code en clair : c'est lui qui est envoyé par email.
    """
    code = f"{secrets.randbelow(1_000_000):06d}"
    utilisateur.otp_hash = generate_password_hash(code)
    utilisateur.otp_expiration = _maintenant_naif() + DUREE_OTP
    db.session.commit()
    return code


def _otp_valide(utilisateur, code):
    """Vrai si le code saisi correspond et n'a pas expiré (10 minutes)."""
    if not code or not utilisateur.otp_hash or utilisateur.otp_expiration is None:
        return False
    if _maintenant_naif() > utilisateur.otp_expiration:
        return False
    return check_password_hash(utilisateur.otp_hash, code.strip())


def _annuler_otp(utilisateur):
    utilisateur.otp_hash = None
    utilisateur.otp_expiration = None
    db.session.commit()


def _envoyer_otp(utilisateur, code):
    """Envoie le code de connexion à 6 chiffres par email."""
    _envoyer_email(
        utilisateur.email,
        "Votre code de connexion — Science Po UCAD",
        f"Bonjour {utilisateur.nom_complet or utilisateur.email}\n\n"
        f"Votre code de connexion est : {code}\n\n"
        "Ce code est valable 10 minutes. Ne le partagez avec personne.\n"
        "Si vous n'êtes pas à l'origine de cette connexion, ignorez cet email.\n"
        "— Science Po UCAD",
    )


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
