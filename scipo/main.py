"""Pages publiques du site : accueil, rubriques, recherche, téléchargement."""
from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, send_from_directory, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func

from scipo import db
from scipo.models import LEVELS, Commentaire, Favori, Resource

main = Blueprint("main", __name__)

# Rubriques accessibles depuis chaque niveau (section « Choisissez votre niveau »
# de l'accueil) : (endpoint, clé de catégorie, libellé, icône Bootstrap)
RUBRIQUES_NIVEAU = [
    ("main.cours", "cours", "Cours", "bi-journal-bookmark-fill"),
    ("main.td", "td", "Travaux Dirigés", "bi-pencil-square"),
    ("main.epreuves", "epreuves", "Épreuves", "bi-file-earmark-ruled"),
    ("main.oeuvres", "oeuvres", "Œuvres", "bi-book-half"),
]


@main.app_context_processor
def _injecter_favoris():
    """Met à disposition de tous les modèles l'ensemble des favoris du membre connecté."""
    if current_user.is_authenticated:
        lignes = db.session.query(Favori.resource_id).filter_by(user_id=current_user.id).all()
        return {"favoris_ids": {ligne[0] for ligne in lignes}}
    return {"favoris_ids": set()}


def _ressource_visible(ressource):
    """Un étudiant connecté n'accède qu'à son niveau et aux documents tous niveaux."""
    if not current_user.is_authenticated or current_user.is_admin or not current_user.niveau:
        return True
    return ressource.niveau is None or ressource.niveau == current_user.niveau


def _visible_pour(requete):
    """Applique la restriction par niveau à une requête de ressources."""
    if current_user.is_authenticated and not current_user.is_admin and current_user.niveau:
        requete = requete.filter(
            db.or_(Resource.niveau.is_(None), Resource.niveau == current_user.niveau))
    return requete


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

    return _visible_pour(requete).order_by(Resource.created_at.desc()).all()


def _page_rubrique(categorie, titre, sous_titre, filtre_niveau=True):
    ressources = _requete_ressources(categorie)
    return render_template("ressources.html", titre_page=titre, sous_titre=sous_titre,
                           ressources=ressources, niveaux=LEVELS, filtre_niveau=filtre_niveau)


@main.route("/")
def index():
    visibles = _visible_pour(db.session.query(Resource))
    stats = {
        "documents": visibles.count(),
        "cours": visibles.filter_by(categorie="cours").count(),
        "td": visibles.filter_by(categorie="td").count(),
        "epreuves": visibles.filter_by(categorie="epreuves").count(),
        "bibliotheque": visibles.filter_by(categorie="bibliotheque").count(),
        "oeuvres": visibles.filter_by(categorie="oeuvres").count(),
    }
    recents = visibles.order_by(Resource.created_at.desc()).limit(6).all()

    # Accueil « par niveau » : nombre de documents (niveau, rubrique) pour les
    # compteurs affichés sous chaque onglet Licence 1 → Master 1.
    lignes = (visibles.with_entities(Resource.niveau, Resource.categorie, func.count())
              .filter(Resource.niveau.in_(LEVELS))
              .group_by(Resource.niveau, Resource.categorie).all())
    par_niveau = {cle: {} for cle in LEVELS}
    for niveau, categorie, nombre in lignes:
        par_niveau[niveau][categorie] = nombre

    return render_template("index.html", stats=stats, recents=recents,
                           par_niveau=par_niveau, niveaux=list(LEVELS.items()),
                           rubriques=RUBRIQUES_NIVEAU)


@main.route("/cours")
def cours():
    return _page_rubrique("cours", "Cours",
                          "Les supports de cours, classés par niveau de Licence et de Master")


@main.route("/travaux-diriges")
def td():
    return _page_rubrique("td", "Travaux Dirigés",
                          "Séries de TD, énoncés et corrigés, par niveau")


