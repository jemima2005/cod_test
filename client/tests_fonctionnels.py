from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from customer.models import Customer, Commande, ProduitPanier
from shop.models import Produit, CategorieProduit, Favorite, Etablissement, CategorieEtablissement
from cities_light.models import City, Country
from io import BytesIO
from PIL import Image


class BaseFunctionalTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.country = Country.objects.create(name="Côte d'Ivoire", code2="CI", code3="CIV")
        self.ville = City.objects.create(name="Abidjan", country=self.country)

        self.user = User.objects.create_user(
            username="testuser@test.com",
            password="Password123!",
            first_name="Jean",
            last_name="Dupont"
        )

        image = Image.new("RGB", (100, 100))
        buf = BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)

        self.customer = Customer.objects.create(
            user=self.user,
            contact_1="0708090605",
            ville=self.ville,
            photo=SimpleUploadedFile("photo.jpg", buf.getvalue(), content_type="image/jpeg")
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

        self.produit1 = Produit.objects.create(
            nom="Smartphone Samsung",
            prix=250000,
            quantite=10,
            categorie=cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.produit2 = Produit.objects.create(
            nom="Écouteurs Bluetooth",
            prix=15000,
            quantite=50,
            categorie=cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.commande1 = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY001",
            transaction_id="TXN001",
            prix_total=265000,
            status=True
        )

        self.commande2 = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY002",
            transaction_id="TXN002",
            prix_total=15000,
            status=True
        )

        ProduitPanier.objects.create(produit=self.produit1, commande=self.commande1, quantite=1)
        ProduitPanier.objects.create(produit=self.produit2, commande=self.commande1, quantite=1)
        ProduitPanier.objects.create(produit=self.produit2, commande=self.commande2, quantite=1)

        Favorite.objects.create(user=self.user, produit=self.produit1)

    def login(self):
        self.client.login(username="testuser@test.com", password="Password123!")


# =====================
# PROFIL
# =====================

class TestProfil(BaseFunctionalTestCase):

    def test_profil_redirige_si_non_connecte(self):
        response = self.client.get(reverse("profil"))
        self.assertEqual(response.status_code, 302)

    def test_profil_accessible_connecte(self):
        self.login()
        response = self.client.get(reverse("profil"))
        self.assertEqual(response.status_code, 200)

    def test_infos_personnelles_affichees(self):
        self.login()
        response = self.client.get(reverse("profil"))
        self.assertEqual(response.context["user"].first_name, "Jean")
        self.assertEqual(response.context["user"].last_name, "Dupont")

    def test_dernieres_commandes_limitees_a_5(self):
        self.login()
        for i in range(10):
            Commande.objects.create(
                customer=self.customer,
                id_paiment=f"PAYX{i}",
                transaction_id=f"TXNX{i}",
                prix_total=1000,
                status=True
            )

        response = self.client.get(reverse("profil"))
        self.assertLessEqual(len(response.context["dernieres_commandes"]), 5)


# =====================
# COMMANDES
# =====================

class TestCommandes(BaseFunctionalTestCase):

    def test_liste_commandes_accessible(self):
        self.login()
        response = self.client.get(reverse("commande"))
        self.assertEqual(response.status_code, 200)

    def test_commandes_affichees(self):
        self.login()
        response = self.client.get(reverse("commande"))
        self.assertContains(response, "TXN001")
        self.assertContains(response, "TXN002")

    def test_recherche_par_transaction(self):
        self.login()
        response = self.client.get(reverse("commande") + "?q=TXN001")
        self.assertContains(response, "TXN001")
        self.assertNotContains(response, "TXN002")


# =====================
# DETAIL COMMANDE
# =====================

class TestDetailCommande(BaseFunctionalTestCase):

    def test_detail_commande_accessible(self):
        self.login()
        response = self.client.get(
            reverse("commande-detail", args=[self.commande1.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_affiche_infos(self):
        self.login()
        response = self.client.get(
            reverse("commande-detail", args=[self.commande1.id])
        )
        self.assertContains(response, "PAY001")
        self.assertContains(response, "TXN001")

    def test_produits_commande_affiches(self):
        self.login()
        response = self.client.get(
            reverse("commande-detail", args=[self.commande1.id])
        )
        self.assertContains(response, "Smartphone Samsung")
        self.assertContains(response, "Écouteurs Bluetooth")


# =====================
# FAVORIS
# =====================

class TestFavoris(BaseFunctionalTestCase):

    def test_liste_favoris_accessible(self):
        self.login()
        response = self.client.get(reverse("liste-souhait"))
        self.assertEqual(response.status_code, 200)

    def test_favoris_affiches(self):
        self.login()
        response = self.client.get(reverse("liste-souhait"))
        self.assertContains(response, "Smartphone Samsung")

    def test_liste_vide_affiche_message(self):
        Favorite.objects.all().delete()
        self.login()
        response = self.client.get(reverse("liste-souhait"))
        self.assertContains(response, "aucun produit")


# =====================
# PARAMETRES
# =====================

class TestParametres(BaseFunctionalTestCase):

    def test_page_parametres_accessible(self):
        self.login()
        response = self.client.get(reverse("parametre"))
        self.assertEqual(response.status_code, 200)

    def test_formulaire_pre_rempli(self):
        self.login()
        response = self.client.get(reverse("parametre"))
        self.assertContains(response, "Jean")
        self.assertContains(response, "Dupont")

    def test_modification_nom_prenom(self):
        self.login()
        self.client.post(reverse("parametre"), {
            "first_name": "Pierre",
            "last_name": "Martin",
            "contact": "0708090605",
            "city": self.ville.id
        })

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Pierre")
        self.assertEqual(self.user.last_name, "Martin")


# =====================
# PDF COMMANDE
# =====================

class TestPDF(BaseFunctionalTestCase):

    def test_generation_pdf_commande(self):
        self.login()
        response = self.client.get(
            reverse("invoice_pdf", args=[self.commande1.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertGreater(len(response.content), 100)
