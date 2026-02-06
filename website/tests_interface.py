from django.test import TestCase
from django.urls import reverse


class TestWebsiteInterface(TestCase):

    def test_index_contient_sections_cles(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, "Nos produits")
        self.assertContains(response, "Pourquoi nous choisir")
        self.assertContains(response, "Nos partenaires")

    def test_about_contient_titre(self):
        response = self.client.get(reverse("about"))
        self.assertContains(response, "À propos")
