"""Point d'entrée du site SciPo UCAD.

Lancer le site :  python app.py
Puis ouvrir :     http://127.0.0.1:5000
"""
from scipo import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
