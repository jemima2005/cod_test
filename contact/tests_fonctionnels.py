from django.test import TestCase, Client
from django.urls import reverse
from contact.models import Contact, NewsLetter
import json


class BaseContactTestCase(TestCase):

    def setUp(self):
        self.client = Client()


# =====================================================
# PAGE CONTACT
# =====================================================

class TestPageContact(BaseContactTestCase):

    def test_page_contact_accessible(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact-us.html')

    def test_formulaire_present(self):
        response = self.client.get(reverse('contact'))
        self.assertContains(response, 'Nom complet')
        self.assertContains(response, 'Email')
        self.assertContains(response, 'Sujet')
        self.assertContains(response, 'Message')


# =====================================================
# FORMULAIRE CONTACT
# =====================================================

class TestFormulaireContact(BaseContactTestCase):

    def post_contact(self, data):
        return self.client.post(
            reverse('post_contact'),
            data=json.dumps(data),
            content_type='application/json'
        )

    def test_envoi_contact_valide(self):
        data = {
            'nom': 'Jean Dupont',
            'email': 'jean@example.com',
            'sujet': 'Information',
            'messages': 'Bonjour'
        }

        response = self.post_contact(data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(Contact.objects.count(), 1)

    def test_contact_champs_manquants_refuses(self):
        data = {
            'nom': '',
            'email': '',
            'sujet': '',
            'messages': ''
        }

        response = self.post_contact(data)

        self.assertFalse(response.json()['success'])
        self.assertEqual(Contact.objects.count(), 0)

    def test_email_invalide_refuse(self):
        data = {
            'nom': 'Test',
            'email': 'email_invalide',
            'sujet': 'Test',
            'messages': 'Test'
        }

        response = self.post_contact(data)

        self.assertFalse(response.json()['success'])
        self.assertEqual(Contact.objects.count(), 0)

    def test_emails_valides_acceptes(self):
        emails = [
            'test@example.com',
            'user.name@example.co.uk',
            'user+tag@example.com'
        ]

        for email in emails:
            Contact.objects.all().delete()
            data = {
                'nom': 'User',
                'email': email,
                'sujet': 'Test',
                'messages': 'Test'
            }

            response = self.post_contact(data)
            self.assertTrue(response.json()['success'])

        self.assertEqual(Contact.objects.count(), 1)


# =====================================================
# NEWSLETTER
# =====================================================

class TestNewsletter(BaseContactTestCase):

    def post_newsletter(self, email):
        return self.client.post(
            reverse('post_newsletter'),
            data=json.dumps({'email': email}),
            content_type='application/json'
        )

    def test_newsletter_valide(self):
        response = self.post_newsletter('newsletter@example.com')
        self.assertTrue(response.json()['success'])
        self.assertEqual(NewsLetter.objects.count(), 1)

    def test_newsletter_email_invalide(self):
        response = self.post_newsletter('email_invalide')
        self.assertFalse(response.json()['success'])
        self.assertEqual(NewsLetter.objects.count(), 0)


# =====================================================
# MODELES (UNITAIRES SIMPLES)
# =====================================================

class TestModelesContact(TestCase):

    def test_creation_contact(self):
        contact = Contact.objects.create(
            nom='Test',
            email='test@example.com',
            sujet='Sujet',
            message='Message'
        )

        self.assertEqual(str(contact), 'Test')
        self.assertTrue(contact.status)

    def test_creation_newsletter(self):
        newsletter = NewsLetter.objects.create(email='news@test.com')
        self.assertEqual(str(newsletter), 'news@test.com')
        self.assertTrue(newsletter.status)
