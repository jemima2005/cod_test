from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from customer.models import (
    Customer, Panier, Commande, ProduitPanier,
    CodePromotionnel, PasswordResetToken
)
from shop.models import Produit, CategorieProduit, Etablissement, CategorieEtablissement
from cities_light.models import City, Country
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import json
import io
from datetime import datetime, timedelta


class BaseCustomerTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.country = Country.objects.create(
            name="Côte d'Ivoire", code2="CI", code3="CIV"
        )
        self.ville = City.objects.create(
            name="Abidjan", country=self.country, display_name="Abidjan, CI"
        )


# =====================================================
# AUTHENTIFICATION
# =====================================================

class TestLogin(BaseCustomerTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123"
        )
        Customer.objects.create(
            user=self.user,
            adresse="Test",
            contact_1="0708090605",
            ville=self.ville
        )

    def test_page_login_accessible(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")

    def test_login_username_reussi(self):
        response = self.client.post(
            reverse("post"),
            data=json.dumps({
                "username": "testuser",
                "password": "TestPassword123"
            }),
            content_type="application/json"
        )

        self.assertTrue(response.json()["success"])
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_login_mot_de_passe_incorrect(self):
        response = self.client.post(
            reverse("post"),
            data=json.dumps({
                "username": "testuser",
                "password": "WrongPassword"
            }),
            content_type="application/json"
        )

        self.assertFalse(response.json()["success"])
        self.assertFalse("_auth_user_id" in self.client.session)


# =====================================================
# INSCRIPTION
# =====================================================

class TestInscription(BaseCustomerTestCase):

    def test_page_inscription_accessible(self):
        response = self.client.get(reverse("guests_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "register.html")

    def test_inscription_complete_reussie(self):
        image = Image.new("RGB", (100, 100))
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)

        photo = SimpleUploadedFile(
            "photo.jpg", buf.getvalue(), content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("inscription"),
            {
                "nom": "Dupont",
                "prenoms": "Jean",
                "username": "newuser",
                "email": "newuser@test.com",
                "phone": "0708090605",
                "ville": self.ville.id,
                "adresse": "Test",
                "password": "Password123",
                "passwordconf": "Password123",
                "file": photo,
            }
        )

        self.assertTrue(response.json()["success"])
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertTrue(Customer.objects.filter(user__username="newuser").exists())

    def test_inscription_passwords_differents(self):
        response = self.client.post(
            reverse("inscription"),
            {
                "nom": "Test",
                "prenoms": "User",
                "username": "user2",
                "email": "user2@test.com",
                "phone": "0708090605",
                "ville": self.ville.id,
                "adresse": "Test",
                "password": "Password123",
                "passwordconf": "DifferentPassword",
            }
        )

        self.assertFalse(response.json()["success"])


# =====================================================
# MOT DE PASSE OUBLIÉ
# =====================================================

class TestMotDePasseOublie(BaseCustomerTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="resetuser",
            email="reset@test.com",
            password="OldPassword123"
        )

    def test_page_forgot_password_accessible(self):
        response = self.client.get(reverse("forgot_password"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "forgot-password.html")

    def test_token_expire_apres_1h(self):
        token = PasswordResetToken.objects.create(
            user=self.user, token="testtoken"
        )

        token.created_at = datetime.now() - timedelta(hours=2)
        token.save()
        token.refresh_from_db()

        self.assertFalse(token.is_valid())


# =====================================================
# PANIER
# =====================================================

class TestGestionPanier(BaseCustomerTestCase):

    def setUp(self):
        super().setUp()

        self.user = User.objects.create_user(
            username="cartuser",
            password="Password123"
        )
        self.customer = Customer.objects.create(
            user=self.user,
            adresse="Test",
            contact_1="0708090605",
            ville=self.ville
        )

        self.client.login(username="cartuser", password="Password123")

        self.panier = Panier.objects.create(customer=self.customer)

        cat_etab = CategorieEtablissement.objects.create(nom="Market", status=True)
        etab = Etablissement.objects.create(
            nom="Shop CI",
            ville=self.ville,
            categorie=cat_etab,
            user=self.user,
            status=True
        )

        cat_prod = CategorieProduit.objects.create(nom="Tech", status=True)
        self.produit = Produit.objects.create(
            nom="Produit Test",
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


# =====================================================
# CODE PROMOTIONNEL
# =====================================================

class TestCodePromotionnel(BaseCustomerTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="promo", password="Password123"
        )
        self.customer = Customer.objects.create(
            user=self.user,
            adresse="Test",
            contact_1="0708090605",
            ville=self.ville
        )

        self.client.login(username="promo", password="Password123")
        self.panier = Panier.objects.create(customer=self.customer)

        self.code = CodePromotionnel.objects.create(
            libelle="Promo",
            etat=True,
            date_fin=datetime.now().date() + timedelta(days=5),
            reduction=0.1,
            nombre_u=10,
            code_promo="PROMO10"
        )

    def test_application_code_valide(self):
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
# DÉCONNEXION
# =====================================================

class TestDeconnexion(BaseCustomerTestCase):

    def test_deconnexion_reussie(self):
        user = User.objects.create_user(
            username="logout", password="Password123"
        )
        self.client.login(username="logout", password="Password123")

        response = self.client.get(reverse("deconnexion"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)
