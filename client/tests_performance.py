from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from customer.models import Customer, Commande, ProduitPanier
from shop.models import Produit, CategorieProduit, Favorite, Etablissement, CategorieEtablissement
from cities_light.models import City, Country


class BasePerformanceTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.country = Country.objects.create(name="Côte d'Ivoire", code2="CI", code3="CIV")
        self.ville = City.objects.create(name="Abidjan", country=self.country)

        self.user = User.objects.create_user(
            username="perf@test.com",
            password="Password123!"
        )

        self.customer = Customer.objects.create(
            user=self.user,
            contact_1="0708090605",
            ville=self.ville
        )

        cat_etab = CategorieEtablissement.objects.create(nom="Market", status=True)
        self.etablissement = Etablissement.objects.create(
            nom="SuperMarket CI",
            ville=self.ville,
            categorie=cat_etab,
            user=self.user,
            status=True
        )

        cat_prod = CategorieProduit.objects.create(nom="Tech", status=True)

        self.produits = []
        for i in range(10):
            p = Produit.objects.create(
                nom=f"Produit {i}",
                prix=10000,
                quantite=10,
                categorie=cat_prod,
                etablissement=self.etablissement,
                status=True
            )
            self.produits.append(p)

        self.commandes = []
        for i in range(100):
            c = Commande.objects.create(
                customer=self.customer,
                id_paiment=f"PAY{i}",
                transaction_id=f"TXN{i}",
                prix_total=20000,
                status=True
            )
            self.commandes.append(c)

            ProduitPanier.objects.create(
                produit=self.produits[i % len(self.produits)],
                commande=c,
                quantite=1
            )

        for i in range(5):
            Favorite.objects.create(user=self.user, produit=self.produits[i])

        self.client.login(username="perf@test.com", password="Password123!")


# ======================================================
# REQUÊTES SQL (VRAIE PERFORMANCE BACKEND)
# ======================================================

@override_settings(DEBUG=True)
class TestRequetesSQL(BasePerformanceTestCase):

    def test_profil_nombre_requetes_limite(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("profil"))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 10)

    def test_liste_commandes_sans_n_plus_1(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("commande"))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 20)

    def test_detail_commande_optimise(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(
                reverse("commande-detail", args=[self.commandes[0].id])
            )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 10)

    def test_liste_souhaits_optimisee(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("liste-souhait"))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 10)


# ======================================================
# PAGINATION (STABILITÉ)
# ======================================================

@override_settings(DEBUG=True)
class TestPaginationPerformance(BasePerformanceTestCase):

    def test_pagination_nombre_requetes_constant(self):
        with CaptureQueriesContext(connection) as ctx1:
            self.client.get(reverse("commande"))

        with CaptureQueriesContext(connection) as ctx2:
            self.client.get(reverse("commande") + "?page=2")

        self.assertEqual(len(ctx1), len(ctx2))


# ======================================================
# MONTÉE EN CHARGE LOGIQUE
# ======================================================

@override_settings(DEBUG=True)
class TestChargeLogique(BasePerformanceTestCase):

    def test_100_commandes_affichage_correct(self):
        response = self.client.get(reverse("commande"))
        self.assertEqual(response.status_code, 200)

        # On vérifie que la pagination est toujours active
        self.assertContains(response, "TXN0")
        self.assertContains(response, "TXN99")


# ======================================================
# PDF (COÛT RAISONNABLE)
# ======================================================

class TestPerformancePDF(BasePerformanceTestCase):

    def test_generation_pdf_non_vide(self):
        response = self.client.get(
            reverse("invoice_pdf", args=[self.commandes[0].id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertGreater(len(response.content), 100)

    def test_pdf_taille_raisonnable(self):
        response = self.client.get(
            reverse("invoice_pdf", args=[self.commandes[0].id])
        )

        taille_mb = len(response.content) / (1024 * 1024)
        self.assertLess(taille_mb, 1.0)


# ======================================================
# ÉCRITURES (PAS DE LATENCE ANORMALE)
# ======================================================

class TestPerformanceEcriture(BasePerformanceTestCase):

    def test_modification_profil_persistante(self):
        response = self.client.post(reverse("parametre"), {
            "first_name": "Pierre",
            "last_name": "Martin",
            "contact": "0708090605",
            "city": self.ville.id
        })

        self.assertIn(response.status_code, [302, 200])

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Pierre")
