from django.test import LiveServerTestCase
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


# =====================================================
# PAGE CONTACT
# =====================================================

class TestPageContact(BaseInterfaceTestCase):

    def test_page_contact_accessible(self):
        self.selenium.get(f"{self.live_server_url}/contact/")
        self.assertIn("Contact", self.selenium.title)

    def test_formulaire_present(self):
        self.selenium.get(f"{self.live_server_url}/contact/")
        form = self.selenium.find_element(By.ID, "contact-form")
        self.assertTrue(form.is_displayed())


# =====================================================
# FORMULAIRE CONTACT
# =====================================================

class TestFormulaireContact(BaseInterfaceTestCase):

    def ouvrir_page(self):
        self.selenium.get(f"{self.live_server_url}/contact/")
        WebDriverWait(self.selenium, 5).until(
            EC.presence_of_element_located((By.ID, "contact-form"))
        )

    def test_champs_visibles(self):
        self.ouvrir_page()

        champs = [
            'input[placeholder*="Nom"]',
            'input[placeholder*="Email"]',
            'input[placeholder*="Sujet"]',
            'textarea[placeholder*="Message"]'
        ]

        for selector in champs:
            champ = self.selenium.find_element(By.CSS_SELECTOR, selector)
            self.assertTrue(champ.is_displayed())

    def test_remplissage_formulaire(self):
        self.ouvrir_page()

        nom = self.selenium.find_element(By.CSS_SELECTOR, 'input[placeholder*="Nom"]')
        email = self.selenium.find_element(By.CSS_SELECTOR, 'input[placeholder*="Email"]')
        sujet = self.selenium.find_element(By.CSS_SELECTOR, 'input[placeholder*="Sujet"]')
        message = self.selenium.find_element(By.CSS_SELECTOR, 'textarea[placeholder*="Message"]')

        nom.send_keys("Test User")
        email.send_keys("test@example.com")
        sujet.send_keys("Sujet")
        message.send_keys("Message test")

        self.assertEqual(nom.get_attribute("value"), "Test User")
        self.assertEqual(email.get_attribute("value"), "test@example.com")

    def test_soumission_affiche_message_succes(self):
        self.ouvrir_page()

        self.selenium.find_element(By.CSS_SELECTOR, 'input[placeholder*="Nom"]').send_keys("UI Test")
        self.selenium.find_element(By.CSS_SELECTOR, 'input[placeholder*="Email"]').send_keys("ui@test.com")
        self.selenium.find_element(By.CSS_SELECTOR, 'input[placeholder*="Sujet"]').send_keys("Sujet")
        self.selenium.find_element(By.CSS_SELECTOR, 'textarea[placeholder*="Message"]').send_keys("Message")

        self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        WebDriverWait(self.selenium, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
        )


# =====================================================
# INTERACTIONS UTILISATEUR
# =====================================================

class TestInteractionUtilisateur(BaseInterfaceTestCase):

    def test_focus_premier_champ(self):
        self.selenium.get(f"{self.live_server_url}/contact/")

        nom = self.selenium.find_element(By.CSS_SELECTOR, 'input[placeholder*="Nom"]')
        nom.click()

        self.assertEqual(self.selenium.switch_to.active_element, nom)

    def test_navigation_tabulation(self):
        self.selenium.get(f"{self.live_server_url}/contact/")

        nom = self.selenium.find_element(By.CSS_SELECTOR, 'input[placeholder*="Nom"]')
        nom.click()
        nom.send_keys(Keys.TAB)

        self.assertNotEqual(self.selenium.switch_to.active_element, nom)
