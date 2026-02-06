from django.test import LiveServerTestCase
from django.contrib.auth.models import User
from shop.models import CategorieEtablissement, CategorieProduit, Etablissement, Produit
from customer.models import Customer
from cities_light.models import City, Country
from django.core.files.uploadedfile import SimpleUploadedFile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io


class BaseInterfaceTestCase(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        cls.selenium = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.selenium, 10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
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
            adresse="T",
            contact_1="07",
            email="shop@test.com",
            logo=logo,
            status=True
        )


# =====================================================
# PAGE SHOP
# =====================================================

class TestShopPage(BaseInterfaceTestCase):

    def test_shop_page_accessible(self):
        self.selenium.get(f"{self.live_server_url}/shop/")
        self.wait.until(EC.url_contains("/shop"))
        self.assertIn("/shop", self.selenium.current_url)

    def test_produit_affiche(self):
        Produit.objects.create(
            nom="Produit UI",
            prix=1000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

        self.selenium.get(f"{self.live_server_url}/shop/")
        self.wait.until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Produit UI"))
        )


# =====================================================
# DETAIL PRODUIT
# =====================================================

class TestDetailProduitUI(BaseInterfaceTestCase):

    def setUp(self):
        super().setUp()
        self.produit = Produit.objects.create(
            nom="Detail UI",
            prix=2000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

    def test_page_detail_accessible(self):
        self.selenium.get(
            f"{self.live_server_url}/shop/produit/{self.produit.slug}"
        )
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        self.assertIn(self.produit.slug, self.selenium.current_url)


# =====================================================
# FAVORIS
# =====================================================

class TestFavorisUI(BaseInterfaceTestCase):

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

        self.produit = Produit.objects.create(
            nom="Fav UI",
            prix=3000,
            quantite=5,
            categorie=self.cat_prod,
            etablissement=self.etablissement,
            status=True
        )

    def test_bouton_favori_present(self):
        self.selenium.get(
            f"{self.live_server_url}/shop/produit/{self.produit.slug}"
        )
        self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[href*="toggle_favorite"]')
            )
        )


# =====================================================
# DASHBOARD VENDEUR
# =====================================================

class TestDashboardUI(BaseInterfaceTestCase):

    def test_dashboard_requiert_auth(self):
        self.selenium.get(f"{self.live_server_url}/shop/dashboard/")
        self.assertNotIn("/dashboard", self.selenium.current_url)

    def test_dashboard_accessible_vendeur(self):
        self.selenium.get(f"{self.live_server_url}/customer/")
        self.wait.until(EC.presence_of_element_located((By.NAME, "username")))

        self.selenium.find_element(By.NAME, "username").send_keys("vendeur")
        self.selenium.find_element(By.NAME, "password").send_keys("Pass123")
        self.selenium.find_element(By.CSS_SELECTOR, "button[type=submit]").click()

        self.wait.until(EC.url_contains("/customer"))
        self.selenium.get(f"{self.live_server_url}/shop/dashboard/")
        self.wait.until(EC.url_contains("/dashboard"))
