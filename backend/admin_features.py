from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse

from backend.models import Product, Brand


@staff_member_required
def admin_search(request):
    """
    Search for products and brands by name in the admin panel.
    :param request:
    :return:
    """
    text = request.GET.get('text', None)  # Retrieve the 'text' query parameter
    res = []

    if text:
        products = Product.objects.filter(name__icontains=text)
        brands = Brand.objects.filter(name__icontains=text)
        for product in products:
            res.append({
                'label': f'{product.name} edit',
                'url': f'/adminbackend/product/{product.id}/change',
                'icon': 'fa fa-edit',
            })

        # Add matching brands to the response list
        for brand in brands:
            res.append({
                'label': f'{brand.name} edit',
                'url': f'/adminbackend/brand/{brand.id}/change',
                'icon': 'fa fa-edit',
            })
    else:
        res = []

    return JsonResponse({
        'length': len(res),
        'data': res
    })