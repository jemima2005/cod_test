from django.db import models
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
# from cinetpay_sdk.s_d_k import Cinetpay
from shop import models as Produit
from django.utils.timezone import now
from datetime import timedelta
from cities_light.models import City


# Create your models here.
class Customer(models.Model):
    user = models.OneToOneField(User, related_name='customer', on_delete=models.CASCADE)
    adresse = models.TextField()
    photo = models.ImageField(upload_to="clients/photo", null=True)
    contact_1 = models.CharField(max_length=15)
    contact_2 = models.CharField(max_length=15, null=True)
    ville = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    pays = models.CharField(max_length=155, null=True)

    date_add = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username


class PasswordResetToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='password_reset_token')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return now() - self.created_at <= timedelta(hours=1)  # Token valide pendant 1 heure

    def __str__(self):
        return f"Token for {self.user.username}"


class CodePromotionnel(models.Model):
    """Model definition for CodePromotionnel."""

    # TODO: Define fields here
    libelle = models.CharField(max_length=250)
    etat = models.BooleanField()
    date_fin = models.DateField()
    forfait = models.ManyToManyField('shop.Produit', related_name="produit_code_promo", blank=True)
    reduction = models.FloatField()
    nombre_u = models.PositiveIntegerField(null=True)
    code_promo = models.CharField(max_length=150)

    date_add = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        """Meta definition for CodePromotionnel."""

        verbose_name = 'Code promotionnel'
        verbose_name_plural = 'Codes Promotionnels'

    def __str__(self):
        """Unicode representation of CodePromotionnel."""
        return self.libelle


class Panier(models.Model):
    """Model definition for Panier."""

    # TODO: Define fields here
    session_id = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="session_panier", null=True , blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="user_panier", null=True , blank=True)
    date_add = models.DateTimeField(auto_now_add=True)
    coupon = models.ForeignKey(CodePromotionnel, on_delete=models.CASCADE, related_name="code_use", null=True , blank=True)
    date_update = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        """Meta definition for Panier."""
        verbose_name = 'Panier'
        verbose_name_plural = 'Paniers'

    def __str__(self):
        """Unicode representation of Panier."""
        return "panier"

    @property
    def total(self):
        panier = Panier.objects.get(id=self.id)
        sum = 0
        for i in panier.produit_panier.all():
            sum = sum + i.total
        return int(sum)

    @property
    def total_with_coupon(self):
        reduction = 0
        if self.coupon:
            reduction = self.coupon.reduction * self.total
        return int(self.total - reduction)

    @property
    def check_empty(self):
        panier = Panier.objects.get(id=self.id)
        if panier.produit_panier.count() > 0:
            return True
        else:
            return False


class Commande(models.Model):
    """Model definition for UserRessource."""

    # TODO: Define fields here
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="user_commande", null=True)
    id_paiment = models.CharField( max_length=50, null=True)
    payment_token = models.CharField(max_length=250, null=True)
    payment_url = models.TextField(null=True)
    transaction_id = models.TextField(null=True)
    api_response_id = models.CharField(max_length=50, null=True)
    crypto = models.CharField(max_length=50, null=True)
    prix_total = models.FloatField()
    date_add = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
    recu_paiement = models.FileField(upload_to="fichiers/paiements", null=True)

    class Meta:
        """Meta definition for UserRessource."""

        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'

    def __str__(self):
        """Unicode representation of UserRessource."""
        return "commande"
    
    @property
    def check_paiement(self):

        if 1:
            return True
        else:
            return False


class ProduitPanier(models.Model):
    produit = models.ForeignKey('shop.Produit', related_name="commande", on_delete=models.CASCADE)
    panier = models.ForeignKey(Panier, related_name="produit_panier", on_delete=models.CASCADE, null=True)
    commande = models.ForeignKey(Commande, related_name="produit_commande", on_delete=models.CASCADE, null=True)
    quantite = models.IntegerField(default=1)
    date_add = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        """Meta definition for UserRessource."""

        verbose_name = 'Produit Panier/Commande'
        verbose_name_plural = 'Produits Panier/Commande'

    @property
    def total(self):
        if self.produit.check_promotion:
            return self.produit.prix_promotionnel * self.quantite
        else:
            return self.produit.prix * self.quantite
        



