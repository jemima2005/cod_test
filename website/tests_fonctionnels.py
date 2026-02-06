from django.test import TestCase
from django.urls import reverse


class TestWebsiteFonctionnels(TestCase):

    def test_page_index_accessible(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")

    def test_page_about_accessible(self):
        response = self.client.get(reverse("about"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "about-us.html")
