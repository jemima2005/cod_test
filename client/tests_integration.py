"""
TESTS D'INTÉGRATION - APPLICATION CLIENT
Site E-Commerce - Module Espace Client

Prérequis:
- Python 3.12
- Django 4.2
- Base de données configurée

Exécution:
python manage.py test client.tests_integration

OU pour un test spécifique:
python manage.py test client.tests_integration.TestIntegrationCommande.test_workflow_complet_commande
"""

from django.test import TestCase, Client as DjangoClient
from django.contrib.auth.models import User
from django.urls import reverse
from customer.models import Customer, Commande, ProduitPanier, Panier
from shop.models import Produit, CategorieProduit, Favorite, Etablissement, CategorieEtablissement
from cities_light.models import City, Country
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
import time


class BaseIntegrationTestCase(TestCase):
    """Classe de base pour les tests d'intégration"""
    
    def setUp(self):
        """Préparation des données de test"""
        
        self.client = DjangoClient()
        
        # Créer un pays et une ville
        self.country = Country.objects.create(
            name="Côte d'Ivoire",
            code2="CI",
            code3="CIV"
        )
        
        self.ville = City.objects.create(
            name="Abidjan",
            country=self.country,
            display_name="Abidjan, CI"
        )
        
        # Créer un utilisateur
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='TestPassword123!',
            first_name='Jean',
            last_name='Dupont'
        )
        
        self.customer = Customer.objects.create(
            user=self.user,
            adresse="Cocody Riviera Palmeraie",
            contact_1="0708090605",
            ville=self.ville,
            pays="Côte d'Ivoire"
        )
        
        # Créer une catégorie établissement
        self.cat_etab = CategorieEtablissement.objects.create(
            nom="Supermarchés",
            status=True
        )
        
        # Créer un établissement
        self.etablissement = Etablissement.objects.create(
            nom="SuperMarket CI",
            nom_du_responsable="Kouassi",
            prenoms_duresponsable="Yao",
            contact_1="0707070707",
            ville=self.ville,
            adresse="Plateau",
            email="supermarket@test.com",
            categorie=self.cat_etab,
            user=self.user,
            status=True
        )
        
        # Créer une catégorie de produit
        self.categorie = CategorieProduit.objects.create(
            nom="Électronique",
            status=True
        )
        
        # Créer des produits
        self.produit1 = Produit.objects.create(
            nom="Smartphone Samsung",
            description="Téléphone haut de gamme",
            prix=250000,
            quantite=10,
            categorie=self.categorie,
            etablissement=self.etablissement,
            status=True
        )
        
        self.produit2 = Produit.objects.create(
            nom="Écouteurs Bluetooth",
            description="Sans fil avec micro",
            prix=15000,
            quantite=50,
            categorie=self.categorie,
            etablissement=self.etablissement,
            status=True
        )
    
    def login(self):
        """Connexion rapide"""
        return self.client.login(username='testuser@example.com', password='TestPassword123!')


# ==============================================================================
# TESTS WORKFLOW COMPLET COMMANDE
# ==============================================================================

