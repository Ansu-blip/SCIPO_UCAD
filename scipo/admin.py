"""Interface d'administration : ajouter, modifier et supprimer les documents."""
import os
import time
import uuid
from functools import wraps

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from scipo import db
from scipo.models import CATEGORIES, LEVELS, Commentaire, Favori, Resource, User

admin = Blueprint("admin", __name__)


def admin_requis(fonction):
    """Décorateur : accès réservé aux comptes administrateurs."""
    @wraps(fonction)
    def decorateur(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return fonction(*args, **kwargs)
    return decorateur


def _supprimer_fichier(chemin):
    """Supprime un fichier du disque en réessayant si Windows le verrouille encore."""
    for _ in range(5):
        try:
            os.remove(chemin)
            return True
        except PermissionError:
            time.sleep(0.2)
        except FileNotFoundError:
            return True
    return False


def _fichier_autorise(nom):
    return "." in nom and nom.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def _enregistrer_fichier(fichier):
    """Enregistre le fichier avec un nom unique et retourne ce nom."""
    nom_stocke = f"{uuid.uuid4().hex[:12]}_{secure_filename(fichier.filename)}"
    fichier.save(os.path.join(current_app.config["UPLOAD_FOLDER"], nom_stocke))
    return nom_stocke


def _lire_formulaire():
    niveau = request.form.get("niveau") or None
    return {
        "titre": request.form.get("titre", "").strip(),
        "description": request.form.get("description", "").strip(),
        "auteur": request.form.get("auteur", "").strip(),
        "categorie": request.form.get("categorie", ""),
        "niveau": niveau if niveau in LEVELS else None,
    }


@admin.route("/")
@login_required
@admin_requis
def tableau_de_bord():
    ressources = db.session.query(Resource).order_by(Resource.created_at.desc()).all()

    statistiques = {
        "documents": len(ressources),
        "membres": db.session.query(User).count(),
        "membres_verifies": db.session.query(User).filter_by(email_verifie=True).count(),
        "telechargements": sum(r.telechargements for r in ressources),
        "favoris": db.session.query(Favori).count(),
        "commentaires": db.session.query(Commentaire).count(),
        "note_moyenne": db.session.query(func.avg(Commentaire.note)).scalar(),
    }

    # Répartition des documents par rubrique (barres de progression)
    total = statistiques["documents"] or 1
    par_categorie = [{"nom": nom,
                      "nombre": sum(1 for r in ressources if r.categorie == cle),
                      "pourcentage": round(100 * sum(1 for r in ressources if r.categorie == cle) / total)}
                     for cle, nom in CATEGORIES.items()]

    top_documents = (db.session.query(Resource)
                     .order_by(Resource.telechargements.desc()).limit(5).all())
    derniers_membres = db.session.query(User).order_by(User.created_at.desc()).limit(5).all()
    derniers_commentaires = (db.session.query(Commentaire)
                             .order_by(Commentaire.created_at.desc()).limit(5).all())

    return render_template("admin/tableau_de_bord.html", ressources=ressources,
                           statistiques=statistiques, par_categorie=par_categorie,
                           top_documents=top_documents, derniers_membres=derniers_membres,
                           derniers_commentaires=derniers_commentaires)


@admin.route("/ressource/ajouter", methods=["GET", "POST"])
@login_required
@admin_requis
def ajouter():
    if request.method == "POST":
        donnees = _lire_formulaire()
        fichier = request.files.get("fichier")

        if not donnees["titre"] or donnees["categorie"] not in CATEGORIES:
            flash("Le titre et la catégorie sont obligatoires.", "danger")
        elif not fichier or fichier.filename == "":
            flash("Veuillez choisir un fichier à téléverser.", "danger")
        elif not _fichier_autorise(fichier.filename):
            flash("Type de fichier non autorisé (pdf, doc/docx, ppt/pptx, txt, epub, zip).", "danger")
        else:
            ressource = Resource(**donnees, nom_fichier=_enregistrer_fichier(fichier),
                                 nom_original=fichier.filename)
            db.session.add(ressource)
            db.session.commit()
            flash(f"Document « {donnees['titre']} » ajouté avec succès. ✅", "success")
            return redirect(url_for("admin.tableau_de_bord"))

    return render_template("admin/formulaire.html", r=None,
                           categories=CATEGORIES, niveaux=LEVELS)


@admin.route("/ressource/<int:res_id>/modifier", methods=["GET", "POST"])
@login_required
@admin_requis
def modifier(res_id):
    ressource = db.get_or_404(Resource, res_id)

    if request.method == "POST":
        donnees = _lire_formulaire()
        fichier = request.files.get("fichier")

        if not donnees["titre"] or donnees["categorie"] not in CATEGORIES:
            flash("Le titre et la catégorie sont obligatoires.", "danger")
        elif fichier and fichier.filename != "" and not _fichier_autorise(fichier.filename):
            flash("Type de fichier non autorisé (pdf, doc/docx, ppt/pptx, txt, epub, zip).", "danger")
        else:
            for cle, valeur in donnees.items():
                setattr(ressource, cle, valeur)
            if fichier and fichier.filename != "":
                ancien = os.path.join(current_app.config["UPLOAD_FOLDER"], ressource.nom_fichier)
                if not _supprimer_fichier(ancien):
                    flash("L'ancien fichier n'a pas pu être supprimé du disque (il restera sur le serveur).",
                          "warning")
                ressource.nom_fichier = _enregistrer_fichier(fichier)
                ressource.nom_original = fichier.filename
            db.session.commit()
            flash(f"Document « {ressource.titre} » modifié avec succès. ✅", "success")
            return redirect(url_for("admin.tableau_de_bord"))

    return render_template("admin/formulaire.html", r=ressource,
                           categories=CATEGORIES, niveaux=LEVELS)


@admin.route("/ressource/<int:res_id>/supprimer", methods=["POST"])
@login_required
@admin_requis
def supprimer(res_id):
    ressource = db.get_or_404(Resource, res_id)
    chemin = os.path.join(current_app.config["UPLOAD_FOLDER"], ressource.nom_fichier)
    if not _supprimer_fichier(chemin):
        flash("Le fichier n'a pas pu être supprimé du disque, mais il a été retiré du site.", "warning")
    db.session.delete(ressource)
    db.session.commit()
    flash(f"Document « {ressource.titre} » supprimé. 🗑️", "info")
    return redirect(url_for("admin.tableau_de_bord"))
