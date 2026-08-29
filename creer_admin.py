"""Créer ou mettre à jour le compte administrateur du site.

Utilisation :  python creer_admin.py
"""
from scipo import create_app, db
from scipo.models import User

app = create_app()

with app.app_context():
    print("=== Création du compte administrateur SciPo UCAD ===")
    email = input("Email administrateur : ").strip().lower()
    nom = input("Nom complet (optionnel) : ").strip()
    mot_de_passe = input("Mot de passe (min. 6 caractères) : ")

    if "@" not in email or len(mot_de_passe) < 6:
        print("❌ Email invalide ou mot de passe trop court (min. 6 caractères).")
    else:
        utilisateur = db.session.query(User).filter_by(email=email).first()
        if utilisateur is None:
            utilisateur = User(email=email, nom_complet=nom or None, is_admin=True)
            print("✅ Nouvel administrateur créé :", email)
        else:
            utilisateur.is_admin = True
            print("✅ Compte existant promu administrateur :", email)
        utilisateur.email_verifie = True   # pas de vérification d'email pour l'administrateur
        utilisateur.set_password(mot_de_passe)
        db.session.add(utilisateur)
        db.session.commit()
