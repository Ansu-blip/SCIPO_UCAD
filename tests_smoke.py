"""Test de fumée de SciPo UCAD : vérifie que toutes les pages principales répondent.

Utilisation :  python tests_smoke.py
"""
from scipo import create_app


def main():
    app = create_app()
    client = app.test_client()
    tout_ok = True

    pages = ["/", "/cours", "/travaux-diriges", "/epreuves", "/bibliotheque", "/oeuvres",
             "/inscription", "/connexion", "/recherche?q=politique",
             "/page-inexistante"]

    for url in pages:
        reponse = client.get(url)
        attendu = 404 if url == "/page-inexistante" else 200
        ok = reponse.status_code == attendu
        tout_ok = tout_ok and ok
        print(f"{'✅ OK   ' if ok else '❌ ÉCHEC'} {url:30} -> {reponse.status_code}")

    # L'administration et les favoris doivent rediriger (302) vers la connexion si non connecté
    for url in ["/admin/", "/favoris"]:
        reponse = client.get(url)
        ok = reponse.status_code == 302
        tout_ok = tout_ok and ok
        print(f"{'✅ OK   ' if ok else '❌ ÉCHEC'} {url + ' (non connecté)':30} -> {reponse.status_code}")

    # Un jeton de vérification invalide redirige proprement vers l'accueil
    reponse = client.get("/verification/jeton-invalide")
    ok = reponse.status_code == 302
    tout_ok = tout_ok and ok
    print(f"{'✅ OK   ' if ok else '❌ ÉCHEC'} {'/verification/jeton-invalide':30} -> {reponse.status_code}")

    print("\n🎉 Tous les tests sont passés — le site fonctionne !"
          if tout_ok else "\n❌ Des tests ont échoué, consultez les messages ci-dessus.")
    return 0 if tout_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
