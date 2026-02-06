from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from customer.models import (
    Customer, Panier, ProduitPanier,
    CodePromotionnel, PasswordResetToken
)
from shop.models import Produit, CategorieProduit, Etablissement, CategorieEtablissement
from cities_light.models import City, Country
import json
from datetime import datetime, timedelta


class BaseSecurityTestCase(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.country = Country.objects.create(
            name="Côte d'Ivoire", code2="CI", code3="CIV"
        )
        self.ville = City.objects.create(
            name="Abidjan", country=self.country, display_name="Abidjan, CI"
        )


# =====================================================
# CSRF
# =====================================================

class TestCSRF(BaseSecurityTestCase):

    def test_post_login_sans_csrf_refuse(self):
        response = self.client.post(
            reverse("post"),
            data=json.dumps({"username": "x", "password": "y"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)


# =====================================================
# SQL INJECTION (INTÉGRITÉ DB)
# =====================================================

class TestSQLInjection(BaseSecurityTestCase):

    def test_injection_sql_ne_casse_pas_db(self):
        payload = "'; DROP TABLE auth_user; --"

        response = self.client.post(
            reverse("post"),
            data=json.dumps({
                "username": payload,
                "password": payload
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username__isnull=False).exists())


# =====================================================
# XSS (NON-RÉFLEXION)
# =====================================================

class TestXSS(BaseSecurityTestCase):

    def test_xss_non_reflechi_login(self):
        payload = '<script>alert("XSS")</script>'

        response = self.client.post(
            reverse("post"),
            data=json.dumps({
                "username": payload,
                "password": payload
            }),
            content_type="application/json"
        )

        content = response.content.decode()
        self.assertNotIn(payload, content)


# =====================================================
# AUTHENTIFICATION
# =====================================================

class TestAuthSecurity(BaseSecurityTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="auth", password="Strong123!"
        )
        Customer.objects.create(
            user=self.user, adresse="T", contact_1="0708", ville=self.ville
        )

    def test_multiples_echecs_login(self):
        for _ in range(5):
            response = self.client.post(
                reverse("post"),
                data=json.dumps({
                    "username": "auth",
                    "password": "wrong"
                }),
                content_type="application/json"
            )
            self.assertFalse(response.json()["success"])


# =====================================================
# PANIER (AUTORISATION)
# =====================================================

class TestPanierSecurity(BaseSecurityTestCase):

    def setUp(self):
        super().setUp()

        self.user1 = User.objects.create_user(username="u1", password="P123")
        self.customer1 = Customer.objects.create(
            user=self.user1, adresse="T", contact_1="0708", ville=self.ville
        )
        self.panier1 = Panier.objects.create(customer=self.customer1)

        self.user2 = User.objects.create_user(username="u2", password="P123")
        self.customer2 = Customer.objects.create(
            user=self.user2, adresse="T", contact_1="0709", ville=self.ville
        )
        self.panier2 = Panier.objects.create(customer=self.customer2)

        cat_etab = CategorieEtablissement.objects.create(nom="T", status=True)
        etab = Etablissement.objects.create(
            nom="T", ville=self.ville,
            categorie=cat_etab, user=self.user1, status=True
        )
        cat_prod = CategorieProduit.objects.create(nom="T", status=True)
        self.produit = Produit.objects.create(
            nom="P", prix=1000, quantite=10,
            categorie=cat_prod, etablissement=etab, status=True
        )

        self.client.login(username="u1", password="P123")

    def test_acces_panier_autrui_refuse(self):
        response = self.client.post(
            reverse("add_to_cart"),
            data=json.dumps({
                "panier": self.panier2.id,
                "produit": self.produit.id,
                "quantite": 1
            }),
            content_type="application/json"
        )

        self.assertFalse(
            ProduitPanier.objects.filter(
                panier=self.panier2, produit=self.produit
            ).exists()
        )

    def test_quantite_negative_refusee(self):
        response = self.client.post(
            reverse("add_to_cart"),
            data=json.dumps({
                "panier": self.panier1.id,
                "produit": self.produit.id,
                "quantite": -5
            }),
            content_type="application/json"
        )

        self.assertFalse(response.json()["success"])


# =====================================================
# PASSWORD RESET
# =====================================================

class TestPasswordResetSecurity(BaseSecurityTestCase):

    def test_token_expire(self):
        user = User.objects.create_user(
            username="reset", password="Old123"
        )

        token = PasswordResetToken.objects.create(
            user=user, token="exp"
        )
        token.created_at = datetime.now() - timedelta(hours=2)
        token.save()
        token.refresh_from_db()

        self.assertFalse(token.is_valid())


# =====================================================
# VALIDATION EMAIL
# =====================================================

class TestValidationEmail(BaseSecurityTestCase):

    def test_email_invalide_refuse(self):
        emails = ["invalid", "@ex.com", "u@"]

        for email in emails:
            response = self.client.post(
                reverse("inscription"),
                {
                    "nom": "T",
                    "prenoms": "U",
                    "username": "t",
                    "email": email,
                    "phone": "0708",
                    "ville": self.ville.id,
                    "adresse": "T",
                    "password": "Password123",
                    "passwordconf": "Password123"
                }
            )

            self.assertFalse(response.json()["success"])
