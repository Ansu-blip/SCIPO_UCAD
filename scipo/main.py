"""Pages publiques du site : accueil, rubriques, recherche, téléchargement."""
from flask import (Blueprint, abort, current_app, redirect, render_template,
                   request, send_from_directory, url_for)
from flask_login import current_user, login_required

from scipo import db
from scipo.models import LEVELS, Resource

main = Blueprint("main", __name__)


def _requete_ressources(categorie=None):
    """Construit la liste des ressources selon filtres (rubrique, niveau, recherche)."""
    requete = db.session.query(Resource)

    if categorie:
        requete = requete.filter_by(categorie=categorie)

    niveau = request.args.get("niveau")
    if niveau in LEVELS:
        requete = requete.filter_by(niveau=niveau)

    terme = request.args.get("q", "").strip()
    if terme:
        motif = f"%{terme}%"
        requete = requete.filter(
            db.or_(Resource.titre.ilike(motif),
                   Resource.description.ilike(motif),
                   Resource.auteur.ilike(motif))
        )

    return requete.order_by(Resource.created_at.desc()).all()


def _page_rubrique(categorie, titre, sous_titre, filtre_niveau=True):
    ressources = _requete_ressources(categorie)
    return render_template("ressources.html", titre_page=titre, sous_titre=sous_titre,
                           ressources=ressources, niveaux=LEVELS, filtre_niveau=filtre_niveau)


@main.route("/")
def index():
    stats = {
        "documents": db.session.query(Resource).count(),
        "cours": db.session.query(Resource).filter_by(categorie="cours").count(),
        "td": db.session.query(Resource).filter_by(categorie="td").count(),
        "bibliotheque": db.session.query(Resource).filter_by(categorie="bibliotheque").count(),
        "oeuvres": db.session.query(Resource).filter_by(categorie="oeuvres").count(),
    }
    recents = db.session.query(Resource).order_by(Resource.created_at.desc()).limit(6).all()
    return render_template("index.html", stats=stats, recents=recents)


@main.route("/cours")
def cours():
    return _page_rubrique("cours", "Cours",
                          "Les supports de cours, classés par niveau de Licence et de Master")


@main.route("/travaux-diriges")
def td():
    return _page_rubrique("td", "Travaux Dirigés",
                          "Séries de TD, énoncés et corrigés, par niveau")


@main.route("/bibliotheque")
def bibliotheque():
    return _page_rubrique("bibliotheque", "Bibliothèque numérique",
                          "Documents, mémoires et ressources numériques à consulter")


@main.route("/oeuvres")
def oeuvres():
    return _page_rubrique("oeuvres", "Œuvres",
                          "Livres, syllabus et articles de référence en Science Politique",
                          filtre_niveau=False)


@main.route("/recherche")
def recherche():
    terme = request.args.get("q", "").strip()
    ressources = _requete_ressources(None)
    return render_template("ressources.html",
                           titre_page=f"Recherche : « {terme} »",
                           sous_titre=f"{len(ressources)} résultat(s) trouvé(s)",
                           ressources=ressources, niveaux=LEVELS, filtre_niveau=False)


@main.route("/ressource/<int:res_id>")
def detail(res_id):
    ressource = db.get_or_404(Resource, res_id)
    return render_template("detail.html", r=ressource)


@main.route("/telecharger/<int:res_id>")
@login_required
def telecharger(res_id):
    """Téléchargement réservé aux membres connectés."""
    ressource = db.get_or_404(Resource, res_id)
    ressource.telechargements += 1
    db.session.commit()
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], ressource.nom_fichier,
                               as_attachment=True, download_name=ressource.nom_original)
