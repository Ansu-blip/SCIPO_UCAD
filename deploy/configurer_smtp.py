"""Configuration de l'envoi d'emails (SMTP) pour SciPo UCAD.

Écrit le fichier « smtp.conf » dans le dossier de données (~/donnees-scipo en
ligne, hors du dépôt Git), puis peut envoyer un email de test pour valider
l'ensemble. Dès que le SMTP est en place, la connexion demande automatiquement
un code à 6 chiffres envoyé par email (OTP).

Utilisation :
    python deploy/configurer_smtp.py            # configuration interactive
    python deploy/configurer_smtp.py --test     # envoie un email de test
    python deploy/configurer_smtp.py --voir     # affiche la config (masquée)

Avec Gmail, utilisez un « mot de passe d'application » (16 caractères) et non
votre mot de passe habituel : Google → Sécurité → Validation en deux étapes →
Mots de passe d'application.
"""
import getpass
import os
import stat
import sys
from pathlib import Path

CHEMIN_PROJET = Path(__file__).resolve().parent.parent
if str(CHEMIN_PROJET) not in sys.path:
    sys.path.insert(0, str(CHEMIN_PROJET))

from config import charger_smtp_conf  # noqa: E402

MODELE = """\
# Configuration SMTP de SciPo UCAD — générée par deploy/configurer_smtp.py
# Fichier personnel : il vit dans le dossier de données, hors du dépôt Git.
SCIPO_SMTP_HOTE={hote}
SCIPO_SMTP_PORT={port}
SCIPO_SMTP_UTILISATEUR={utilisateur}
SCIPO_SMTP_MOT_DE_PASSE={mot_de_passe}
SCIPO_EMAIL_EXPEDITEUR={expediteur}
"""


def dossier_donnees():
    """Dossier de données : variable d'environnement ou ~/donnees-scipo."""
    dossier = os.environ.get("SCIPO_DATA_DIR", "").strip()
    return Path(dossier) if dossier else Path.home() / "donnees-scipo"


def charger_configuration():
    """Configuration SMTP détectée (variables d'environnement + smtp.conf)."""
    charger_smtp_conf()
    return {
        "hote": os.environ.get("SCIPO_SMTP_HOTE", ""),
        "port": os.environ.get("SCIPO_SMTP_PORT", "587"),
        "utilisateur": os.environ.get("SCIPO_SMTP_UTILISATEUR", ""),
        "mot_de_passe": os.environ.get("SCIPO_SMTP_MOT_DE_PASSE", ""),
        "expediteur": os.environ.get("SCIPO_EMAIL_EXPEDITEUR", ""),
    }


def configurer():
    """Questions/réponses puis écriture de smtp.conf (droits restreints)."""
    actuelle = charger_configuration()
    print("=== Configuration email de Science Po UCAD ===")
    print("Fournisseur le plus courant : Gmail (smtp.gmail.com, port 587).")
    print("Avec Gmail, utilisez un MOT DE PASSE D'APPLICATION (16 caractères) :")
    print("  Google → Sécurité → Validation en deux étapes → Mots de passe d'application.\n")

    hote = input(f"Serveur SMTP [{actuelle['hote'] or 'smtp.gmail.com'}] : ").strip() \
        or actuelle["hote"] or "smtp.gmail.com"
    port = input(f"Port [{actuelle['port'] or '587'}] : ").strip() \
        or actuelle["port"] or "587"
    utilisateur = input(f"Adresse Gmail expéditrice [{actuelle['utilisateur']}] : ").strip() \
        or actuelle["utilisateur"]
    if "@" not in utilisateur:
        print("❌ Une adresse email valide est requise (ex. prenom.nom@gmail.com).")
        return 1
    mot_de_passe = getpass.getpass(
        "Mot de passe d'application (saisie masquée) : ").strip() or actuelle["mot_de_passe"]
    if not mot_de_passe:
        print("❌ Le mot de passe d'application est obligatoire.")
        return 1
    expediteur_defaut = actuelle["expediteur"] or f"SciPo UCAD <{utilisateur}>"
    expediteur = input(f"Nom affiché de l'expéditeur [{expediteur_defaut}] : ").strip() \
        or expediteur_defaut

    dossier = dossier_donnees()
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "smtp.conf"
    fichier.write_text(MODELE.format(
        hote=hote, port=port, utilisateur=utilisateur,
        mot_de_passe=mot_de_passe, expediteur=expediteur), encoding="utf-8")
    try:   # lecture réservée au propriétaire (utile sur Linux / PythonAnywhere)
        fichier.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    print(f"\n✅ Configuration enregistrée : {fichier}")
    print("   → Appliquez-la : bouton Reload (onglet Web de PythonAnywhere).")
    print("   → Testez-la  : python deploy/configurer_smtp.py --test")
    return 0


