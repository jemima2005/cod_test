from django.test import TestCase
from django.urls import reverse


class TestWebsiteSecurite(TestCase):

    def test_404_personnalisee(self):
        response = self.client.get("/page-inexistante")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")

    def test_404_ne_divulgue_pas_erreur(self):
        response = self.client.get("/page-inexistante")
        self.assertNotContains(response, "Traceback")
        self.assertNotContains(response, "Exception")

    def test_xss_non_rendu(self):
        response = self.client.get(reverse("about"))
        self.assertNotContains(response, "<script>")
