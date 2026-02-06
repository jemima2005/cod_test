from django.test import TestCase, Client
from django.urls import reverse
from contact.models import Contact, NewsLetter
import json


class BaseIntegrationTestCase(TestCase):

    def setUp(self):
        self.client = Client()


# =====================================================
# WORKFLOW CONTACT
# =====================================================

class TestWorkflowContact(BaseIntegrationTestCase):

    def post_contact(self, data):
        return self.client.post(
            reverse('post_contact'),
            data=json.dumps(data),
            content_type='application/json'
        )

    def test_workflow_contact_valide(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)

        data = {
            'nom': 'Utilisateur Test',
            'email': 'integration@test.com',
            'sujet': 'Test',
            'messages': 'Message'
        }

        response = self.post_contact(data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(Contact.objects.count(), 1)

    def test_contacts_consecutifs(self):
        for i in range(5):
            data = {
                'nom': f'User {i}',
                'email': f'user{i}@test.com',
                'sujet': f'Sujet {i}',
                'messages': f'Message {i}'
            }

            response = self.post_contact(data)
            self.assertTrue(response.json()['success'])

        contacts = Contact.objects.order_by('date_add')
        self.assertEqual(contacts.count(), 5)
        self.assertEqual(contacts.first().nom, 'User 0')
        self.assertEqual(contacts.last().nom, 'User 4')

    def test_contact_reussi_apres_echec(self):
        data = {
            'nom': 'Test',
            'email': 'email_invalide',
            'sujet': 'Test',
            'messages': 'Test'
        }

        response = self.post_contact(data)
        self.assertFalse(response.json()['success'])
        self.assertEqual(Contact.objects.count(), 0)

        data['email'] = 'valide@test.com'
        response = self.post_contact(data)
        self.assertTrue(response.json()['success'])
        self.assertEqual(Contact.objects.count(), 1)


# =====================================================
# WORKFLOW NEWSLETTER
# =====================================================

class TestWorkflowNewsletter(BaseIntegrationTestCase):

    def post_newsletter(self, email):
        return self.client.post(
            reverse('post_newsletter'),
            data=json.dumps({'email': email}),
            content_type='application/json'
        )

    def test_inscription_newsletter(self):
        response = self.post_newsletter('newsletter@test.com')
        self.assertTrue(response.json()['success'])
        self.assertEqual(NewsLetter.objects.count(), 1)

    def test_newsletter_multiple(self):
        emails = [
            'user1@test.com',
            'user2@test.com',
            'user3@test.com'
        ]

        for email in emails:
            response = self.post_newsletter(email)
            self.assertTrue(response.json()['success'])

        self.assertEqual(NewsLetter.objects.count(), 3)

    def test_newsletter_apres_echec(self):
        response = self.post_newsletter('invalide')
        self.assertFalse(response.json()['success'])
        self.assertEqual(NewsLetter.objects.count(), 0)

        response = self.post_newsletter('valide@test.com')
        self.assertTrue(response.json()['success'])
        self.assertEqual(NewsLetter.objects.count(), 1)


# =====================================================
# CONTACT + NEWSLETTER
# =====================================================

class TestContactEtNewsletter(BaseIntegrationTestCase):

    def test_contact_puis_newsletter(self):
        self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': 'Jean',
                'email': 'jean@test.com',
                'sujet': 'Question',
                'messages': 'Test'
            }),
            content_type='application/json'
        )

        self.client.post(
            reverse('post_newsletter'),
            data=json.dumps({'email': 'jean@test.com'}),
            content_type='application/json'
        )

        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(NewsLetter.objects.count(), 1)

    def test_newsletter_puis_contact(self):
        self.client.post(
            reverse('post_newsletter'),
            data=json.dumps({'email': 'user@test.com'}),
            content_type='application/json'
        )

        self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': 'User',
                'email': 'user@test.com',
                'sujet': 'Support',
                'messages': 'Help'
            }),
            content_type='application/json'
        )

        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(NewsLetter.objects.count(), 1)


# =====================================================
# COHÉRENCE DES DONNÉES
# =====================================================

class TestCoherenceDonnees(BaseIntegrationTestCase):

    def test_status_par_defaut(self):
        self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': 'Test',
                'email': 'test@test.com',
                'sujet': 'Test',
                'messages': 'Test'
            }),
            content_type='application/json'
        )

        contact = Contact.objects.first()
        self.assertTrue(contact.status)

        self.client.post(
            reverse('post_newsletter'),
            data=json.dumps({'email': 'news@test.com'}),
            content_type='application/json'
        )

        newsletter = NewsLetter.objects.first()
        self.assertTrue(newsletter.status)

    def test_format_email_preserve(self):
        emails = [
            'simple@test.com',
            'with.dot@test.com',
            'with+plus@test.com',
            'CAPS@TEST.COM'
        ]

        for email in emails:
            Contact.objects.all().delete()
            self.client.post(
                reverse('post_contact'),
                data=json.dumps({
                    'nom': 'Test',
                    'email': email,
                    'sujet': 'Test',
                    'messages': 'Test'
                }),
                content_type='application/json'
            )

            contact = Contact.objects.first()
            self.assertEqual(contact.email, email)


# =====================================================
# RÉSILIENCE
# =====================================================

class TestResilience(BaseIntegrationTestCase):

    def test_systeme_resiste_json_invalide(self):
        response = self.client.post(
            reverse('post_contact'),
            data='{"json":',
            content_type='application/json'
        )

        self.assertIn(response.status_code, [200, 400, 500])

        response = self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': 'Recovery',
                'email': 'recovery@test.com',
                'sujet': 'Test',
                'messages': 'OK'
            }),
            content_type='application/json'
        )

        self.assertTrue(response.json()['success'])

    def test_volume_contacts_raisonnable(self):
        for i in range(20):
            response = self.client.post(
                reverse('post_contact'),
                data=json.dumps({
                    'nom': f'User {i}',
                    'email': f'user{i}@test.com',
                    'sujet': 'Load',
                    'messages': 'Test'
                }),
                content_type='application/json'
            )

            self.assertTrue(response.json()['success'])

        self.assertEqual(Contact.objects.count(), 20)


# =====================================================
# INTÉGRATION ADMIN (STRUCTURE)
# =====================================================

class TestIntegrationAdmin(BaseIntegrationTestCase):

    def test_contacts_complets_pour_admin(self):
        for i in range(3):
            self.client.post(
                reverse('post_contact'),
                data=json.dumps({
                    'nom': f'Admin {i}',
                    'email': f'admin{i}@test.com',
                    'sujet': 'Admin',
                    'messages': 'Test'
                }),
                content_type='application/json'
            )

        contacts = Contact.objects.all()
        self.assertEqual(contacts.count(), 3)

        for contact in contacts:
            self.assertIsNotNone(contact.id)
            self.assertIsNotNone(contact.nom)
            self.assertIsNotNone(contact.email)
            self.assertIsNotNone(contact.sujet)
            self.assertIsNotNone(contact.message)
            self.assertIsNotNone(contact.date_add)
            self.assertIsNotNone(contact.date_update)
            self.assertIsNotNone(contact.status)
