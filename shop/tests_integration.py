from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from shop.models import (
    CategorieEtablissement, CategorieProduit,
    Etablissement, Produit, Favorite
)
from customer.models import Customer, Panier, ProduitPanier, Commande
from cities_light.models import City, Country
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
from datetime import datetime, timedelta


class BaseShopIntegrationTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.country = Country.objects.create(
            name="Côte d'Ivoire", code2="CI", code3="CIV"
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
            adresse="Test",
            contact_1="0708",
            email="shop@test.com",
            logo=logo,
            status=True
        )


# =====================================================
# PRODUIT ↔ CATÉGORIE
# =====================================================

class TestIntegrationProduitCategorie(BaseShopIntegrationTestCase):

    def test_produit_lie_a_categorie(self):
        produit = Produit.objects.create(
            nom="Produit",
            prix=10000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.assertEqual(produit.categorie, self.cat_prod)
        self.assertIn(produit, self.cat_prod.produit.all())


# =====================================================
# CLIENT ↔ FAVORIS
# =====================================================

class TestIntegrationFavoris(BaseShopIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.client_user = User.objects.create_user(
            username="client", password="Pass123"
        )
        self.customer = Customer.objects.create(
            user=self.client_user,
            adresse="T",
            contact_1="07",
            ville=self.ville
        )

        self.produit = Produit.objects.create(
            nom="Fav",
            prix=5000,
            quantite=10,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

    def test_ajout_favori(self):
        self.client.login(username="client", password="Pass123")

        self.client.get(
            reverse("toggle_favorite", args=[self.produit.id])
        )

        self.assertTrue(
            Favorite.objects.filter(
                user=self.client_user, produit=self.produit
            ).exists()
        )


# =====================================================
# VENDEUR ↔ DASHBOARD
# =====================================================

class TestIntegrationDashboard(BaseShopIntegrationTestCase):

    def test_dashboard_vendeur_affiche_ses_articles(self):
        Produit.objects.create(
            nom="P1",
            prix=1000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.client.login(username="vendeur", password="Pass123")
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_articles"], 1)


# =====================================================
# COMMANDE ↔ PRODUIT ↔ VENDEUR
# =====================================================

class TestIntegrationCommande(BaseShopIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.client_user = User.objects.create_user(
            username="buyer", password="Pass123"
        )
        self.customer = Customer.objects.create(
            user=self.client_user,
            adresse="T",
            contact_1="07",
            ville=self.ville
        )

        self.produit = Produit.objects.create(
            nom="Cmd",
            prix=20000,
            quantite=10,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

    def test_commande_visible_pour_vendeur(self):
        commande = Commande.objects.create(
            customer=self.customer,
            prix_total=20000,
            transaction_id="tx123"
        )

        ProduitPanier.objects.create(
            commande=commande,
            produit=self.produit,
            quantite=1
        )

        self.client.login(username="vendeur", password="Pass123")
        response = self.client.get(reverse("commande-reçu"))

        self.assertEqual(response.status_code, 200)


# =====================================================
# MULTI-VENDEURS (ISOLATION)
# =====================================================

class TestIsolationMultiVendeurs(BaseShopIntegrationTestCase):

    def setUp(self):
        super().setUp()

        self.vendeur2 = User.objects.create_user(
            username="vendeur2", password="Pass123"
        )

        self.etab2 = Etablissement.objects.create(
            user=self.vendeur2,
            nom="Shop2",
            categorie=self.cat_etab,
            ville=self.ville,
            adresse="T",
            contact_1="09",
            email="shop2@test.com",
            status=True
        )

    def test_vendeur_ne_voit_que_ses_produits(self):
        Produit.objects.create(
            nom="P1",
            prix=1000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        Produit.objects.create(
            nom="P2",
            prix=2000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etab2,
            status=True
        )

        self.client.login(username="vendeur", password="Pass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_articles"], 1)


# =====================================================
# COHÉRENCE DONNÉES
# =====================================================

class TestCoherenceDonnees(BaseShopIntegrationTestCase):

    def test_slug_unique(self):
        p1 = Produit.objects.create(
            nom="Test",
            prix=1000,
            quantite=1,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        p2 = Produit.objects.create(
            nom="Test",
            prix=2000,
            quantite=2,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.assertNotEqual(p1.slug, p2.slug)

    def test_suppression_etablissement_supprime_produits(self):
        produit = Produit.objects.create(
            nom="Del",
            prix=1000,
            quantite=1,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.etablissement.delete()
        self.assertFalse(
            Produit.objects.filter(id=produit.id).exists()
        )
