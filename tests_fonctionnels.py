"""Tests fonctionnels de SciPo UCAD (base de données en mémoire : aucun risque).

Scénario complet : inscription → connexion → administration → publication
d'un document → recherche → téléchargement → modification → suppression.

Utilisation :  python tests_fonctionnels.py
"""
import io
import os
import re
import shutil
import tempfile

from config import Config
from itsdangerous import URLSafeTimedSerializer
from scipo import _creer_admin_initial, create_app, db
from scipo.auth import SALT_VERIFICATION
from scipo.models import Commentaire, Resource, User


class ConfigTest(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"   # base de données en mémoire
    SECRET_KEY = "cle-de-test"


def _jeton(client, url):
    """Récupère le jeton CSRF du formulaire affiché sur la page donnée."""
    page = client.get(url)
    correspondance = re.search(rb'name="csrf_token"\s+value="([^"]+)"', page.data)
    assert correspondance, f"Jeton CSRF introuvable sur {url}"
    return correspondance.group(1).decode()


def main():
    dossier_temporaire = tempfile.mkdtemp()
    ConfigTest.UPLOAD_FOLDER = dossier_temporaire

    app = create_app(ConfigTest)
    client = app.test_client()
    tout_ok = True

    def verifier(label, condition):
        nonlocal tout_ok
        tout_ok = tout_ok and bool(condition)
        print(f"{'✅ OK   ' if condition else '❌ ÉCHEC'} {label}")

    # 1. Inscription d'un étudiant
    reponse = client.post("/inscription", data={
        "nom_complet": "Awa Test",
        "email": "awa.test@exemple.sn",
        "password": "motdepasse123",
        "password2": "motdepasse123",
        "csrf_token": _jeton(client, "/inscription"),
    })
    verifier("Inscription d'un étudiant (redirection)", reponse.status_code == 302)

    accueil = client.get("/").get_data(as_text=True)
    verifier("L'étudiant connecté apparaît sur l'accueil", "Awa Test" in accueil)
    verifier("La bannière « email non vérifié » apparaît", "pas encore été vérifiée" in accueil)

    with app.app_context():
        utilisateur = db.session.query(User).filter_by(email="awa.test@exemple.sn").first()
        verifier("Le nouvel email est enregistré comme non vérifié",
                 utilisateur.email_verifie is False)

    # 1bis. Vérification de l'email via le lien signé envoyé « par email »
    jeton_email = URLSafeTimedSerializer(
        "cle-de-test", salt=SALT_VERIFICATION).dumps("awa.test@exemple.sn")
    verifier("Le lien de vérification signé fonctionne",
             client.get(f"/verification/{jeton_email}").status_code == 302)
    with app.app_context():
        utilisateur = db.session.query(User).filter_by(email="awa.test@exemple.sn").first()
        verifier("L'email est maintenant marqué vérifié", utilisateur.email_verifie is True)

    # 2. Déconnexion puis reconnexion
    verifier("Déconnexion", client.get("/deconnexion").status_code == 302)
    reponse = client.post("/connexion", data={
        "email": "awa.test@exemple.sn",
        "password": "motdepasse123",
        "csrf_token": _jeton(client, "/connexion"),
    })
    verifier("Reconnexion avec les mêmes identifiants", reponse.status_code == 302)

    # 3. Un simple étudiant n'a pas accès à l'administration
    verifier("Administration interdite aux étudiants (403)",
             client.get("/admin/").status_code == 403)

    # 4. Promotion en administrateur puis accès au tableau de bord
    with app.app_context():
        utilisateur = db.session.query(User).filter_by(email="awa.test@exemple.sn").first()
        utilisateur.is_admin = True
        db.session.commit()
    verifier("Tableau de bord accessible à l'administrateur",
             client.get("/admin/").status_code == 200)

    # 5. Publication d'un document
    reponse = client.post("/admin/ressource/ajouter", data={
        "titre": "Introduction à la Science Politique — Chapitre 1",
        "categorie": "cours",
        "niveau": "licence1",
        "auteur": "Pr. Test",
        "description": "Support de cours d'introduction.",
        "fichier": (io.BytesIO(b"%PDF-1.4 document de test"), "cours_intro.pdf"),
        "csrf_token": _jeton(client, "/admin/ressource/ajouter"),
    }, content_type="multipart/form-data")
    verifier("Publication d'un cours par l'administrateur (redirection)",
             reponse.status_code == 302)

    with app.app_context():
        ressource = db.session.query(Resource).first()
        ressource_id = ressource.id if ressource else None
    verifier("Le document est enregistré en base de données", ressource_id is not None)

    # 6. Le document apparaît dans la rubrique Cours et dans la recherche
    page_cours = client.get("/cours?niveau=licence1").get_data(as_text=True)
    verifier("Le document apparaît dans /cours (filtre Licence 1)",
             "Introduction à la Science Politique" in page_cours)
    page_recherche = client.get("/recherche?q=Introduction").get_data(as_text=True)
    verifier("La recherche trouve le document",
             "Introduction à la Science Politique" in page_recherche)

    # 7. Téléchargement : autorisé pour un membre, refusé pour un visiteur
    reponse = client.get(f"/telecharger/{ressource_id}")
    verifier("Téléchargement par un membre connecté",
             reponse.status_code == 200 and reponse.data.startswith(b"%PDF"))
    reponse.close()   # libère le fichier (sinon Windows le garde verrouillé)
    visiteur = app.test_client()   # nouveau client = non connecté
    verifier("Téléchargement refusé aux visiteurs (redirection connexion)",
             visiteur.get(f"/telecharger/{ressource_id}").status_code == 302)

    # 8. Favoris : ajout, consultation, retrait puis remise (pour la suite)
    jeton_formulaire = _jeton(client, f"/ressource/{ressource_id}")
    reponse = client.post(f"/favori/{ressource_id}/basculer", data={
        "csrf_token": jeton_formulaire, "suivant": f"/ressource/{ressource_id}"})
    verifier("Ajout du document aux favoris (redirection)", reponse.status_code == 302)
    page_favoris = client.get("/favoris").get_data(as_text=True)
    verifier("Le favori apparaît sur la page « Mes favoris »",
             "Introduction à la Science Politique" in page_favoris)

    reponse = client.post(f"/favori/{ressource_id}/basculer", data={
        "csrf_token": jeton_formulaire, "suivant": f"/ressource/{ressource_id}"})
    verifier("Retrait du document des favoris (même bouton)", reponse.status_code == 302)
    page_favoris = client.get("/favoris").get_data(as_text=True)
    verifier("La page « Mes favoris » affiche l'état vide",
             "Aucun favori pour l'instant" in page_favoris)

    reponse = client.post(f"/favori/{ressource_id}/basculer", data={
        "csrf_token": jeton_formulaire, "suivant": f"/ressource/{ressource_id}"})
    verifier("Remise en favoris (pour la suite du scénario)", reponse.status_code == 302)

    # 9. Commentaires et notes : publier un avis avec une note de 4
    reponse = client.post(f"/ressource/{ressource_id}/commenter", data={
        "note": "4",
        "contenu": "Très bon support, clair et bien structuré.",
        "csrf_token": jeton_formulaire,
    })
    verifier("Publication d'un avis avec une note (redirection)", reponse.status_code == 302)
    page_detail = client.get(f"/ressource/{ressource_id}").get_data(as_text=True)
    verifier("L'avis apparaît sur la page du document",
             "Très bon support, clair et bien structuré." in page_detail)
    verifier("La note moyenne est affichée", "4.0/5" in page_detail)

    with app.app_context():
        nb_avis = db.session.query(Commentaire).count()
    reponse = client.post(f"/ressource/{ressource_id}/commenter", data={
        "note": "9", "contenu": "note invalide", "csrf_token": jeton_formulaire})
    with app.app_context():
        verifier("Un avis avec une note invalide (9) est refusé",
                 reponse.status_code == 302 and db.session.query(Commentaire).count() == nb_avis)

    # 10. Le tableau de bord affiche les nouvelles statistiques
    page_admin = client.get("/admin/").get_data(as_text=True)
    verifier("Le tableau de bord affiche favoris et avis",
             "Favoris" in page_admin and "Avis publiés" in page_admin)

    # 11. Modération : suppression de l'avis par l'administrateur
    with app.app_context():
        avis = db.session.query(Commentaire).first()
        avis_id = avis.id if avis else None
    reponse = client.post(f"/commentaire/{avis_id}/supprimer", data={
        "csrf_token": jeton_formulaire})
    verifier("Suppression d'un avis par l'administrateur", reponse.status_code == 302)
    page_detail = client.get(f"/ressource/{ressource_id}").get_data(as_text=True)
    verifier("L'avis supprimé n'apparaît plus", "Très bon support" not in page_detail)

    # 12. Modification puis suppression du document
    reponse = client.post(f"/admin/ressource/{ressource_id}/modifier", data={
        "titre": "Introduction à la Science Politique — Chapitre 1 (v2)",
        "categorie": "cours",
        "niveau": "licence2",
        "auteur": "Pr. Test",
        "description": "Version mise à jour.",
        "fichier": (io.BytesIO(b"%PDF-1.4 version 2"), "cours_intro_v2.pdf"),
        "csrf_token": _jeton(client, f"/admin/ressource/{ressource_id}/modifier"),
    }, content_type="multipart/form-data")
    verifier("Modification du document", reponse.status_code == 302)

    reponse = client.post(f"/admin/ressource/{ressource_id}/supprimer", data={
        "csrf_token": _jeton(client, "/admin/"),
    })
    verifier("Suppression du document", reponse.status_code == 302)
    verifier("Le document n'existe plus (404)",
             client.get(f"/ressource/{ressource_id}").status_code == 404)

    # 13. Création automatique de l'administrateur initial (utile en ligne, ex. Render)
    os.environ["SCIPO_ADMIN_EMAIL"] = "chef@exemple.sn"
    os.environ["SCIPO_ADMIN_MOT_DE_PASSE"] = "secret123"
    try:
        application = create_app(ConfigTest)
        with application.app_context():
            admin = db.session.query(User).filter_by(email="chef@exemple.sn").first()
            verifier("Administrateur initial créé depuis les variables d'environnement",
                     admin is not None and admin.is_admin and admin.email_verifie)

        # Un compte déjà existant n'est jamais dupliqué ni écrasé
        os.environ["SCIPO_ADMIN_EMAIL"] = "awa.test@exemple.sn"
        os.environ["SCIPO_ADMIN_MOT_DE_PASSE"] = "autre-secret-123"
        with app.app_context():
            _creer_admin_initial()
            verifier("Aucune duplication si le compte admin existe déjà",
                     db.session.query(User).filter_by(email="awa.test@exemple.sn").count() == 1)
    finally:
        os.environ.pop("SCIPO_ADMIN_EMAIL", None)
        os.environ.pop("SCIPO_ADMIN_MOT_DE_PASSE", None)

    shutil.rmtree(dossier_temporaire, ignore_errors=True)

    print("\n🎉 Tous les tests fonctionnels sont passés — le site est 100 % opérationnel !"
          if tout_ok else "\n❌ Des tests ont échoué, consultez les messages ci-dessus.")
    return 0 if tout_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