class TestIntegrationCommande(BaseIntegrationTestCase):
    """Tests du workflow complet de gestion des commandes"""
    
    def test_workflow_complet_commande(self):
        """INT-CLI-001: Workflow complet - Création → Consultation → PDF"""
        
        # Étape 1: Créer une commande
        commande = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY001",
            transaction_id="TXN001",
            prix_total=265000,
            status=True
        )
        
        ProduitPanier.objects.create(
            produit=self.produit1,
            commande=commande,
            quantite=1
        )
        
        ProduitPanier.objects.create(
            produit=self.produit2,
            commande=commande,
            quantite=1
        )
        
        # Étape 2: Se connecter
        self.login()
        
        # Étape 3: Consulter le profil (doit afficher la commande)
        response = self.client.get(reverse('profil'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TXN001')
        
        # Étape 4: Consulter la liste des commandes
        response = self.client.get(reverse('commande'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TXN001')
        self.assertContains(response, 'Smartphone Samsung')
        
        # Étape 5: Consulter le détail
        response = self.client.get(reverse('commande-detail', args=[commande.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PAY001')
        self.assertContains(response, '265000')
        
        # Étape 6: Générer le PDF
        response = self.client.get(reverse('invoice_pdf', args=[commande.id]))
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertGreater(len(response.content), 0)
        
        print("✅ INT-CLI-001: Workflow commande complet OK")
    
    def test_commande_affichee_immediatement(self):
        """INT-CLI-002: Nouvelle commande visible immédiatement"""
        
        self.login()
        
        # Compter les commandes avant
        response = self.client.get(reverse('commande'))
        nb_avant = response.content.decode().count('<tr>')
        
        # Créer une nouvelle commande
        commande = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY_NEW",
            transaction_id="TXN_NEW",
            prix_total=100000,
            status=True
        )
        
        # Vérifier qu'elle apparaît
        response = self.client.get(reverse('commande'))
        self.assertContains(response, 'TXN_NEW')
        
        print("✅ INT-CLI-002: Commande visible immédiatement OK")
    
    def test_modification_commande_refletee(self):
        """INT-CLI-003: Modification d'une commande reflétée partout"""
        
        # Créer une commande
        commande = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY_MOD",
            transaction_id="TXN_MOD",
            prix_total=50000,
            status=True
        )
        
        self.login()
        
        # Vérifier le prix initial
        response = self.client.get(reverse('commande-detail', args=[commande.id]))
        self.assertContains(response, '50000')
        
        # Modifier le prix
        commande.prix_total = 75000
        commande.save()
        
        # Vérifier la modification
        response = self.client.get(reverse('commande-detail', args=[commande.id]))
        self.assertContains(response, '75000')
        self.assertNotContains(response, '50000')
        
        print("✅ INT-CLI-003: Modification commande reflétée OK")


# ==============================================================================
# TESTS WORKFLOW FAVORIS
# ==============================================================================

class TestIntegrationFavoris(BaseIntegrationTestCase):
    """Tests du workflow de gestion des favoris"""
    
    def test_ajout_favori_affiche_liste(self):
        """INT-CLI-004: Ajout favori → Visible dans liste souhaits"""
        
        self.login()
        
        # Vérifier liste vide
        response = self.client.get(reverse('liste-souhait'))
        self.assertContains(response, "aucun produit")
        
        # Ajouter un favori
        Favorite.objects.create(
            user=self.user,
            produit=self.produit1
        )
        
        # Vérifier qu'il apparaît
        response = self.client.get(reverse('liste-souhait'))
        self.assertContains(response, 'Smartphone Samsung')
        
        print("✅ INT-CLI-004: Ajout favori visible OK")
    
    def test_suppression_favori_retire_liste(self):
        """INT-CLI-005: Suppression favori → Retiré de la liste"""
        
        # Créer un favori
        favori = Favorite.objects.create(
            user=self.user,
            produit=self.produit1
        )
        
        self.login()
        
        # Vérifier présence
        response = self.client.get(reverse('liste-souhait'))
        self.assertContains(response, 'Smartphone Samsung')
        
        # Supprimer
        favori.delete()
        
        # Vérifier absence
        response = self.client.get(reverse('liste-souhait'))
        self.assertNotContains(response, 'Smartphone Samsung')
        
        print("✅ INT-CLI-005: Suppression favori OK")
    
    def test_favori_integration_produit(self):
        """INT-CLI-006: Favori lié au produit correct"""
        
        # Ajouter les 2 produits aux favoris
        Favorite.objects.create(user=self.user, produit=self.produit1)
        Favorite.objects.create(user=self.user, produit=self.produit2)
        
        self.login()
        response = self.client.get(reverse('liste-souhait'))
        
        # Vérifier que les 2 sont présents avec les bons noms et prix
        self.assertContains(response, 'Smartphone Samsung')
        self.assertContains(response, 'Écouteurs Bluetooth')
        self.assertContains(response, '250000')
        self.assertContains(response, '15000')
        
        print("✅ INT-CLI-006: Favoris liés aux produits OK")


# ==============================================================================
# TESTS WORKFLOW PROFIL
# ==============================================================================

class TestIntegrationProfil(BaseIntegrationTestCase):
    """Tests du workflow de gestion du profil"""
    
    def test_modification_profil_refletee_partout(self):
        """INT-CLI-007: Modification profil → Visible sur toutes les pages"""
        
        self.login()
        
        # Modifier le profil
        response = self.client.post(reverse('parametre'), {
            'first_name': 'Pierre',
            'last_name': 'Martin',
            'contact': '0123456789',
            'city': self.ville.id,
            'address': 'Nouvelle adresse'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Vérifier sur le profil
        response = self.client.get(reverse('profil'))
        self.assertContains(response, 'Pierre')
        self.assertContains(response, 'Martin')
        
        # Vérifier sur les paramètres
        response = self.client.get(reverse('parametre'))
        self.assertContains(response, 'Pierre')
        self.assertContains(response, 'Martin')
        self.assertContains(response, '0123456789')
        
        print("✅ INT-CLI-007: Modification profil reflétée OK")
    
    def test_changement_ville_reflete(self):
        """INT-CLI-008: Changement de ville → Affiché correctement"""
        
        # Créer une nouvelle ville
        nouvelle_ville = City.objects.create(
            name="Yamoussoukro",
            country=self.country,
            display_name="Yamoussoukro, CI"
        )
        
        self.login()
        
        # Changer la ville
        response = self.client.post(reverse('parametre'), {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'contact': '0708090605',
            'city': nouvelle_ville.id,
            'address': 'Cocody'
        })
        
        # Vérifier sur le profil
        response = self.client.get(reverse('profil'))
        self.assertContains(response, 'Yamoussoukro')
        
        print("✅ INT-CLI-008: Changement ville OK")
    
    def test_upload_photo_affichee(self):
        """INT-CLI-009: Upload photo → Affichée sur le profil"""
        
        self.login()
        
        # Créer une image
        image = Image.new('RGB', (100, 100), color='green')
        img_io = io.BytesIO()
        image.save(img_io, format='JPEG')
        img_io.seek(0)
        
        fichier = SimpleUploadedFile(
            "nouvelle_photo.jpg",
            img_io.getvalue(),
            content_type="image/jpeg"
        )
        
        # Uploader
        response = self.client.post(reverse('parametre'), {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'contact': '0708090605',
            'city': self.ville.id,
            'address': 'Cocody',
            'profile_picture': fichier
        })
        
        # Vérifier que la photo a changé
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.photo)
        self.assertIn('nouvelle_photo', self.customer.photo.name)
        
        print("✅ INT-CLI-009: Upload photo OK")


# ==============================================================================
# TESTS INTÉGRATION RECHERCHE
# ==============================================================================

class TestIntegrationRecherche(BaseIntegrationTestCase):
    """Tests d'intégration de la recherche"""
    
    def test_recherche_trouve_commande_par_transaction(self):
        """INT-CLI-010: Recherche par transaction trouve la bonne commande"""
        
        # Créer plusieurs commandes
        for i in range(5):
            commande = Commande.objects.create(
                customer=self.customer,
                id_paiment=f"PAY{i:03d}",
                transaction_id=f"TXN{i:03d}",
                prix_total=10000,
                status=True
            )
        
        self.login()
        
        # Rechercher TXN002
        response = self.client.get(reverse('commande') + '?q=TXN002')
        
        # Doit trouver TXN002 uniquement
        self.assertContains(response, 'TXN002')
        self.assertNotContains(response, 'TXN001')
        self.assertNotContains(response, 'TXN003')
        
        print("✅ INT-CLI-010: Recherche transaction OK")
    
    def test_recherche_trouve_commande_par_produit(self):
        """INT-CLI-011: Recherche par nom produit trouve la commande"""
        
        # Créer une commande avec le produit1
        commande = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY_SEARCH",
            transaction_id="TXN_SEARCH",
            prix_total=250000,
            status=True
        )
        
        ProduitPanier.objects.create(
            produit=self.produit1,
            commande=commande,
            quantite=1
        )
        
        self.login()
        
        # Rechercher "Samsung"
        response = self.client.get(reverse('commande') + '?q=Samsung')
        
        # Doit trouver la commande contenant le Samsung
        self.assertContains(response, 'TXN_SEARCH')
        self.assertContains(response, 'Samsung')
        
        print("✅ INT-CLI-011: Recherche produit OK")


# ==============================================================================
# TESTS INTÉGRATION PAGINATION
# ==============================================================================

class TestIntegrationPagination(BaseIntegrationTestCase):
    """Tests d'intégration de la pagination"""
    
    def test_pagination_preserve_recherche(self):
        """INT-CLI-012: Pagination préserve les critères de recherche"""
        
        # Créer 15 commandes avec "SPECIAL" dans le nom
        for i in range(15):
            Commande.objects.create(
                customer=self.customer,
                id_paiment=f"PAY_SPECIAL_{i}",
                transaction_id=f"TXN_SPECIAL_{i}",
                prix_total=10000,
                status=True
            )
        
        self.login()
        
        # Rechercher "SPECIAL"
        response = self.client.get(reverse('commande') + '?q=SPECIAL')
        self.assertContains(response, 'SPECIAL')
        
        # Aller à la page 2
        response = self.client.get(reverse('commande') + '?q=SPECIAL&page=2')
        
        # Doit toujours contenir "SPECIAL" (recherche préservée)
        self.assertContains(response, 'SPECIAL')
        self.assertIn('q=SPECIAL', response.content.decode())
        
        print("✅ INT-CLI-012: Pagination préserve recherche OK")


# ==============================================================================
# TESTS INTÉGRATION MULTI-MODULES
# ==============================================================================

class TestIntegrationMultiModules(BaseIntegrationTestCase):
    """Tests d'intégration entre plusieurs modules"""
    
    def test_produit_modifie_affecte_commande(self):
        """INT-CLI-013: Modification produit → Reflétée dans commande"""
        
        # Créer une commande avec produit1
        commande = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY_INT",
            transaction_id="TXN_INT",
            prix_total=250000,
            status=True
        )
        
        produit_panier = ProduitPanier.objects.create(
            produit=self.produit1,
            commande=commande,
            quantite=1
        )
        
        self.login()
        
        # Vérifier le nom initial
        response = self.client.get(reverse('commande-detail', args=[commande.id]))
        self.assertContains(response, 'Smartphone Samsung')
        
        # Modifier le nom du produit
        self.produit1.nom = "Smartphone Samsung Galaxy S24"
        self.produit1.save()
        
        # Vérifier la modification dans la commande
        response = self.client.get(reverse('commande-detail', args=[commande.id]))
        self.assertContains(response, 'Smartphone Samsung Galaxy S24')
        
        print("✅ INT-CLI-013: Modification produit reflétée OK")
    
    def test_suppression_utilisateur_cascade(self):
        """INT-CLI-014: Suppression utilisateur → Cascade sur données liées"""
        
        # Créer un autre utilisateur avec données
        user2 = User.objects.create_user(
            username='user2@test.com',
            password='Password123!'
        )
        
        customer2 = Customer.objects.create(
            user=user2,
            adresse="Test",
            contact_1="0101010101",
            ville=self.ville
        )
        
        commande2 = Commande.objects.create(
            customer=customer2,
            id_paiment="PAY_CASCADE",
            transaction_id="TXN_CASCADE",
            prix_total=50000,
            status=True
        )
        
        # Compter avant suppression
        nb_customers_avant = Customer.objects.count()
        nb_commandes_avant = Commande.objects.count()
        
        # Supprimer l'utilisateur
        user2.delete()
        
        # Vérifier la cascade
        nb_customers_apres = Customer.objects.count()
        nb_commandes_apres = Commande.objects.count()
        
        self.assertEqual(nb_customers_apres, nb_customers_avant - 1)
        self.assertEqual(nb_commandes_apres, nb_commandes_avant - 1)
        
        print("✅ INT-CLI-014: Cascade suppression OK")


# ==============================================================================
# TESTS SESSION ET ÉTAT
# ==============================================================================

class TestIntegrationSession(BaseIntegrationTestCase):
    """Tests d'intégration liés aux sessions"""
    
    def test_session_maintenue_navigation(self):
        """INT-CLI-015: Session maintenue pendant la navigation"""
        
        self.login()
        
        # Naviguer sur plusieurs pages
        pages = [
            reverse('profil'),
            reverse('commande'),
            reverse('liste-souhait'),
            reverse('parametre'),
            reverse('profil')
        ]
        
        for page in pages:
            response = self.client.get(page)
            self.assertEqual(response.status_code, 200)
            # Vérifier que l'utilisateur est toujours connecté
            self.assertEqual(response.context['user'].username, 'testuser@example.com')
        
        print("✅ INT-CLI-015: Session maintenue OK")
    
    def test_deconnexion_efface_acces(self):
        """INT-CLI-016: Déconnexion → Plus d'accès aux pages protégées"""
        
        self.login()
        
        # Accès possible
        response = self.client.get(reverse('profil'))
        self.assertEqual(response.status_code, 200)
        
        # Déconnexion
        self.client.logout()
        
        # Accès bloqué
        response = self.client.get(reverse('profil'))
        self.assertEqual(response.status_code, 302)  # Redirection
        
        print("✅ INT-CLI-016: Déconnexion bloque accès OK")


# ==============================================================================
# TESTS WORKFLOW COMPLET UTILISATEUR
# ==============================================================================

class TestWorkflowCompletUtilisateur(BaseIntegrationTestCase):
    """Test du workflow complet d'un utilisateur"""
    
    def test_scenario_utilisateur_complet(self):
        """INT-CLI-017: Scénario complet d'utilisation"""
        
        # 1. Connexion
        self.login()
        print("  ✓ Connexion OK")
        
        # 2. Consulter le profil
        response = self.client.get(reverse('profil'))
        self.assertEqual(response.status_code, 200)
        print("  ✓ Profil consulté")
        
        # 3. Modifier les informations
        response = self.client.post(reverse('parametre'), {
            'first_name': 'Jean Modifié',
            'last_name': 'Dupont',
            'contact': '0708090605',
            'city': self.ville.id,
            'address': 'Nouvelle adresse'
        })
        self.assertEqual(response.status_code, 302)
        print("  ✓ Profil modifié")
        
        # 4. Ajouter un favori
        Favorite.objects.create(user=self.user, produit=self.produit1)
        print("  ✓ Favori ajouté")
        
        # 5. Consulter les favoris
        response = self.client.get(reverse('liste-souhait'))
        self.assertContains(response, 'Smartphone Samsung')
        print("  ✓ Favoris consultés")
        
        # 6. Créer une commande
        commande = Commande.objects.create(
            customer=self.customer,
            id_paiment="PAY_SCENARIO",
            transaction_id="TXN_SCENARIO",
            prix_total=250000,
            status=True
        )
        ProduitPanier.objects.create(
            produit=self.produit1,
            commande=commande,
            quantite=1
        )
        print("  ✓ Commande créée")
        
        # 7. Consulter la liste des commandes
        response = self.client.get(reverse('commande'))
        self.assertContains(response, 'TXN_SCENARIO')
        print("  ✓ Commandes consultées")
        
        # 8. Consulter le détail
        response = self.client.get(reverse('commande-detail', args=[commande.id]))
        self.assertContains(response, 'PAY_SCENARIO')
        print("  ✓ Détail consulté")
        
        # 9. Télécharger le PDF
        response = self.client.get(reverse('invoice_pdf', args=[commande.id]))
        self.assertEqual(response['Content-Type'], 'application/pdf')
        print("  ✓ PDF téléchargé")
        
        # 10. Rechercher une commande
        response = self.client.get(reverse('commande') + '?q=SCENARIO')
        self.assertContains(response, 'SCENARIO')
        print("  ✓ Recherche effectuée")
        
        print("✅ INT-CLI-017: Scénario utilisateur complet OK")


# ==============================================================================
# FONCTION POUR EXÉCUTER TOUS LES TESTS
# ==============================================================================

def run_all_integration_tests():
    """
    Fonction pour exécuter tous les tests d'intégration
    
    Usage:
    python manage.py test client.tests_integration --verbosity=2
    """
    import unittest
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter tous les tests d'intégration
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationCommande))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationFavoris))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationProfil))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationRecherche))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationPagination))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationMultiModules))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationSession))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowCompletUtilisateur))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Afficher le résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS D'INTÉGRATION - APPLICATION CLIENT")
    print("="*70)
    print(f"Tests exécutés: {result.testsRun}")
    print(f"✅ Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Échecs: {len(result.failures)}")
    print(f"⚠️ Erreurs: {len(result.errors)}")
    print("="*70)
    
    return result


if __name__ == '__main__':
    run_all_integration_tests()