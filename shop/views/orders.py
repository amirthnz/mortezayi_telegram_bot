from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from shop.models import (
    TelegramUser,
    Address,
    Order,
    OrderItem,
    Product
)
from shop.services.telegram_api import TelegramService
import requests
import os
from django.conf import settings
from shop.models import Telebot
from shop.forms import OrderForm
from shop import constants

telegram_service = TelegramService()


def get_bot_token():
        try:
            bot = Telebot.objects.first()
            return bot.token
        except Telebot.DoesNotExist:
            return None


def order_list(request):
    orders = Order.objects.all()

    context = {
        'orders': orders
    }

    return render(request, 'shop/order/list.html', context)

@require_POST
def change_order_status(request):
    order_id = request.POST.get('order_id')
    new_status = request.POST.get('status')
    order = get_object_or_404(Order, id=order_id)

    # Change the order status
    order.status = new_status
    order.save()

    # Take action when completing order
    if new_status == 'complete':
        chat_id = order.customer.chat_id
        telegram_service.send_message(chat_id, 'سفارش شما تکمیل شد\nفایل های خریداری شده برای شما ارسال می شوند')
        # SEND DOWNLOADABLE PRODUCTS TO USER
        files_to_send = []
        for item in order.items.all():
            product = item.product
            if product.downloadable:
                pf_name = product.product_file.name
                files_to_send.append(pf_name)
                print(pf_name)


        for pr_file in files_to_send:
            send_file(chat_id, pr_file)


        telegram_service.send_message(chat_id, "در صورتی که محصول فیزیکی در سبد شما وجود داشته باشد کد رهگیری آن بزودی برای شما ارسال می شود")


    return redirect('shop:orders')




@require_POST
def add_order(request, product_id):
    user = TelegramUser .objects.first()  # Assuming you want the first user; adjust as necessary

    # Get the product or return 404 if it doesn't exist
    product = get_object_or_404(Product, id=product_id)

    # Check if the product is downloadable or has stock greater than 0
    if product.downloadable or product.stock > 0:
        # Attempt to find an existing pending order
        order = user.orders.filter(status='pending').first()

        if not order:
            # If no pending order found, create a new order
            order = Order.objects.create(customer=user)

        # Check if the product is already in the order
        order_item = order.items.filter(product=product).first()

        if order_item:
            # If the product already exists in the order, increment its quantity
            order_item.quantity += 1
            order_item.save()
        else:
            # If the product does not exist, create a new OrderItem
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1
            )

        # Reduce product stock if not downloadable
        if not product.downloadable:
            product.stock -= 1
            product.save()
    else:
        # Optionally, you can add a message to inform the user why the product wasn't added
        # For example, using Django messages framework
        messages.error(request, "This product cannot be added to the order because it is not available for purchase.")
        return redirect('shop:product_list')

    return redirect('shop:orders')


def send_file(chat_id, file_name):
    url = f"https://api.telegram.org/bot{get_bot_token()}/sendDocument"
    file_path = os.path.join(settings.MEDIA_ROOT, file_name)

    with open(file_path, 'rb') as pdf_file:
        files = {'document': pdf_file}
        data = {
            'chat_id': chat_id,
            'caption': f"محصول شما"
        }
        response = requests.post(url, data=data, files=files)
        if response.status_code == 200:
            telegram_service.send_message(chat_id, "محصول با موفقیت ارسال شد")

        else:
            telegram_service.send_message(chat_id, "لطفا به پشتیبانی ربات (آیدی در بیو) پیام دهید")


def order_detail(request, pk):
    order = Order.objects.get(id=pk)

    chat_id = order.customer.chat_id
    total_price = 0

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            cd = form.cleaned_data
            message_param = cd['tracking_id']
            message = f'محصول شما ارسال شد، کد رهگیری شما:\n\n{message_param}'
            telegram_service.send_message(chat_id, message)
            messages.success(request, 'کد رهگیری ثبت شد')
            return redirect('shop:order_detail', order.id)




    if order.items.count() > 0:
        total_price = sum(item.product.price * item.quantity for item in order.items.all())
        if order.need_tracking:
            total_price += constants.SHIPPING_PRICE

    context = {
        'order':order,
        'total_price':total_price,
        'shipping_price':constants.SHIPPING_PRICE
    }

    if order.need_tracking:
        form = OrderForm(instance=order)
        context['form'] = form



    return render(request, 'shop/order/detail.html', context)


def order_delete(request, pk):
    order = Order.objects.get(id=pk)
    order.delete()
    messages.warning(request, "سفارش موردنظر حذف شد")
    return redirect('shop:orders')