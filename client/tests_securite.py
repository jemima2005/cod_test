from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from customer.models import Customer, Commande
from shop.models import Produit, CategorieProduit, Favorite, Etablissement, CategorieEtablissement
from cities_light.models import City, Country
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io


class BaseSecurityTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.country = Country.objects.create(name="Côte d'Ivoire", code2="CI", code3="CIV")
        self.ville = City.objects.create(name="Abidjan", country=self.country)

        self.user1 = User.objects.create_user(
            username="user1@test.com",
            password="Password123!"
        )
        self.user2 = User.objects.create_user(
            username="user2@test.com",
            password="Password123!"
        )

        self.customer1 = Customer.objects.create(
            user=self.user1,
            contact_1="0101010101",
            ville=self.ville
        )
        self.customer2 = Customer.objects.create(
            user=self.user2,
            contact_1="0202020202",
            ville=self.ville
        )

        cat_etab = CategorieEtablissement.objects.create(nom="Market", status=True)
        etab = Etablissement.objects.create(
            nom="Market CI",
            ville=self.ville,
            categorie=cat_etab,
            user=self.user1,
            status=True
        )

        cat_prod = CategorieProduit.objects.create(nom="Tech", status=True)
        self.produit = Produit.objects.create(
            nom="Smartphone",
            prix=100000,
            quantite=10,
            categorie=cat_prod,
            etablissement=etab,
            status=True
        )

        self.commande1 = Commande.objects.create(
            customer=self.customer1,
            id_paiment="PAY001",
            transaction_id="TXN001",
            prix_total=100000,
            status=True
        )

        self.commande2 = Commande.objects.create(
            customer=self.customer2,
            id_paiment="PAY002",
            transaction_id="TXN002",
            prix_total=50000,
            status=True
        )

        Favorite.objects.create(user=self.user1, produit=self.produit)


# =========================
# AUTHENTIFICATION / SESSION
# =========================

class TestAuthentification(BaseSecurityTestCase):

    def test_pages_protegees_sans_login(self):
        urls = [
            reverse('profil'),
            reverse('commande'),
            reverse('commande-detail', args=[self.commande1.id]),
            reverse('liste-souhait'),
            reverse('parametre'),
            reverse('invoice_pdf', args=[self.commande1.id]),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [302, 403])

    def test_deconnexion_bloque_acces(self):
        self.client.login(username="user1@test.com", password="Password123!")
        self.client.logout()
        response = self.client.get(reverse('profil'))
        self.assertEqual(response.status_code, 302)


# =========================
# AUTORISATION / IDOR
# =========================

class TestAutorisation(BaseSecurityTestCase):

    def test_commande_autre_utilisateur_inaccessible(self):
        self.client.login(username="user1@test.com", password="Password123!")
        response = self.client.get(
            reverse('commande-detail', args=[self.commande2.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_pdf_autre_utilisateur_refuse(self):
        self.client.login(username="user1@test.com", password="Password123!")
        response = self.client.get(
            reverse('invoice_pdf', args=[self.commande2.id])
        )
        self.assertNotEqual(response.status_code, 200)

    def test_liste_commandes_isolee(self):
        self.client.login(username="user1@test.com", password="Password123!")
        response = self.client.get(reverse('commande'))
        self.assertContains(response, 'TXN001')
        self.assertNotContains(response, 'TXN002')


# =========================
# CSRF (VRAI TEST)
# =========================

class TestCSRF(BaseSecurityTestCase):

    def setUp(self):
        super().setUp()
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username="user1@test.com", password="Password123!")

    def test_post_sans_csrf_refuse(self):
        response = self.client.post(reverse('parametre'), {
            'first_name': 'Test',
            'contact': '0101010101',
            'city': self.ville.id,
        })
        self.assertEqual(response.status_code, 403)


# =========================
# SQL INJECTION
# =========================

class TestSQLInjection(BaseSecurityTestCase):

    def test_injection_sql_ne_divulgue_rien(self):
        self.client.login(username="user1@test.com", password="Password123!")
        response = self.client.get(reverse('commande'), {
            'q': "' OR 1=1 --"
        })

        content = response.content.decode()
        self.assertNotIn('TXN002', content)
        self.assertNotIn('user2@test.com', content)


# =========================
# XSS
# =========================

class TestXSS(BaseSecurityTestCase):

    def test_xss_echappe(self):
        self.client.login(username="user1@test.com", password="Password123!")

        payload = '<script>alert("XSS")</script>'
        self.client.post(reverse('parametre'), {
            'first_name': payload,
            'contact': '0101010101',
            'city': self.ville.id,
        })

        response = self.client.get(reverse('profil'))
        self.assertNotContains(response, payload)
        self.assertContains(response, '&lt;script&gt;')


# =========================
# UPLOAD FICHIERS
# =========================

class TestUpload(BaseSecurityTestCase):

    def test_upload_php_rejete(self):
        self.client.login(username="user1@test.com", password="Password123!")

        php_file = SimpleUploadedFile(
            "shell.php",
            b"<?php echo 'hack'; ?>",
            content_type="application/x-php"
        )

        self.client.post(reverse('parametre'), {
            'first_name': 'Test',
            'contact': '0101010101',
            'city': self.ville.id,
            'profile_picture': php_file
        })

        self.customer1.refresh_from_db()
        self.assertFalse(self.customer1.photo)

    def test_upload_image_valide_accepte(self):
        self.client.login(username="user1@test.com", password="Password123!")

        img = Image.new('RGB', (100, 100))
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)

        image_file = SimpleUploadedFile(
            "photo.jpg",
            buf.getvalue(),
            content_type="image/jpeg"
        )

        self.client.post(reverse('parametre'), {
            'first_name': 'Test',
            'contact': '0101010101',
            'city': self.ville.id,
            'profile_picture': image_file
        })

        self.customer1.refresh_from_db()
        self.assertTrue(self.customer1.photo)

    def test_upload_trop_gros_rejete(self):
        self.client.login(username="user1@test.com", password="Password123!")

        big_file = SimpleUploadedFile(
            "big.jpg",
            b"x" * (20 * 1024 * 1024),
            content_type="image/jpeg"
        )

        self.client.post(reverse('parametre'), {
            'first_name': 'Test',
            'contact': '0101010101',
            'city': self.ville.id,
            'profile_picture': big_file
        })

        self.customer1.refresh_from_db()
        self.assertFalse(self.customer1.photo)


# =========================
# VALIDATION DES ENTREES
# =========================

class TestValidation(BaseSecurityTestCase):

    def test_numero_invalide_refuse(self):
        self.client.login(username="user1@test.com", password="Password123!")

        self.client.post(reverse('parametre'), {
            'first_name': 'Test',
            'contact': 'ABC123',
            'city': self.ville.id,
        })

        self.customer1.refresh_from_db()
        self.assertNotEqual(self.customer1.contact_1, 'ABC123')

    def test_ville_inexistante_refusee(self):
        self.client.login(username="user1@test.com", password="Password123!")

        response = self.client.post(reverse('parametre'), {
            'first_name': 'Test',
            'contact': '0101010101',
            'city': 999999,
        })

        self.assertNotEqual(response.status_code, 302)
