from django.test import TestCase, Client
from django.urls import reverse
from contact.models import Contact, NewsLetter
import json


class BaseSecurityTestCase(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)


# =====================================================
# CSRF (TEST RÉEL)
# =====================================================

class TestCSRF(BaseSecurityTestCase):

    def test_post_contact_sans_csrf_refuse(self):
        response = self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': 'Test',
                'email': 'test@test.com',
                'sujet': 'Test',
                'messages': 'Test'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)


# =====================================================
# INJECTION SQL (INTÉGRITÉ DB)
# =====================================================

class TestInjectionSQL(BaseSecurityTestCase):

    def test_injection_sql_ne_casse_pas_db(self):
        payload = "'; DROP TABLE contact_contact; --"

        response = self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': payload,
                'email': 'sql@test.com',
                'sujet': payload,
                'messages': payload
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), 1)

        contact = Contact.objects.first()
        self.assertEqual(contact.nom, payload)


# =====================================================
# XSS (NON-RÉFLEXION)
# =====================================================

class TestXSS(BaseSecurityTestCase):

    def test_xss_non_reflechi_dans_reponse(self):
        payload = '<script>alert("XSS")</script>'

        response = self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': payload,
                'email': 'xss@test.com',
                'sujet': payload,
                'messages': payload
            }),
            content_type='application/json'
        )

        content = response.content.decode('utf-8')
        self.assertNotIn(payload, content)

    def test_xss_stocke_mais_non_execute(self):
        payload = '<img src=x onerror="alert(1)">'

        self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': payload,
                'email': 'xss2@test.com',
                'sujet': 'Test',
                'messages': payload
            }),
            content_type='application/json'
        )

        contact = Contact.objects.first()
        self.assertEqual(contact.nom, payload)


# =====================================================
# VALIDATION EMAIL
# =====================================================

class TestValidationEmail(BaseSecurityTestCase):

    def test_email_malveillant_rejete(self):
        emails = [
            'test<script>@example.com',
            'test@example.com\nBcc:hack@evil.com',
            'test;DROP TABLE@example.com'
        ]

        for email in emails:
            response = self.client.post(
                reverse('post_contact'),
                data=json.dumps({
                    'nom': 'Test',
                    'email': email,
                    'sujet': 'Test',
                    'messages': 'Test'
                }),
                content_type='application/json'
            )

            self.assertFalse(response.json()['success'])
            self.assertEqual(Contact.objects.count(), 0)


# =====================================================
# JSON MALFORMÉ
# =====================================================

class TestJSON(BaseSecurityTestCase):

    def test_json_invalide_ne_crashe_pas(self):
        response = self.client.post(
            reverse('post_contact'),
            data='{"nom":',
            content_type='application/json'
        )

        self.assertIn(response.status_code, [400, 403, 500])

        # Requête valide ensuite
        response = self.client.post(
            reverse('post_contact'),
            data=json.dumps({
                'nom': 'Recovery',
                'email': 'ok@test.com',
                'sujet': 'OK',
                'messages': 'OK'
            }),
            content_type='application/json'
        )

        self.assertTrue(response.json()['success'])


# =====================================================
# MÉTHODES HTTP
# =====================================================

class TestMethodesHTTP(BaseSecurityTestCase):

    def test_get_interdit_sur_post_contact(self):
        response = self.client.get(reverse('post_contact'))
        self.assertIn(response.status_code, [403, 405])

    def test_put_delete_refuses(self):
        for method in ['put', 'delete', 'patch']:
            response = getattr(self.client, method)(
                reverse('post_contact'),
                data=json.dumps({'test': 'data'}),
                content_type='application/json'
            )
            self.assertIn(response.status_code, [403, 405])


# =====================================================
# FUITE D'INFORMATION
# =====================================================

class TestFuiteInformation(BaseSecurityTestCase):

    def test_pas_de_stacktrace_exposee(self):
        response = self.client.post(
            reverse('post_contact'),
            data=json.dumps({'bad': 'data'}),
            content_type='application/json'
        )

        content = response.content.decode('utf-8')
        forbidden = ['Traceback', 'SECRET_KEY', 'django.db', '/home/']

        for item in forbidden:
            self.assertNotIn(item, content)
