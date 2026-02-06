from django.test import LiveServerTestCase
from django.contrib.auth.models import User
from customer.models import Customer
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
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        cls.selenium = webdriver.Chrome(options=options)
        cls.selenium.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        self.country = Country.objects.create(
            name="Côte d'Ivoire", code2="CI", code3="CIV"
        )
        self.ville = City.objects.create(
            name="Abidjan", country=self.country, display_name="Abidjan, CI"
        )


# =====================================================
# LOGIN
# =====================================================

class TestLoginUI(BaseInterfaceTestCase):

    def test_page_login_accessible(self):
        self.selenium.get(f"{self.live_server_url}/customer/")
        self.assertIn("login", self.selenium.current_url.lower())

    def test_formulaire_login_present(self):
        self.selenium.get(f"{self.live_server_url}/customer/")
        form = self.selenium.find_element(By.TAG_NAME, "form")
        self.assertTrue(form.is_displayed())

    def test_champs_login_visibles(self):
        self.selenium.get(f"{self.live_server_url}/customer/")
        self.assertTrue(self.selenium.find_element(By.NAME, "username").is_displayed())
        self.assertTrue(self.selenium.find_element(By.NAME, "password").is_displayed())

    def test_login_reussi_redirection(self):
        user = User.objects.create_user(
            username="uitest", password="Pass123"
        )
        Customer.objects.create(
            user=user, adresse="Test", contact_1="0708", ville=self.ville
        )

        self.selenium.get(f"{self.live_server_url}/customer/")
        self.selenium.find_element(By.NAME, "username").send_keys("uitest")
        self.selenium.find_element(By.NAME, "password").send_keys("Pass123")
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(self.selenium, 5).until(
            lambda d: "login" not in d.current_url.lower()
        )

    def test_login_echec_message_erreur(self):
        self.selenium.get(f"{self.live_server_url}/customer/")
        self.selenium.find_element(By.NAME, "username").send_keys("wrong")
        self.selenium.find_element(By.NAME, "password").send_keys("wrong")
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(self.selenium, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert-danger"))
        )


# =====================================================
# INSCRIPTION
# =====================================================

class TestInscriptionUI(BaseInterfaceTestCase):

    def test_page_inscription_accessible(self):
        self.selenium.get(f"{self.live_server_url}/customer/signup")
        self.assertIn("signup", self.selenium.current_url.lower())

    def test_champs_inscription_presents(self):
        self.selenium.get(f"{self.live_server_url}/customer/signup")

        champs = [
            "nom", "prenoms", "username",
            "email", "phone", "password", "passwordconf"
        ]

        for champ in champs:
            element = self.selenium.find_element(By.NAME, champ)
            self.assertTrue(element.is_displayed())

    def test_navigation_signup_vers_login(self):
        self.selenium.get(f"{self.live_server_url}/customer/signup")
        link = self.selenium.find_element(By.PARTIAL_LINK_TEXT, "connexion")
        link.click()

        WebDriverWait(self.selenium, 5).until(
            lambda d: "login" in d.current_url.lower()
        )


# =====================================================
# NAVIGATION
# =====================================================

class TestNavigationUI(BaseInterfaceTestCase):

    def test_navigation_login_vers_inscription(self):
        self.selenium.get(f"{self.live_server_url}/customer/")
        link = self.selenium.find_element(By.PARTIAL_LINK_TEXT, "inscription")
        link.click()

        WebDriverWait(self.selenium, 5).until(
            lambda d: "signup" in d.current_url.lower()
        )


# =====================================================
# INTERACTIONS
# =====================================================

class TestInteractionsUI(BaseInterfaceTestCase):

    def test_focus_champ_username(self):
        self.selenium.get(f"{self.live_server_url}/customer/")
        username = self.selenium.find_element(By.NAME, "username")
        username.click()

        self.assertEqual(self.selenium.switch_to.active_element, username)

    def test_tabulation(self):
        self.selenium.get(f"{self.live_server_url}/customer/")
        username = self.selenium.find_element(By.NAME, "username")
        username.click()
        username.send_keys(Keys.TAB)

        self.assertNotEqual(self.selenium.switch_to.active_element, username)
