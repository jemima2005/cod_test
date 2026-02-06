from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from contact.models import Contact, NewsLetter
import json


class BasePerformanceTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        # Données de base
        for i in range(100):
            Contact.objects.create(
                nom=f'User {i}',
                email=f'user{i}@example.com',
                sujet=f'Sujet {i}',
                message=f'Message {i}'
            )

        for i in range(50):
            NewsLetter.objects.create(
                email=f'newsletter{i}@example.com'
            )


# =====================================================
# REQUÊTES SQL (SEULE VRAIE MESURE PERTINENTE)
# =====================================================

@override_settings(DEBUG=True)
class TestRequetesSQL(BasePerformanceTestCase):

    def test_page_contact_nombre_requetes_limite(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 5)

    def test_post_contact_requetes_minimales(self):
        data = {
            'nom': 'Perf',
            'email': 'perf@test.com',
            'sujet': 'Test',
            'messages': 'Test'
        }

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(
                reverse('post_contact'),
                data=json.dumps(data),
                content_type='application/json'
            )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 3)

    def test_post_newsletter_requetes_minimales(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(
                reverse('post_newsletter'),
                data=json.dumps({'email': 'perf@test.com'}),
                content_type='application/json'
            )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 3)


# =====================================================
# STABILITÉ AVEC VOLUME DE DONNÉES
# =====================================================

@override_settings(DEBUG=True)
class TestStabiliteVolume(BasePerformanceTestCase):

    def test_page_contact_stable_avec_100_contacts(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 5)

    def test_ajout_contacts_ne_degrade_pas_requetes(self):
        # Ajouter beaucoup plus de données
        for i in range(200):
            Contact.objects.create(
                nom=f'Extra {i}',
                email=f'extra{i}@example.com',
                sujet='Extra',
                message='Extra'
            )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 5)


# =====================================================
# TAILLE DES DONNÉES (PAS LE TEMPS)
# =====================================================

class TestTailleDonnees(BasePerformanceTestCase):

    def test_message_long_accepte(self):
        message = 'A' * 10000

        response = self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': 'Long',
                'email': 'long@test.com',
                'sujet': 'Test',
                'messages': message
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.filter(email='long@test.com').count(), 1)


# =====================================================
# COHÉRENCE JSON
# =====================================================

class TestReponseJSON(BasePerformanceTestCase):

    def test_reponse_json_valide(self):
        response = self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': 'JSON',
                'email': 'json@test.com',
                'sujet': 'Test',
                'messages': 'Test'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('success', data)


# =====================================================
# ABSENCE DE N+1 (LOGIQUE)
# =====================================================

@override_settings(DEBUG=True)
class TestAbsenceNPlusOne(BasePerformanceTestCase):

    def test_nombre_requetes_independant_volume(self):
        with CaptureQueriesContext(connection) as ctx1:
            self.client.get(reverse('contact'))

        for i in range(300):
            Contact.objects.create(
                nom=f'NPlus {i}',
                email=f'nplus{i}@example.com',
                sujet='Test',
                message='Test'
            )

        with CaptureQueriesContext(connection) as ctx2:
            self.client.get(reverse('contact'))

        self.assertEqual(len(ctx1), len(ctx2))
