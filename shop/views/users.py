from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.http import JsonResponse
from shop.models import TelegramUser
from shop.models import Telebot
from shop.services.telegram_api import TelegramService


@login_required
def user_list(request):
    user_list = TelegramUser.objects.all()
    # Pagination with 12 people per page
    paginator = Paginator(user_list, 12)
    page_number = request.GET.get('page', 1)
    try:
        users = paginator.page(page_number)
    except PageNotAnInteger:
        # If page_number is not an integer deliver the first page
        users = paginator.page(1)
    except EmptyPage:
        # If page_number is out of range deliver last page of results
        users = paginator.page(paginator.num_pages)
    context = {
        "users":users
    }
    return render(request, 'shop/user/list.html', context)


@login_required
def broadcast(request):
    mybot = Telebot.objects.first()
    telegram_service = TelegramService()
    users = TelegramUser.objects.all()
    number_of_users = TelegramUser.objects.count()
    if request.method == 'POST':
        message = request.POST.get('w3review')
        sent_messages = 0
        for user in users:
            try:
                telegram_service.send_message(user.chat_id, message)
                sent_messages = sent_messages + 1
            except Exception as e:
                print("Error sending message for some users")


        if number_of_users == sent_messages:
            messages.success(request, f'کل کاربران {number_of_users} تعداد پیام ارسالی: {sent_messages}')
        elif sent_messages == 0:
            messages.error(request, f'کل کاربران {number_of_users} تعداد پیام ارسالی: {sent_messages}')
        else:
            messages.warning(request, f'کل کاربران {number_of_users} تعداد پیام ارسالی: {sent_messages}')

    context = {}
    if Telebot.objects.exists():
        context['bot'] = 'True'

    return render(request, 'shop/user/broadcast.html', context)


@login_required
def user_detail(request, chat_id):
    telegram_service = TelegramService()
    mybot = Telebot.objects.first()
    user = TelegramUser.objects.get(chat_id=chat_id)
    if request.method == 'POST':
        if 'send_message' in request.POST:
            message = request.POST.get('w3review')
            try:
                new_keyboard = [[mybot.category_button_text, mybot.basket_button_text ], [mybot.order_button_text]]
                reply_markup = {
                    'keyboard': new_keyboard,
                    'resize_keyboard': True,
                    'one_time_keyboard': False
                }
                telegram_service.send_message_with_keyboard(user.chat_id, message, reply_markup)
                messages.success(request, 'پیام شما با موفقیت ارسال شد')
            except Exception as e:
                messages.error(request, 'مشکلی پیش آمده، لطفا دوباره امحان کنید و یا با پشتیبانی تماس بگیرید')




    context = {
        'user':user,
    }

    if Telebot.objects.exists():
        context['bot'] = 'True'
    return render(request, 'shop/user/detail.html', context)