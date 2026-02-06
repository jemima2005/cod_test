from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from shop.models import (
    CategorieEtablissement, CategorieProduit,
    Etablissement, Produit, Favorite
)
from customer.models import Customer
from cities_light.models import City, Country
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io


class BaseShopPerformanceTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.country = Country.objects.create(
            name="CI", code2="CI", code3="CIV"
        )
        self.ville = City.objects.create(
            name="Abidjan", country=self.country
        )

        self.cat_etab = CategorieEtablissement.objects.create(
            nom="Market", status=True
        )
        self.cat_prod = CategorieProduit.objects.create(
            nom="Tech", categorie=self.cat_etab, status=True
        )

        self.vendeur = User.objects.create_user(
            username="vendeur", password="Pass123"
        )

        img = Image.new("RGB", (50, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        logo = SimpleUploadedFile(
            "logo.jpg", buf.getvalue(), content_type="image/jpeg"
        )

        self.etablissement = Etablissement.objects.create(
            user=self.vendeur,
            nom="Shop",
            categorie=self.cat_etab,
            ville=self.ville,
            adresse="T",
            contact_1="07",
            email="shop@test.com",
            logo=logo,
            status=True
        )


# =====================================================
# SHOP — NOMBRE DE REQUÊTES
# =====================================================

@override_settings(DEBUG=True)
class TestPerformanceShop(BaseShopPerformanceTestCase):

    def test_page_shop_requetes_constantes(self):
        for i in range(20):
            Produit.objects.create(
                nom=f"P{i}",
                prix=1000,
                quantite=5,
                categorie=self.cat_prod,
                etablissement=self.etablissement,
                status=True
            )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("shop"))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 15)


# =====================================================
# DETAIL PRODUIT — PAS DE N+1
# =====================================================

@override_settings(DEBUG=True)
class TestPerformanceDetailProduit(BaseShopPerformanceTestCase):

    def test_detail_produit_requetes_limitees(self):
        produit = Produit.objects.create(
            nom="Detail",
            prix=2000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(
                reverse("product_detail", args=[produit.slug])
            )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 10)


# =====================================================
# FAVORIS — STABILITÉ DB
# =====================================================

@override_settings(DEBUG=True)
class TestPerformanceFavoris(BaseShopPerformanceTestCase):

    def setUp(self):
        super().setUp()
        self.client_user = User.objects.create_user(
            username="client", password="Pass123"
        )
        Customer.objects.create(
            user=self.client_user,
            adresse="T",
            contact_1="07",
            ville=self.ville
        )

        self.produits = []
        for i in range(30):
            p = Produit.objects.create(
                nom=f"P{i}",
                prix=1000,
                quantite=5,
                categorie=self.cat_prod,
                etablissement=self.etablissement,
                status=True
            )
            self.produits.append(p)

    def test_toggle_favori_requetes_constantes(self):
        self.client.login(username="client", password="Pass123")

        with CaptureQueriesContext(connection) as ctx:
            self.client.get(
                reverse("toggle_favorite", args=[self.produits[0].id])
            )

        self.assertLessEqual(len(ctx), 5)


# =====================================================
# DASHBOARD VENDEUR — VOLUME
# =====================================================

@override_settings(DEBUG=True)
class TestPerformanceDashboard(BaseShopPerformanceTestCase):

    def test_dashboard_volume_constant(self):
        for i in range(40):
            Produit.objects.create(
                nom=f"P{i}",
                prix=1000,
                quantite=5,
                categorie=self.cat_prod,
                etablissement=self.etablissement,
                status=True
            )

        self.client.login(username="vendeur", password="Pass123")

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 15)
