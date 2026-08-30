"""WSGI PythonAnywhere pour SciPo UCAD — prêt à l'emploi, rien à modifier.

Copiez tout ce fichier dans le « WSGI configuration file » de l'onglet Web
de PythonAnywhere (voir deploy/pythonanywhere_console.sh pour la procédure).
"""
import os
import sys

# Le nom d'utilisateur PythonAnywhere est détecté automatiquement
NOM_UTILISATEUR = os.path.basename(os.path.expanduser("~"))

CHEMIN_PROJET = f"/home/{NOM_UTILISATEUR}/SCIPO_UCAD"
DOSSIER_DONNEES = f"/home/{NOM_UTILISATEUR}/donnees-scipo"

# Clé secrète stable : générée une première fois puis réutilisée (les sessions
# des utilisateurs ne sont pas invalidées à chaque rechargement du site).
os.makedirs(DOSSIER_DONNEES, exist_ok=True)
fichier_cle = os.path.join(DOSSIER_DONNEES, "cle_secrete.txt")
try:
    with open(fichier_cle) as f:
        cle_secrete = f.read().strip()
except FileNotFoundError:
    import secrets
    cle_secrete = secrets.token_hex(32)
    with open(fichier_cle, "w") as f:
        f.write(cle_secrete)

os.environ["SCIPO_SECRET_KEY"] = cle_secrete
os.environ["SCIPO_DATA_DIR"] = DOSSIER_DONNEES

if CHEMIN_PROJET not in sys.path:
    sys.path.insert(0, CHEMIN_PROJET)

from app import app as application  # noqa: E402