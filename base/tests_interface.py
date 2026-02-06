from django.test import TestCase
from django.template import Template, Context


class TestBaseInterface(TestCase):

    def render_base(self):
        template = Template(
            "{% extends 'base.html' %}{% block content %}X{% endblock %}"
        )
        return template.render(Context({}))

    def test_header_present(self):
        html = self.render_base()
        self.assertIn("header", html)

    def test_footer_present(self):
        html = self.render_base()
        self.assertIn("footer", html)

    def test_bloc_content_existe(self):
        html = self.render_base()
        self.assertIn("X", html)
