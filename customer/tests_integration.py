from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from customer.models import (
    Customer, Panier, ProduitPanier,
    CodePromotionnel, PasswordResetToken
)
from shop.models import Produit, CategorieProduit, Etablissement, CategorieEtablissement
from cities_light.models import City, Country
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import json
import io
from datetime import datetime, timedelta


class BaseIntegrationTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.country = Country.objects.create(
            name="Côte d'Ivoire", code2="CI", code3="CIV"
        )
        self.ville = City.objects.create(
            name="Abidjan", country=self.country, display_name="Abidjan, CI"
        )


# =====================================================
# INSCRIPTION → LOGIN
# =====================================================

class TestIntegrationInscriptionLogin(BaseIntegrationTestCase):

    def test_inscription_cree_user_et_customer(self):
        image = Image.new("RGB", (50, 50))
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)

        photo = SimpleUploadedFile(
            "photo.jpg", buf.getvalue(), content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("inscription"),
            {
                "nom": "Test",
                "prenoms": "User",
                "username": "integration",
                "email": "integration@test.com",
                "phone": "0708090605",
                "ville": self.ville.id,
                "adresse": "Test",
                "password": "Password123",
                "passwordconf": "Password123",
                "file": photo,
            }
        )

        self.assertTrue(response.json()["success"])
        self.assertTrue(User.objects.filter(username="integration").exists())
        self.assertTrue(Customer.objects.filter(user__username="integration").exists())

    def test_login_apres_inscription(self):
        user = User.objects.create_user(
            username="loginuser", password="Password123"
        )
        Customer.objects.create(
            user=user, adresse="Test", contact_1="0708", ville=self.ville
        )

        response = self.client.post(
            reverse("post"),
            data=json.dumps({
                "username": "loginuser",
                "password": "Password123"
            }),
            content_type="application/json"
        )

        self.assertTrue(response.json()["success"])
        self.assertIn("_auth_user_id", self.client.session)


# =====================================================
# PANIER ↔ PRODUITS
# =====================================================

class TestIntegrationPanier(BaseIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="cart", password="Password123"
        )
        self.customer = Customer.objects.create(
            user=self.user, adresse="Test", contact_1="0708", ville=self.ville
        )
        self.panier = Panier.objects.create(customer=self.customer)
        self.client.login(username="cart", password="Password123")

        cat_etab = CategorieEtablissement.objects.create(nom="Market", status=True)
        etab = Etablissement.objects.create(
            nom="Shop", ville=self.ville,
            categorie=cat_etab, user=self.user, status=True
        )
        cat_prod = CategorieProduit.objects.create(nom="Tech", status=True)
        self.produit = Produit.objects.create(
            nom="Produit",
            prix=10000,
            quantite=10,
            categorie=cat_prod,
            etablissement=etab,
            status=True
        )

    def test_ajout_produit_panier(self):
        response = self.client.post(
            reverse("add_to_cart"),
            data=json.dumps({
                "panier": self.panier.id,
                "produit": self.produit.id,
                "quantite": 2
            }),
            content_type="application/json"
        )

        self.assertTrue(response.json()["success"])
        self.assertTrue(
            ProduitPanier.objects.filter(
                panier=self.panier, produit=self.produit
            ).exists()
        )

    def test_total_panier_calcule(self):
        ProduitPanier.objects.create(
            panier=self.panier, produit=self.produit, quantite=3
        )

        self.panier.refresh_from_db()
        self.assertEqual(self.panier.total, 30000)


# =====================================================
# CODE PROMOTIONNEL
# =====================================================

class TestIntegrationCodePromo(BaseIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="promo", password="Password123"
        )
        self.customer = Customer.objects.create(
            user=self.user, adresse="Test", contact_1="0708", ville=self.ville
        )
        self.panier = Panier.objects.create(customer=self.customer)
        self.client.login(username="promo", password="Password123")

        self.code = CodePromotionnel.objects.create(
            libelle="Promo",
            etat=True,
            date_fin=datetime.now().date() + timedelta(days=5),
            reduction=0.10,
            nombre_u=10,
            code_promo="PROMO10"
        )

    def test_application_code_promo(self):
        response = self.client.post(
            reverse("add_coupon"),
            data=json.dumps({
                "panier": self.panier.id,
                "coupon": "PROMO10"
            }),
            content_type="application/json"
        )

        self.assertTrue(response.json()["success"])
        self.panier.refresh_from_db()
        self.assertEqual(self.panier.coupon, self.code)


# =====================================================
# PASSWORD RESET (INTÉGRATION MINIMALE)
# =====================================================

class TestIntegrationPasswordReset(BaseIntegrationTestCase):

    def test_token_expire(self):
        user = User.objects.create_user(
            username="reset", password="OldPassword123"
        )

        token = PasswordResetToken.objects.create(
            user=user, token="reset"
        )

        token.created_at = datetime.now() - timedelta(hours=2)
        token.save()
        token.refresh_from_db()

        self.assertFalse(token.is_valid())


# =====================================================
# COHÉRENCE DB
# =====================================================

class TestCoherenceRelations(BaseIntegrationTestCase):

    def test_suppression_user_supprime_customer_et_panier(self):
        user = User.objects.create_user(
            username="cascade", password="Password123"
        )
        customer = Customer.objects.create(
            user=user, adresse="Test", contact_1="0708", ville=self.ville
        )
        panier = Panier.objects.create(customer=customer)

        user.delete()

        self.assertFalse(Customer.objects.filter(id=customer.id).exists())
        self.assertFalse(Panier.objects.filter(id=panier.id).exists())
