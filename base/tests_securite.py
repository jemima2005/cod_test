from django.test import TestCase
from django.template import Template, Context


class TestBaseSecurite(TestCase):

    def test_script_non_rendu_par_defaut(self):
        template = Template(
            "{% extends 'base.html' %}{% block content %}<script>alert(1)</script>{% endblock %}"
        )
        html = template.render(Context({}))

        self.assertNotIn("<script>alert(1)</script>", html)
