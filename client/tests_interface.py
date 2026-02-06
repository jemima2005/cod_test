from django.test import LiveServerTestCase
from django.contrib.auth.models import User
from customer.models import Customer, Commande, ProduitPanier
from shop.models import Produit, CategorieProduit, Favorite, Etablissement, CategorieEtablissement
from cities_light.models import City, Country

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BaseInterfaceTestCase(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        cls.selenium = webdriver.Chrome(options=options)
        cls.selenium.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        self.country = Country.objects.create(name="Côte d'Ivoire", code2="CI", code3="CIV")
        self.ville = City.objects.create(name="Abidjan", country=self.country)

        self.user = User.objects.create_user(
            username="user@test.com",
            password="Test12345"
        )

        self.customer = Customer.objects.create(
            user=self.user,
            contact_1="0700000000",
            ville=self.ville
        )

        cat_etab = CategorieEtablissement.objects.create(nom="Market", status=True)
        etab = Etablissement.objects.create(
            nom="Market CI",
            ville=self.ville,
            categorie=cat_etab,
            user=self.user,
            status=True
        )

        cat_prod = CategorieProduit.objects.create(nom="Tech", status=True)
        self.produit = Produit.objects.create(
            nom="Phone",
            prix=100000,
            quantite=10,
            categorie=cat_prod,
            etablissement=etab,
            status=True
        )

        self.commande = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY001",
            transaction_id="TXN001",
            prix_total=100000,
            status=True
        )

        ProduitPanier.objects.create(
            produit=self.produit,
            commande=self.commande,
            quantite=1
        )

        Favorite.objects.create(user=self.user, produit=self.produit)

    def login(self):
        self.selenium.get(f"{self.live_server_url}/login/")
        self.selenium.find_element(By.NAME, "username").send_keys("user@test.com")
        self.selenium.find_element(By.NAME, "password").send_keys("Test12345")
        self.selenium.find_element(By.NAME, "password").send_keys(Keys.RETURN)

        WebDriverWait(self.selenium, 5).until(
            EC.url_contains("/client")
        )


class TestNavigationUI(BaseInterfaceTestCase):

    def test_navigation_vers_commandes(self):
        self.login()

        commandes_link = WebDriverWait(self.selenium, 5).until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Commandes"))
        )
        commandes_link.click()

        WebDriverWait(self.selenium, 5).until(
            EC.url_contains("/commande")
        )

        table = self.selenium.find_element(By.TAG_NAME, "table")
        self.assertTrue(table.is_displayed())


class TestFormulaireUI(BaseInterfaceTestCase):

    def test_modification_prenom(self):
        self.login()
        self.selenium.get(f"{self.live_server_url}/client/parametre")

        first_name = WebDriverWait(self.selenium, 5).until(
            EC.presence_of_element_located((By.ID, "first_name"))
        )

        first_name.clear()
        first_name.send_keys("Pierre")

        submit = self.selenium.find_element(By.CSS_SELECTOR, "button[type=submit]")
        submit.click()

        WebDriverWait(self.selenium, 5).until(
            EC.text_to_be_present_in_element_value((By.ID, "first_name"), "Pierre")
        )


class TestPaginationUI(BaseInterfaceTestCase):

    def test_pagination_visible(self):
        self.login()
        self.selenium.get(f"{self.live_server_url}/client/commande")

        pagination = self.selenium.find_element(By.CLASS_NAME, "pagination")
        self.assertTrue(pagination.is_displayed())
