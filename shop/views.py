from django.shortcuts import redirect, render,  get_object_or_404
from . import models
from customer import models as customer_models
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
# from cinetpay_sdk.s_d_k import Cinetpay
from cities_light.models import City

from django.contrib import messages
from .models import Produit, Favorite, Etablissement, CategorieProduit
from customer.models import Commande

from django.core.paginator import Paginator
from django.utils import timezone


# Create your views here.
def shop(request):
    produits = models.Produit.objects.filter(status=True)
    datas = {
        'produits' : produits
    }
    return render(request, 'shop.html', datas)


def product_detail(request, slug):
    produit = get_object_or_404(Produit, slug=slug)
    produits = Produit.objects.filter(categorie=produit.categorie).exclude(id=produit.id)[:3]

    
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, produit=produit).exists()

    datas = {
        'produit': produit,
        'produits': produits,
        'is_favorited': is_favorited, 
    }
    return render(request, 'product-details.html', datas)


def toggle_favorite(request, produit_id):
    if not request.user.is_authenticated:
        messages.error(request, "Veuillez vous connecter pour ajouter des favoris.")
        return redirect('login') 

    produit = get_object_or_404(Produit, id=produit_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, produit=produit)

    if not created:  
        favorite.delete()
        messages.success(request, f"Le produit {produit.nom} a été retiré de vos favoris.")
    else:
        messages.success(request, f"Le produit {produit.nom} a été ajouté à vos favoris.")

    return redirect('product_detail', slug=produit.slug)


def cart(request):
    datas = {}
    return render(request, 'cart.html', datas)


@login_required(login_url='login')
def checkout(request):
    datas = {}
    return render(request, 'checkout.html', datas)


@csrf_exempt
def paiement_success(request):
    if request.user.is_authenticated:
        commandes = customer_models.Commande.objects.filter(customer=request.user.customer)

        datas = {
            'commandes': commandes,
        }
        return render(request, 'paiement.html', datas)
    else:
        return redirect('index')


def single(request, slug):
    try:
        try:
            categorie = models.CategorieProduit.objects.get(slug=slug)
            produits = categorie.produit.all()
        except:
            categorie = models.CategorieEtablissement.objects.get(slug=slug)
            produits = categorie.produit_etab.all()
    except:
        return redirect('shop')

    datas = {
        'produits' : produits,
        'categorie' : categorie
    }
    return render(request, 'shop.html', datas)


def post_paiement_details(request):

    postdata = json.loads(request.body.decode('utf-8'))
    transaction_id = postdata['transaction_id']
    notify_url = postdata['notify_url']
    return_url = postdata['return_url']
    panier = postdata['panier']
    user = request.user

    url = ""
    isSuccess = False

    _ = isSuccess
    if user and panier is not None and transaction_id is not None and notify_url is not None and return_url is not None :
        try:
            panier = customer_models.Panier.objects.get(id=panier, customer=user.customer)
        except:
            panier = None

        if panier:
            data = {
                'amount': 100,
                'currency': "XOF",
                'transaction_id': transaction_id,
                'description': "TRANSACTION DESCRIPTION",
                'return_url': notify_url,
                'notify_url': return_url,
                'customer_name': user.first_name,
                'customer_surname': user.last_name,
            }

            try:

                commande = customer_models.Commande()
                commande.customer = request.user.customer
                commande.payment_url = 'payment_url'
                commande.id_paiment = transaction_id
                commande.transaction_id = transaction_id
                commande.api_response_id = 'api_response_id'
                commande.payment_token = 'payment_token'
                commande.prix_total = panier.total_with_coupon
                commande.save()

                for i in customer_models.ProduitPanier.objects.filter(panier=panier):
                    i.panier = None
                    i.commande = commande
                    i.save()
                isSuccess = True
                message = "Commande validée"
                panier.delete()

            except Exception as _:
                isSuccess = False
                message = "Une erreur s'est produite, merci de rééssayer"
        else:
            isSuccess = False
            message = "Une erreur s'est produite"
    else:
        isSuccess = False
        message = "Une erreur s'est produite"
    data = {
        'message': message,
        'success': isSuccess,
        'payment_url' : url
    }
    return JsonResponse(data, safe=False)


@login_required
def dashboard(request):
    
    etablissement = get_object_or_404(Etablissement, user=request.user)

    
    total_articles = Produit.objects.filter(etablissement=etablissement).count()

    
    today = timezone.now().date()
    commandes_aujourdhui = Commande.objects.filter(
        produit_commande__produit__etablissement=etablissement,
        date_add__date=today
    ).distinct().count()

    
    total_commandes = Commande.objects.filter(produit_commande__produit__etablissement=etablissement).distinct().count()

    
    derniers_articles = Produit.objects.filter(etablissement=etablissement).order_by("-date_add")[:5]

    
    dernieres_commandes = Commande.objects.filter(produit_commande__produit__etablissement=etablissement).distinct().order_by("-date_add")[:5]

    context = {
        "etablissement": etablissement,
        "total_articles": total_articles,
        "commandes_aujourdhui": commandes_aujourdhui,
        "total_commandes": total_commandes,
        "derniers_articles": derniers_articles,
        "dernieres_commandes": dernieres_commandes,
    }

    return render(request, "dashboard.html", context)


