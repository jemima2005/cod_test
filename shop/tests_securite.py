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


class BaseShopSecurityTestCase(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

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

        self.vendeur1 = User.objects.create_user(
            username="v1", password="Pass123"
        )
        self.vendeur2 = User.objects.create_user(
            username="v2", password="Pass123"
        )

        img = Image.new("RGB", (50, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        logo = SimpleUploadedFile(
            "logo.jpg", buf.getvalue(), content_type="image/jpeg"
        )

        self.etab1 = Etablissement.objects.create(
            user=self.vendeur1,
            nom="Shop1",
            categorie=self.cat_etab,
            ville=self.ville,
            adresse="T",
            contact_1="07",
            email="s1@test.com",
            logo=logo,
            status=True
        )

        self.etab2 = Etablissement.objects.create(
            user=self.vendeur2,
            nom="Shop2",
            categorie=self.cat_etab,
            ville=self.ville,
            adresse="T",
            contact_1="08",
            email="s2@test.com",
            logo=logo,
            status=True
        )


# =====================================================
# AUTORISATIONS VENDEURS
# =====================================================

class TestAutorisationVendeur(BaseShopSecurityTestCase):

    def test_vendeur_ne_modifie_pas_article_autrui(self):
        produit = Produit.objects.create(
            nom="P",
            prix=1000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etab2,
            status=True
        )

        self.client.login(username="v1", password="Pass123")

        self.client.post(
            reverse("modifier", args=[produit.id]),
            {"nom": "Hack", "prix": 1, "quantite": 1}
        )

        produit.refresh_from_db()
        self.assertEqual(produit.nom, "P")

    def test_vendeur_ne_supprime_pas_article_autrui(self):
        produit = Produit.objects.create(
            nom="Del",
            prix=1000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etab2,
            status=True
        )

        self.client.login(username="v1", password="Pass123")
        self.client.post(reverse("supprimer-article", args=[produit.id]))

        self.assertTrue(
            Produit.objects.filter(id=produit.id).exists()
        )


# =====================================================
# VALIDATION DONNÉES MÉTIER
# =====================================================

class TestValidationDonnees(BaseShopSecurityTestCase):

    def test_prix_negatif_refuse(self):
        self.client.login(username="v1", password="Pass123")

        response = self.client.post(
            reverse("ajout-article"),
            {
                "nom": "Neg",
                "prix": -100,
                "quantite": 5,
                "categorie": self.cat_prod.id
            }
        )

        self.assertFalse(
            Produit.objects.filter(nom="Neg").exists()
        )

    def test_quantite_negative_refusee(self):
        self.client.login(username="v1", password="Pass123")

        response = self.client.post(
            reverse("ajout-article"),
            {
                "nom": "NegQ",
                "prix": 1000,
                "quantite": -5,
                "categorie": self.cat_prod.id
            }
        )

        self.assertFalse(
            Produit.objects.filter(nom="NegQ").exists()
        )


# =====================================================
# XSS (RENDU)
# =====================================================

class TestXSSShop(BaseShopSecurityTestCase):

    def test_script_non_rendu(self):
        payload = '<script>alert("XSS")</script>'

        produit = Produit.objects.create(
            nom=payload,
            prix=1000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etab1,
            status=True
        )

        response = self.client.get(
            reverse("product_detail", args=[produit.slug])
        )

        self.assertNotContains(response, payload)


# =====================================================
# UPLOAD FICHIERS
# =====================================================

class TestUploadSecurity(BaseShopSecurityTestCase):

    def test_fichier_non_image_refuse(self):
        self.client.login(username="v1", password="Pass123")

        fichier = SimpleUploadedFile(
            "evil.php",
            b"<?php echo 'hack'; ?>",
            content_type="application/x-php"
        )

        self.client.post(
            reverse("ajout-article"),
            {
                "nom": "Hack",
                "prix": 1000,
                "quantite": 5,
                "categorie": self.cat_prod.id,
                "image": fichier
            }
        )

        self.assertFalse(
            Produit.objects.filter(nom="Hack").exists()
        )


# =====================================================
# FAVORIS
# =====================================================

class TestFavorisSecurity(BaseShopSecurityTestCase):

    def test_pas_de_doublon_favori(self):
        user = User.objects.create_user(
            username="client", password="Pass123"
        )
        Customer.objects.create(
            user=user,
            adresse="T",
            contact_1="07",
            ville=self.ville
        )

        produit = Produit.objects.create(
            nom="Fav",
            prix=1000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etab1,
            status=True
        )

        self.client.login(username="client", password="Pass123")

        self.client.get(reverse("toggle_favorite", args=[produit.id]))
        self.client.get(reverse("toggle_favorite", args=[produit.id]))

        self.assertLessEqual(
            Favorite.objects.filter(user=user, produit=produit).count(),
            1
        )


# =====================================================
# ACCÈS PROTÉGÉS
# =====================================================

class TestAccesProteges(BaseShopSecurityTestCase):

    def test_dashboard_requiert_auth(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_ajout_article_requiert_auth(self):
        response = self.client.get(reverse("ajout-article"))
        self.assertEqual(response.status_code, 302)