@main.route("/epreuves")
def epreuves():
    return _page_rubrique("epreuves", "Épreuves anciennes",
                          "Les sujets des années passées pour vous entraîner en conditions réelles")


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
    if not _ressource_visible(ressource):
        abort(403)
    commentaires = (db.session.query(Commentaire)
                    .filter_by(resource_id=ressource.id)
                    .order_by(Commentaire.created_at.desc()).all())
    return render_template("detail.html", r=ressource, commentaires=commentaires)


@main.route("/telecharger/<int:res_id>")
@login_required
def telecharger(res_id):
    """Téléchargement réservé aux membres connectés."""
    ressource = db.get_or_404(Resource, res_id)
    if not _ressource_visible(ressource):
        abort(403)
    ressource.telechargements += 1
    db.session.commit()
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], ressource.nom_fichier,
                               as_attachment=True, download_name=ressource.nom_original)


@main.route("/favoris")
@login_required
def favoris():
    """Page « Mes favoris » : les documents enregistrés par le membre."""
    favoris_utilisateur = (db.session.query(Favori)
                           .filter_by(user_id=current_user.id)
                           .order_by(Favori.created_at.desc()).all())
    ressources = [favori.ressource for favori in favoris_utilisateur
                  if _ressource_visible(favori.ressource)]
    return render_template("favoris.html", titre_page="Mes favoris",
                           sous_titre=f"{len(ressources)} document(s) enregistré(s) pour y revenir vite")


@main.route("/favori/<int:res_id>/basculer", methods=["POST"])
@login_required
def basculer_favori(res_id):
    """Ajoute le document aux favoris, ou le retire s'il y est déjà."""
    ressource = db.get_or_404(Resource, res_id)
    existant = db.session.query(Favori).filter_by(user_id=current_user.id,
                                                  resource_id=ressource.id).first()
    if existant:
        db.session.delete(existant)
        db.session.commit()
        flash(f"« {ressource.titre} » retiré de vos favoris.", "info")
    else:
        db.session.add(Favori(user_id=current_user.id, resource_id=ressource.id))
        db.session.commit()
        flash(f"« {ressource.titre} » ajouté à vos favoris. ⭐", "success")

    # Retour à la page d'où vient le membre (protection contre les redirections externes)
    destination = (request.form.get("suivant") or "").strip()
    if not destination.startswith("/") or destination.startswith("//"):
        destination = url_for("main.detail", res_id=ressource.id)
    return redirect(destination)


@main.route("/ressource/<int:res_id>/commenter", methods=["POST"])
@login_required
def commenter(res_id):
    """Publie un avis (texte + note de 1 à 5) sur un document."""
    ressource = db.get_or_404(Resource, res_id)
    contenu = request.form.get("contenu", "").strip()
    note = request.form.get("note", "")

    if not contenu:
        flash("Votre avis ne peut pas être vide.", "danger")
    elif note not in {"1", "2", "3", "4", "5"}:
        flash("Veuillez choisir une note de 1 à 5 étoiles.", "danger")
    else:
        avis = Commentaire(contenu=contenu, note=int(note),
                           user_id=current_user.id, resource_id=ressource.id)
        db.session.add(avis)
        db.session.commit()
        flash("Merci pour votre avis ! ⭐", "success")
    return redirect(url_for("main.detail", res_id=ressource.id))


@main.route("/commentaire/<int:com_id>/supprimer", methods=["POST"])
@login_required
def supprimer_commentaire(com_id):
    """Supprime un avis : l'auteur ou l'administrateur uniquement (modération)."""
    commentaire = db.get_or_404(Commentaire, com_id)
    if current_user.id != commentaire.user_id and not current_user.is_admin:
        abort(403)
    ressource_id = commentaire.resource_id
    db.session.delete(commentaire)
    db.session.commit()
    flash("Le commentaire a été supprimé.", "info")
    return redirect(url_for("main.detail", res_id=ressource_id))
