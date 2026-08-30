#!/usr/bin/env bash
# ============================================================
#  SciPo UCAD — Installation automatique sur PythonAnywhere
#
#  Prérequis : le code a été cloné dans ~/SCIPO_UCAD (voir README,
#  section « Mise en ligne »). Puis, dans la console Bash :
#
#     cd ~/SCIPO_UCAD && bash deploy/pythonanywhere_console.sh
# ============================================================
set -e

DOSSIER_CODE="$HOME/SCIPO_UCAD"
DOSSIER_DONNEES="$HOME/donnees-scipo"

cd "$DOSSIER_CODE"

echo "==> 1/4  Environnement virtuel Python"
if ! workon scipo 2>/dev/null; then
    mkvirtualenv scipo --python=python3.13 \
        || mkvirtualenv scipo --python=python3.12
fi

echo "==> 2/4  Installation des dépendances"
pip install -q -r requirements.txt

echo "==> 3/4  Dossier des données persistantes (base + documents)"
mkdir -p "$DOSSIER_DONNEES"

echo "==> 4/4  Compte administrateur (email + mot de passe demandés)"
python creer_admin.py

NOM="$(whoami)"
echo ""
echo "============================================================"
echo "Installation terminée ! Dernières étapes, onglet « Web » :"
echo ""
echo "  1. Add a new web app  ->  Manual configuration  ->  Python 3.13"
echo "  2. Section « Code » :"
echo "       Working directory : $DOSSIER_CODE"
echo "       Virtualenv        : /home/$NOM/.virtualenvs/scipo"
echo "  3. Static files : /static/  ->  $DOSSIER_CODE/scipo/static"
echo "  4. WSGI configuration file : remplacez tout le contenu par"
echo "     celui de deploy/pythonanywhere_wsgi.py (rien a modifier)"
echo "  5. Cochez « Force HTTPS », puis bouton vert « Reload »"
echo ""
echo "  Votre site : https://$NOM.pythonanywhere.com"
echo "============================================================"