@login_required
def ajout_article(request):
    etablissement = get_object_or_404(Etablissement, user=request.user)
    categories = CategorieProduit.objects.all()

    if request.method == "POST":
        nom = request.POST.get("nom")
        description = request.POST.get("description")
        prix = request.POST.get("prix")
        quantite = request.POST.get("quantite")
        categorie_id = request.POST.get("categorie")
        categorie = get_object_or_404(CategorieProduit, id=categorie_id)

        image = request.FILES.get("image")
        image_2 = request.FILES.get("image_2")
        image_3 = request.FILES.get("image_3")

        Produit.objects.create(
            nom=nom,
            description=description,
            prix=prix,
            categorie=categorie,
            etablissement=etablissement,
            image=image,
            image_2=image_2,
            quantite=quantite,
            image_3=image_3,
            status=True,
        )

        messages.success(request, "Article ajouté avec succès !")
        return redirect("article-detail")

    
    return render(request, "ajout-article.html", {
        "categories": categories,
        "etablissement": etablissement,  
    })

@login_required
def article_detail(request):
    etablissement = get_object_or_404(Etablissement, user=request.user)
    articles = Produit.objects.filter(etablissement=etablissement)

    # Gestion des filtres
    search_query = request.GET.get("search", "")
    category_filter = request.GET.get("category", "")

    if search_query:
        articles = articles.filter(nom__icontains=search_query)

    if category_filter:
        articles = articles.filter(categorie__nom=category_filter)

    categories = CategorieProduit.objects.all()  

    return render(request, "article-detail.html", {
        "articles": articles,
        "categories": categories,
        "search_query": search_query,
        "category_filter": category_filter,
        "etablissement": etablissement,
    })


@login_required
def modifier_article(request, article_id):
    etablissement = get_object_or_404(Etablissement, user=request.user)
    article = get_object_or_404(Produit, id=article_id, etablissement=etablissement)
    categories = CategorieProduit.objects.all()

    if request.method == "POST":
        article.nom = request.POST.get("nom")
        article.description = request.POST.get("description")
        
        
        prix_str = request.POST.get("prix").replace(',', '.')  
        try:
            article.prix = float(prix_str)
        except ValueError:
            messages.error(request, "Erreur : Le prix doit être un nombre valide.")
            return redirect("modifier", article_id=article.id)
        
        article.quantite = request.POST.get("quantite")
        article.categorie = get_object_or_404(CategorieProduit, id=request.POST.get("categorie"))

        if "image" in request.FILES:
            article.image = request.FILES["image"]
        if "image_2" in request.FILES:
            article.image_2 = request.FILES["image_2"]
        if "image_3" in request.FILES:
            article.image_3 = request.FILES["image_3"]

        article.save()
        messages.success(request, "Article modifié avec succès !")
        return redirect("article-detail")

    return render(request, "modifier-article.html", {"article": article, "categories": categories, "etablissement": etablissement,})


@login_required
def supprimer_article(request, article_id):
    etablissement = get_object_or_404(Etablissement, user=request.user)
    article = get_object_or_404(Produit, id=article_id, etablissement=etablissement)

    if request.method == "POST":
        article.delete()
        messages.success(request, "Article supprimé avec succès !")
        return redirect("article-detail")

    return render(request, "confirmer-suppression.html", {"article": article})


@login_required
def commande_reçu(request):
    etablissement = get_object_or_404(Etablissement, user=request.user)
    commandes_list = Commande.objects.filter(produit_commande__produit__etablissement=etablissement).distinct().order_by('-date_add')

    # 📌 Filtrage par client
    client = request.GET.get("client")
    if client:
        commandes_list = commandes_list.filter(customer__user__first_name__icontains=client).order_by('-date_add')

    # 📌 Filtrage par produit
    produit = request.GET.get("produit")
    if produit:
        commandes_list = commandes_list.filter(produit_commande__produit__nom__icontains=produit).order_by('-date_add')

    # 📌 Filtrage par statut
    status = request.GET.get("status")
    if status == "payée":
        commandes_list = commandes_list.filter(status=True).order_by('-date_add')
    elif status == "attente":
        commandes_list = commandes_list.filter(status=False).order_by('-date_add')

    # 📌 Filtrage par date
    date_min = request.GET.get("date_min")
    date_max = request.GET.get("date_max")
    if date_min:
        commandes_list = commandes_list.filter(date_add__gte=date_min).order_by('-date_add')
    if date_max:
        commandes_list = commandes_list.filter(date_add__lte=date_max).order_by('-date_add')

    paginator = Paginator(commandes_list, 25)
    page_number = request.GET.get("page")
    commandes = paginator.get_page(page_number)

    return render(request, "commande-reçu.html", {"commandes": commandes, "etablissement": etablissement})


@login_required
def commande_reçu_detail(request, commande_id):
    etablissement = get_object_or_404(Etablissement, user=request.user)
    commande = get_object_or_404(Commande, id=commande_id, produit_commande__produit__etablissement=etablissement)

    return render(request, "commande-reçu-detail.html", {"commande": commande,"etablissement": etablissement,})


@login_required(login_url='login')
def etablissement_parametre(request):
    etablissement = get_object_or_404(Etablissement, user=request.user)

    if request.method == "POST":
        etablissement.nom = request.POST.get('nom')
        etablissement.nom_du_responsable = request.POST.get('nom_responsable')
        etablissement.prenoms_duresponsable = request.POST.get('prenoms_responsable')
        etablissement.contact_1 = request.POST.get('contact')

        ville = request.POST.get('ville')
        if ville:
            ville = City.objects.get(id=int(ville))
        else:
            ville = None

        etablissement.ville = ville
        etablissement.adresse = request.POST.get('adresse')
        etablissement.email = request.POST.get('email')

        if 'logo' in request.FILES:
            etablissement.logo = request.FILES['logo']
        if 'couverture' in request.FILES:
            etablissement.couverture = request.FILES['couverture']

        etablissement.save()

        messages.success(request, "Les informations de l'établissement ont été mises à jour avec succès.")
        return redirect('etablissement-parametre')

    return render(request, 'etablissement-parametre.html', {'etablissement': etablissement})

