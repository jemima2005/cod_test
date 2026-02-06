from django.test import TestCase
from django.template import Template, Context


class TestBaseIntegration(TestCase):

    def test_base_template_rendu_sans_contexte(self):
        template = Template(
            "{% extends 'base.html' %}{% block content %}OK{% endblock %}"
        )
        html = template.render(Context({}))

        self.assertIn("OK", html)

    def test_base_template_avec_contexte_minimal(self):
        template = Template(
            "{% extends 'base.html' %}{% block content %}CONTENT{% endblock %}"
        )

        context = {
            "infos": None,
            "cat": [],
            "cart": None,
            "horaires": [],
            "galeries": [],
        }

        html = template.render(Context(context))
        self.assertIn("CONTENT", html)
