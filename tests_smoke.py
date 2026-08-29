"""Test de fumée de SciPo UCAD : vérifie que toutes les pages principales répondent.

Utilisation :  python tests_smoke.py
"""
from scipo import create_app


def main():
    app = create_app()
    client = app.test_client()
    tout_ok = True

    pages = ["/", "/cours", "/travaux-diriges", "/bibliotheque", "/oeuvres",
             "/inscription", "/connexion", "/recherche?q=politique",
             "/page-inexistante"]

    for url in pages:
        reponse = client.get(url)
        attendu = 404 if url == "/page-inexistante" else 200
        ok = reponse.status_code == attendu
        tout_ok = tout_ok and ok
        print(f"{'✅ OK   ' if ok else '❌ ÉCHEC'} {url:30} -> {reponse.status_code}")

    # L'administration doit rediriger (302) vers la connexion si non connecté
    reponse = client.get("/admin/")
    ok = reponse.status_code == 302
    tout_ok = tout_ok and ok
    print(f"{'✅ OK   ' if ok else '❌ ÉCHEC'} {'/admin/ (non connecté)':30} -> {reponse.status_code}")

    print("\n🎉 Tous les tests sont passés — le site fonctionne !"
          if tout_ok else "\n❌ Des tests ont échoué, consultez les messages ci-dessus.")
    return 0 if tout_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
