from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from shop.models import Address


def address_list(request):
    addresses = Address.objects.all()

    data = {
        'results': list(addresses.values('customer'))
    }

    return JsonResponse(data)


def address(request, customer_id):
    addresses = get_object_or_404(Address, customer=customer_id)

    data = {
        'results': {
            'customer': addresses.customer.chat_id,
            'country': addresses.country,
            'city': addresses.city,
            'street': addresses.street,
        }
    }

    return JsonResponse(data)