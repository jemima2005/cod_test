from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from shop.models import (
    CategorieEtablissement, CategorieProduit,
    Etablissement, Produit, Favorite
)
from customer.models import Customer
from cities_light.models import City, Country
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
from datetime import datetime, timedelta


class BaseShopTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.country = Country.objects.create(
            name="Côte d'Ivoire", code2="CI", code3="CIV"
        )
        self.ville = City.objects.create(
            name="Abidjan", country=self.country, display_name="Abidjan, CI"
        )

        self.cat_etab = CategorieEtablissement.objects.create(
            nom="Market", status=True
        )
        self.cat_prod = CategorieProduit.objects.create(
            nom="Tech", categorie=self.cat_etab, status=True
        )

        self.user_vendeur = User.objects.create_user(
            username="vendeur", password="Pass123"
        )

        image = Image.new("RGB", (50, 50))
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)

        logo = SimpleUploadedFile(
            "logo.jpg", buf.getvalue(), content_type="image/jpeg"
        )

        self.etablissement = Etablissement.objects.create(
            user=self.user_vendeur,
            nom="Shop",
            categorie=self.cat_etab,
            ville=self.ville,
            adresse="Test",
            contact_1="0708",
            email="shop@test.com",
            logo=logo,
            status=True
        )


# =====================================================
# CATALOGUE
# =====================================================

class TestCatalogue(BaseShopTestCase):

    def test_page_shop_accessible(self):
        response = self.client.get(reverse("shop"))
        self.assertEqual(response.status_code, 200)

    def test_produit_visible_dans_shop(self):
        produit = Produit.objects.create(
            nom="Phone",
            prix=100000,
            quantite=10,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        response = self.client.get(reverse("shop"))
        self.assertContains(response, "Phone")


# =====================================================
# DÉTAIL PRODUIT
# =====================================================

class TestDetailProduit(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.produit = Produit.objects.create(
            nom="Laptop",
            prix=500000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

    def test_page_detail_accessible(self):
        response = self.client.get(
            reverse("product_detail", args=[self.produit.slug])
        )
        self.assertEqual(response.status_code, 200)


# =====================================================
# FAVORIS
# =====================================================

class TestFavoris(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.user_client = User.objects.create_user(
            username="client", password="Pass123"
        )
        Customer.objects.create(
            user=self.user_client,
            adresse="T",
            contact_1="0708",
            ville=self.ville
        )

        self.produit = Produit.objects.create(
            nom="Fav",
            prix=20000,
            quantite=10,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

    def test_ajout_favori_connecte(self):
        self.client.login(username="client", password="Pass123")

        self.client.get(
            reverse("toggle_favorite", args=[self.produit.id])
        )

        self.assertTrue(
            Favorite.objects.filter(
                user=self.user_client, produit=self.produit
            ).exists()
        )

    def test_favori_non_connecte_redirige(self):
        response = self.client.get(
            reverse("toggle_favorite", args=[self.produit.id])
        )
        self.assertEqual(response.status_code, 302)


# =====================================================
# PROMOTIONS
# =====================================================

class TestPromotions(BaseShopTestCase):

    def test_promotion_active(self):
        produit = Produit.objects.create(
            nom="Promo",
            prix=100000,
            prix_promotionnel=80000,
            date_debut_promo=datetime.now().date() - timedelta(days=1),
            date_fin_promo=datetime.now().date() + timedelta(days=3),
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.assertTrue(produit.check_promotion)

    def test_promotion_expiree(self):
        produit = Produit.objects.create(
            nom="Old",
            prix=100000,
            prix_promotionnel=80000,
            date_debut_promo=datetime.now().date() - timedelta(days=10),
            date_fin_promo=datetime.now().date() - timedelta(days=1),
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.assertFalse(produit.check_promotion)


# =====================================================
# DASHBOARD VENDEUR
# =====================================================

class TestDashboardVendeur(BaseShopTestCase):

    def test_dashboard_requiert_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_accessible_vendeur(self):
        self.client.login(username="vendeur", password="Pass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)


# =====================================================
# GESTION ARTICLES
# =====================================================

class TestGestionArticles(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(username="vendeur", password="Pass123")

    def test_ajout_article_valide(self):
        image = Image.new("RGB", (100, 100))
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)

        fichier = SimpleUploadedFile(
            "p.jpg", buf.getvalue(), content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("ajout-article"),
            {
                "nom": "New",
                "prix": 50000,
                "quantite": 5,
                "categorie": self.cat_prod.id,
                "image": fichier
            }
        )

        self.assertTrue(
            Produit.objects.filter(nom="New").exists()
        )

    def test_suppression_article(self):
        produit = Produit.objects.create(
            nom="Del",
            prix=10000,
            quantite=2,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.client.post(
            reverse("supprimer-article", args=[produit.id])
        )

        self.assertFalse(
            Produit.objects.filter(id=produit.id).exists()
        )


# =====================================================
# PANIER / CHECKOUT (ACCÈS)
# =====================================================

class TestPanierCheckout(BaseShopTestCase):

    def test_panier_accessible(self):
        response = self.client.get(reverse("cart"))
        self.assertEqual(response.status_code, 200)

    def test_checkout_requiert_login(self):
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 302)
