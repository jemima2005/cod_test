from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from customer.models import Customer, Panier, ProduitPanier, CodePromotionnel
from shop.models import Produit, CategorieProduit, Etablissement, CategorieEtablissement
from cities_light.models import City, Country
import json
from datetime import datetime, timedelta


class BasePerformanceTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.country = Country.objects.create(
            name="Côte d'Ivoire", code2="CI", code3="CIV"
        )
        self.ville = City.objects.create(
            name="Abidjan", country=self.country, display_name="Abidjan, CI"
        )


# =====================================================
# AUTHENTIFICATION — REQUÊTES SQL
# =====================================================

@override_settings(DEBUG=True)
class TestPerformanceAuth(BasePerformanceTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="perf", password="Pass123"
        )
        Customer.objects.create(
            user=self.user, adresse="T", contact_1="0708", ville=self.ville
        )

    def test_login_nombre_requetes_limite(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(
                reverse("post"),
                data=json.dumps({
                    "username": "perf",
                    "password": "Pass123"
                }),
                content_type="application/json"
            )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 10)


# =====================================================
# PANIER — ABSENCE DE N+1
# =====================================================

@override_settings(DEBUG=True)
class TestPerformancePanier(BasePerformanceTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="cart", password="Pass123"
        )
        self.customer = Customer.objects.create(
            user=self.user, adresse="T", contact_1="0708", ville=self.ville
        )
        self.panier = Panier.objects.create(customer=self.customer)
        self.client.login(username="cart", password="Pass123")

        cat_etab = CategorieEtablissement.objects.create(nom="T", status=True)
        etab = Etablissement.objects.create(
            nom="T", ville=self.ville,
            categorie=cat_etab, user=self.user, status=True
        )
        cat_prod = CategorieProduit.objects.create(nom="T", status=True)

        self.produits = []
        for i in range(20):
            p = Produit.objects.create(
                nom=f"P{i}", prix=1000, quantite=10,
                categorie=cat_prod, etablissement=etab, status=True
            )
            self.produits.append(p)
            ProduitPanier.objects.create(
                panier=self.panier, produit=p, quantite=1
            )

    def test_calcul_total_sans_n_plus_1(self):
        with CaptureQueriesContext(connection) as ctx:
            total = self.panier.total

        self.assertEqual(total, 20000)
        self.assertLessEqual(len(ctx), 5)


# =====================================================
# CODE PROMO — STABILITÉ
# =====================================================

@override_settings(DEBUG=True)
class TestPerformanceCodePromo(BasePerformanceTestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="promo", password="Pass123"
        )
        self.customer = Customer.objects.create(
            user=self.user, adresse="T", contact_1="0708", ville=self.ville
        )
        self.panier = Panier.objects.create(customer=self.customer)
        self.client.login(username="promo", password="Pass123")

        for i in range(20):
            CodePromotionnel.objects.create(
                libelle=f"Promo{i}",
                etat=True,
                date_fin=datetime.now().date() + timedelta(days=5),
                reduction=0.10,
                nombre_u=100,
                code_promo=f"CODE{i}"
            )

    def test_application_code_requetes_constantes(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(
                reverse("add_coupon"),
                data=json.dumps({
                    "panier": self.panier.id,
                    "coupon": "CODE10"
                }),
                content_type="application/json"
            )

        self.assertTrue(response.json()["success"])
        self.assertLessEqual(len(ctx), 10)


# =====================================================
# VOLUME DE DONNÉES
# =====================================================

@override_settings(DEBUG=True)
class TestPerformanceVolume(BasePerformanceTestCase):

    def test_login_independant_volume_users(self):
        for i in range(100):
            user = User.objects.create_user(
                username=f"user{i}", password="Pass123"
            )
            Customer.objects.create(
                user=user, adresse="T", contact_1="07", ville=self.ville
            )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(
                reverse("post"),
                data=json.dumps({
                    "username": "user50",
                    "password": "Pass123"
                }),
                content_type="application/json"
            )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 10)
