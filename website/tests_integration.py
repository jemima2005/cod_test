from django.test import TestCase
from django.urls import reverse


class TestWebsiteIntegration(TestCase):

    def test_index_sans_donnees(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

    def test_about_sans_donnees(self):
        response = self.client.get(reverse("about"))
        self.assertEqual(response.status_code, 200)