def tester():
    """Envoie un email de test avec la configuration détectée."""
    dossier = dossier_donnees()
    if (dossier / "smtp.conf").is_file() or os.environ.get("SCIPO_DATA_DIR"):
        os.environ["SCIPO_DATA_DIR"] = str(dossier)
    configuration = charger_configuration()
    if not configuration["hote"]:
        print("❌ Aucun SMTP configuré. Lancez d'abord : python deploy/configurer_smtp.py")
        return 1
    print(f"Serveur : {configuration['hote']}:{configuration['port']}  "
          f"Utilisateur : {configuration['utilisateur']}")

    from scipo import create_app
    from scipo.auth import _envoyer_email

    app = create_app()
    if not app.config["OTP_ACTIVE"]:
        print("ℹ️ Remarque : le code OTP est désactivé (SCIPO_OTP_ACTIF=0 ?).")
    destinataire = input("Envoyer l'email de test à "
                         f"[{configuration['utilisateur']}] : ").strip() \
        or configuration["utilisateur"]
    try:
        with app.app_context():
            _envoyer_email(
                destinataire,
                "Test de configuration — Science Po UCAD",
                "Bravo ! La configuration SMTP de Science Po UCAD fonctionne.\n"
                "Les codes de connexion (OTP) et les liens de vérification partiront\n"
                "désormais bien par email.\n— Science Po UCAD",
            )
    except Exception as erreur:
        print(f"\n❌ Échec de l'envoi : {erreur}")
        print("   Vérifiez : mot de passe d'APPLICATION (et non le mot de passe Gmail),")
        print("   port 587 (STARTTLS) ou 465 (SSL), et votre connexion internet.")
        return 1
    print(f"\n✅ Email de test envoyé à {destinataire} — vérifiez la boîte de réception")
    print("   (et les spams). Le code OTP est désormais actif sur le site.")
    return 0


def montrer():
    """Affiche la configuration détectée, mot de passe masqué."""
    configuration = charger_configuration()
    mot_de_passe = configuration["mot_de_passe"]
    masque = (mot_de_passe[:2] + "…" + mot_de_passe[-2:]) if len(mot_de_passe) > 4 \
        else ("défini" if mot_de_passe else "(vide)")
    print(f"Hôte          : {configuration['hote'] or '(non configuré)'}")
    print(f"Port          : {configuration['port']}")
    print(f"Utilisateur   : {configuration['utilisateur'] or '(non configuré)'}")
    print(f"Mot de passe  : {masque}")
    print(f"Expéditeur    : {configuration['expediteur'] or '(par défaut)'}")
    print(f"Code OTP      : {'actif' if configuration['hote'] else 'inactif (SMTP manquant)'}")
    print(f"Fichier       : {dossier_donnees() / 'smtp.conf'}")
    return 0


def main():
    argument = sys.argv[1] if len(sys.argv) > 1 else ""
    if argument == "--test":
        return tester()
    if argument == "--voir":
        return montrer()
    if argument in {"", "--configurer"}:
        return configurer()
    print(f"Argument inconnu : {argument}\n"
          "Utilisation : python deploy/configurer_smtp.py [--configurer|--test|--voir]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())