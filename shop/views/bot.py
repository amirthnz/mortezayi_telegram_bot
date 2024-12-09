from django.shortcuts import render, redirect
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from shop.forms import RobotForm
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from shop.services.telegram_api import TelegramService
from shop.services.sms_service import MessageService
from shop import constants
from shop.models import Category, Product, Order, OrderItem, Address, Telebot, TelegramUser


# Create your views here.
def get_bot_token():
        try:
            bot = Telebot.objects.first()
            return bot.token
        except Telebot.DoesNotExist:
            return None

def generate_keyboard(items=None, custom_keyboard = False):
    mybot = Telebot.objects.first()
    if custom_keyboard:
        new_keyboard = generate_custom_list(items, mybot.back_button_text)
        return new_keyboard

def generate_custom_list(items, back_button_text, chunk_size=2):
    # Initialize the result list with the two distinct fixed items
    result = []

    # Loop through the items and group them in chunks of 'chunk_size'
    for i in range(0, len(items), chunk_size):
        result.append(items[i:i + chunk_size])
    # Back button
    result.append([back_button_text])

    return result


class TelegramWebhookAPI(APIView):
    """
    Handles incoming webhook requests from Telegram
    """

    def __init__(self):
        self.expecting_photo = {}
        self.my_bot = self.get_bot()

    def get_bot(self):
        return Telebot.objects.first()

    telegram_service = TelegramService()
    message_service = MessageService()
    current_page = constants.MAIN_PAGE

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        # Get telegram update object
        data = request.data

        message = data.get('message', {})
        callback_query = data.get('callback_query', {})
        reply_to_message = message.get('reply_to_message', {})
        if message:
            from_user = message.get('from', {})
            chat_id = from_user.get('id')
            text = message.get('text', '')


            # Process the message
            self.proccess_message(chat_id, from_user, message, request, reply_to_message)
        elif callback_query:
            self.handle_callback_query(callback_query)


        return Response({'status', 'ok'}, status=status.HTTP_200_OK)


    def proccess_message(self, chat_id, from_user, message, data, reply_to_message={}):

        first_name = from_user.get('first_name', '')
        last_name = from_user.get('last_name', '')
        username = from_user.get('username', '')
        text = message.get('text', '')
        photo = message.get('photo', None)

        first_time_user = False

        try:
            user = TelegramUser .objects.get(chat_id=chat_id)
            first_time_user = False
        except TelegramUser.DoesNotExist:
            user = TelegramUser .objects.create(chat_id=chat_id, first_name=first_name, last_name=last_name, username=username)
            first_time_user = True

        categories = Category.objects.all()




        if reply_to_message:
            reply_message_text = reply_to_message.get('text')
            if reply_message_text == constants.GET_RECIPE:
                self.proccess_reply_message(chat_id, photo)
            elif reply_message_text == constants.TAKE_ADDRESS_STATE:
                self.process_address_state_reply(chat_id, text)
            elif reply_message_text == constants.TAKE_ADDRESS_CITY:
                self.proccess_address_city_reply(chat_id, text)
            elif reply_message_text == constants.TAKE_ADDRESS_STREET:
                self.proccess_address_street_reply(chat_id, text)
            elif reply_message_text == constants.TAKE_ADDRESS_NEIGHBORHOOD:
                self.proccess_address_neighborhood_reply(chat_id, text)
            elif reply_message_text == constants.TAKE_ADDRESS_PLATE:
                self.proccess_address_plate_reply(chat_id, text)
            elif reply_message_text == constants.TAKE_ADDRESS_UNIT:
                self.proccess_address_unit_reply(chat_id, text)
        else:
            if text != '':
                if '/start' in text:
                    # Set user state
                    user.state = constants.MAIN_PAGE
                    user.save()
                    if first_time_user:
                        self.telegram_service.send_welcome_message(chat_id)
                    else:
                        self.telegram_service.send_main_menu(chat_id)


                elif '/menu' in text:
                    self.telegram_service.send_main_menu(chat_id)

                elif self.my_bot.category_button_text in text or '/catalog' in text:
                    category_titles = [category.title for category in categories]
                    if category_titles.__len__() > 0:
                        keyboard = generate_keyboard(category_titles, True)
                        reply_markup = {
                            'keyboard': generate_keyboard(category_titles, True),
                            'resize_keyboard': True,  # Optional: resize keyboard to fit the number of buttons
                            'one_time_keyboard': False  # Optional: hide the keyboard after a button press
                        }
                        message_text = self.my_bot.select_category_message
                        self.telegram_service.send_message_with_keyboard(chat_id, message_text, reply_markup)
                        user.state = constants.CATEGORY_PAGE
                        user.save()
                    else:
                        self.telegram_service.send_message(chat_id, 'در حال حاضر محصولی وجود ندارد', False)

                elif self.my_bot.basket_button_text in text:
                    print("Show order")
                    self.view_order(chat_id)

                elif self.my_bot.order_button_text in text:
                    user = TelegramUser .objects.get(chat_id=chat_id)
                    pending_orders = user.orders.filter(status='wait_for_pay')
                    if pending_orders:
                        for order in pending_orders:
                            self.show_current_unpaid_order(chat_id, order)
                    else:
                        self.telegram_service.send_message(chat_id, 'سفارش در جریانی ندارید')

                elif self.my_bot.back_button_text in text:
                    # If we are in category page we should show main menu
                    if user.state == constants.CATEGORY_PAGE:
                        reply_markup = {
                            'keyboard': generate_keyboard(),
                            'resize_keyboard': True,  # Optional: resize keyboard to fit the number of buttons
                            'one_time_keyboard': False  # Optional: hide the keyboard after a button press
                        }
                        self.telegram_service.send_main_menu(chat_id)
                        user.state = constants.MAIN_PAGE
                        user.save()
                elif text in [category.title for category in categories]:
                        category = Category.objects.get(title=text)
                        self.telegram_service.send_product_choices(chat_id, category)
                else:
                    self.telegram_service.send_main_menu(chat_id)




    def handle_callback_query(self, callback_query):
        chat_id = callback_query['from']['id']
        callback_data = callback_query.get('data')

        product_replies = []
        products = Product.objects.all()
        for product in products:
            product_replies.append(product.title)

        if callback_data in product_replies:
            try:
                product = Product.objects.get(title=callback_data)

                message_text = f'{product.title} \n\n {product.description}'
                picture_names = [image.image.name for image in product.images.all()]
                if picture_names:
                    # Send product with photo
                    self.telegram_service.send_product(chat_id, message_text, product.id, picture_names)
                else:
                    # Send product without photo
                    print("GETTING CALLED")
                    self.telegram_service.send_product(chat_id, message_text, product.id)
            except Product.DoesNotExist:
                self.telegram_service.send_message(chat_id, 'محصول وجود ندارد')
        elif 'add_to_order' in callback_data:
            action, product_id = callback_data.split(':')
            self.add_product_to_order(chat_id, product_id)

        elif 'decrease_quantity' in callback_data:
            action, item_id = callback_data.split(':')
            self.decrease_quantity(chat_id, item_id)

        elif 'increase_quantity' in callback_data:
            action, item_id = callback_data.split(':')
            self.increase_quantity(chat_id, item_id)

        elif 'checkout_order' in callback_data:
            self.process_checkout(chat_id)

        elif 'delete_order' in callback_data:
            # DELETE ORDER
            action, order_id = callback_data.split(':')
            self.delete_order(chat_id, order_id)

        elif 'send_recipe' in callback_data:
            action, order_id = callback_data.split(':')
            self.take_user_recipe(order_id, chat_id)

        elif 'view_order' in callback_data:
            self.view_order(chat_id)
        elif 'address_approved' in callback_data:
            # self.telegram_service.send_message(chat_id, 'تشکر')
            user = TelegramUser.objects.get(chat_id=chat_id)
            user_address = Address.objects.get(customer=user)
            current_order_id = user.current_order_id
            pending_order = Order.objects.get(id=current_order_id)

            pending_order.shipping_address = user_address
            pending_order.save()
            self.checkout(chat_id, pending_order)

            self.process_checkout(chat_id)
            # self.telegram_service.send_main_menu(chat_id)
        elif 'address_edit' in callback_data or 'add_address' in callback_data:
            self.telegram_service.send_force_reply_message(chat_id, constants.TAKE_ADDRESS_STATE)
        else:
            self.telegram_service.send_message(chat_id, 'دستور وجود ندارد')


    def view_order(self, chat_id):
        print("VIEW ORDER")
        # Turn this to a method so we can use it somewhere else
        # Show user's order if have one
        user = TelegramUser .objects.get(chat_id=chat_id)

        # Check for existing pending orders
        # pending_orders = user.orders.filter(status='pending')
        pending_orders = Order.pending.filter(customer=user)

        if pending_orders.exists():
            self.show_current_pending_order(chat_id)
        else:
            self.telegram_service.send_message(chat_id, f'سبد خرید شما خالی است\nمشاهده محصولات /catalog', False)


    def take_user_recipe(self, order_id, chat_id):

        # WE WANT TO GET ORDER ID SO WE KNOW WHICH ORDER USER WANTS TO PAY FOR
        user = TelegramUser .objects.get(chat_id=chat_id)
        # check if the order still exists
        try:
            order = Order.objects.get(id=order_id)
            # Check if order is not complete
            if order.status != 'complete':
                user.current_order_id = order_id
                user.save()
                # MAYBE WE CAN SET A LOCAL FIELD FOR CURRENT PAYMENT ORDER IN USER MODEL
                messageText = constants.GET_RECIPE
                keyboard = {
                'force_reply': True,
                }
                self.telegram_service.send_message_with_keyboard(chat_id, messageText, keyboard)
            else:
                self.telegram_service.send_message(chat_id, 'سفارش شما کامل شده است')

                self.telegram_service.send_main_menu(chat_id)
        except Order.DoesNotExist:
            self.telegram_service.send_message(chat_id, 'سفارش مورد نظر حذف شده است')


    def proccess_reply_message(self, chat_id, photo):
        user = TelegramUser .objects.get(chat_id=chat_id)
        # GET THE USER CURRENT PAYING ORDER
        current_order_id = user.current_order_id
        try:
            current_order = Order.objects.get(id=current_order_id)
            # Check if the order is not in complete state

            if photo:
                # GET THE PHOTO AND SAVE IT IN ORDERs
                photo_file_id = photo[-1]['file_id']
                file_path = self.get_file_path(photo_file_id)
                image_data = self.download_image(file_path)
                current_order.photo.save(f'{current_order.id}_{chat_id}.jpg', ContentFile(image_data))

                current_order.photo_id = photo_file_id
                # CHANGE ORDER STATUS TO WAIT FOR REVIEW
                current_order.status = 'wait_for_review'

                current_order.save()

                # RESPOND THE USER WITH A THANK YOU AND THAT YOU SHOULD WAIT FOR PROCCESSING
                self.telegram_service.send_message(chat_id, 'با تشکر، وضعیت سفارش شما به نیاز به بررسی تغییر یافت')
                self.message_service.send_message("رسید پرداخت برای بررسی", "09386274038")
                self.telegram_service.send_main_menu(chat_id)
                pass
            else:
                self.telegram_service.send_message(chat_id, 'لطفا فقط عکس ارسال کنید')
                self.take_user_recipe(current_order_id, chat_id)
        except Order.DoesNotExist:
            self.telegram_service.send_message(chat_id, "سفارش شما حذف شده است")


    def process_address_state_reply(self, chat_id, text):
        print(f'{text} state for {chat_id}')

        user = TelegramUser .objects.get(chat_id=chat_id)

        # Check if user has an address and update it
        try:
            address = Address.objects.get(customer=user)
            address.state = text
            address.save()
        except Address.DoesNotExist:
            # No address, creating a new one
            address = Address.objects.create(customer=user, state=text)


        self.telegram_service.send_force_reply_message(chat_id, constants.TAKE_ADDRESS_CITY)

    def proccess_address_city_reply(self, chat_id, text):
        print(f'{text} city for {chat_id}')

        user = TelegramUser .objects.get(chat_id=chat_id)

        # Check if user has an address and update it
        address = Address.objects.get(customer=user)
        address.city = text
        address.save()

        self.telegram_service.send_force_reply_message(chat_id, constants.TAKE_ADDRESS_STREET)

    def proccess_address_street_reply(self, chat_id, text):
        print(f'{text} street for {chat_id}')
        user = TelegramUser .objects.get(chat_id=chat_id)
        address = Address.objects.get(customer=user)
        address.street = text
        address.save()

        self.telegram_service.send_force_reply_message(chat_id, constants.TAKE_ADDRESS_NEIGHBORHOOD)

    def proccess_address_neighborhood_reply(self, chat_id, text):
        print(f'{text} neighborhood for {chat_id}')
        user = TelegramUser .objects.get(chat_id=chat_id)
        address = Address.objects.get(customer=user)
        address.neighborhood = text
        address.save()

        self.telegram_service.send_force_reply_message(chat_id, constants.TAKE_ADDRESS_PLATE)

    def proccess_address_plate_reply(self, chat_id, text):
        print(f'{text} plate for {chat_id}')
        user = TelegramUser .objects.get(chat_id=chat_id)
        address = Address.objects.get(customer=user)
        address.plate = text
        address.save()

        self.telegram_service.send_force_reply_message(chat_id, constants.TAKE_ADDRESS_UNIT)

    def proccess_address_unit_reply(self, chat_id, text):
        print(f'{text} unit for {chat_id}')
        user = TelegramUser .objects.get(chat_id=chat_id)
        address = Address.objects.get(customer=user)
        address.unit = text
        address.save()

        self.approve_user_address(chat_id)


    def approve_user_address(self, chat_id):
        message = self.generate_address_message(chat_id)

        keyboard = {
                'inline_keyboard':
                [
                    [
                        {
                            'text': "تایید آدرس",
                            'callback_data': "address_approved"
                        },
                        {
                            'text': "ویرایش آدرس",
                            'callback_data': "address_edit"
                        }
                    ]
                ],
                'remove_keyboard': False
            }

        self.telegram_service.send_message_with_keyboard(chat_id, message, keyboard)




    def delete_order(self, chat_id, order_id):
        current_order = Order.objects.get(id=order_id)
        # Get physical items in the order
        for item in current_order.items.all():
            print(f'{item}')
        current_order.delete()
        self.telegram_service.send_message(chat_id, self.my_bot.cancel_order_message)

    def add_product_to_order(self, chat_id, product_id):
        try:
            # Get the TelegramUser  instance
            user = TelegramUser .objects.get(chat_id=chat_id)

            # Check for existing pending orders
            pending_orders = user.orders.filter(status='pending')

            keyboard = {'inline_keyboard': [
                [{'text': 'مشاهده سبد خرید', 'callback_data': 'view_order'}]
            ], 'remove_keyboard': False}

            if pending_orders.exists():
                # If a pending order exists, use the first one (you can adjust this logic as needed)
                order = pending_orders.first()
                product = Product.objects.get(id=product_id)
                if product.downloadable:
                    print("IS DOWNLOADABLE PRODUCT")
                    order_item, created = OrderItem.objects.get_or_create(order=order, product_id=product_id)

                    if created:
                        # If the item was created, it's a new addition
                        order_item.quantity = 1  # Set initial quantity to 1
                        order_item.save()
                        # Add basket button
                        print(keyboard)
                        self.telegram_service.send_message_with_keyboard(chat_id, "محصول به سبد شما اضافه شد", keyboard)

                    else:
                        print(keyboard)
                        self.telegram_service.send_message_with_keyboard(chat_id, "محصول در سبد شما موجود است", keyboard)
                else:
                    print(keyboard)
                    order_item, created = OrderItem.objects.get_or_create(order=order, product_id=product_id)
                    if created:
                        # Check stock before creating the order item
                        if product.stock > 0:
                            # If the item was created, it's a new addition
                            order_item.quantity = 1  # Set initial quantity to 1
                            order_item.save()
                            product.stock -= 1
                            product.save()
                            print(keyboard)
                            self.telegram_service.send_message_with_keyboard(chat_id, "محصول به سبد شما اضافه شد", keyboard)
                        else:
                            self.telegram_service.send_message(chat_id, "متاسفم، موجودی کافی نیست.")
                    else:
                        # If the item already exists, check stock before incrementing
                        if product.stock > 0:
                            # If the item already exists, increment the quantity
                            order_item.quantity += 1
                            order_item.save()
                            product.stock -= 1
                            product.save()
                            print(keyboard)
                            self.telegram_service.send_message_with_keyboard(chat_id, f"محصول به سبد شما اضافه شد. تعداد: {order_item.quantity}", keyboard)
                        else:
                            self.telegram_service.send_message(chat_id, "متاسفم، موجودی کافی نیست.")
                # Check if the product already exists in the order

            else:
                # If no pending orders exist, create a new one
                order = Order.objects.create(customer=user)  # Create a new order with pending status
                product = Product.objects.get(id=product_id)

                # Add the product to the new order
                if product.downloadable:
                    OrderItem.objects.create(order=order, product_id=product_id, quantity=1)  # Set initial quantity to 1
                    self.telegram_service.send_message_with_keyboard(chat_id, "محصول به سبد شما اضافه شد", keyboard)
                else:
                    # Check stock before creating the order item
                    if product.stock > 0:
                        # If the item was created, it's a new addition
                        OrderItem.objects.create(order=order, product_id=product_id, quantity=1)
                        # Decrease product stock
                        product.stock -= 1
                        # Save product
                        product.save()
                        # Inform user
                        self.telegram_service.send_message_with_keyboard(chat_id, "محصول به سبد شما اضافه شد", keyboard)

        except TelegramUser .DoesNotExist:
            self.telegram_service.send_message(chat_id, "کاربر پیدا نشد.")


    def decrease_quantity(self, chat_id, item_id):
        try:
            # Get the TelegramUser  instance
            user = TelegramUser .objects.get(chat_id=chat_id)

            # Retrieve pending orders
            pending_orders = user.orders.filter(status='pending')

            if pending_orders.exists():
                # Use the first pending order
                order = pending_orders.first()
                # Try to find the item in the order
                item = order.items.filter(id=item_id).first()  # More efficient way to find the item

                if item:
                    product = item.product
                    if item.quantity > 1:
                        item.quantity -= 1  # Decrease the quantity
                        item.save()  # Save the updated item
                        product.stock += 1
                        product.save()
                        print(f"Decreased quantity of item {item_id}. New quantity: {item.quantity}")
                    else:
                        # Handle the case where the quantity is 1
                        item.delete()
                        product.stock += 1
                        product.save()
                        self.telegram_service.send_message(chat_id, 'محصول از سبد شما حذف شد')
                        print("Quantity is already 1. Consider removing the item instead.")

                    # Check if the order is now empty
                    if not order.items.exists():  # Check if there are no items left in the order
                        order.delete()  # Delete the order if it's empty
                        print(f"Order for user {chat_id} has been deleted because it is empty.")

                        self.telegram_service.send_message(chat_id, 'سبد خرید شما حذف شد')
                    else:
                        self.show_current_pending_order(chat_id)
                else:
                    print("Item not found in the order.")
            else:
                print("No pending orders found for the user.")

        except TelegramUser .DoesNotExist:
            print("User  not found.")


    def increase_quantity(self, chat_id, item_id):
        try:
            # Get the TelegramUser  instance
            user = TelegramUser .objects.get(chat_id=chat_id)

            # Retrieve pending orders
            pending_orders = user.orders.filter(status='pending')

            if pending_orders.exists():
                # Use the first pending order
                order = pending_orders.first()
                # Try to find the item in the order
                item = order.items.filter(id=item_id).first()  # More efficient way to find the item

                if item:
                    # Assume the item has a foreign key to the Product model
                    product = item.product  # Adjust this line according to your actual model structure
                    if product.stock > 0:  # Ensure there's enough stock
                        item.quantity += 1  # Increase the quantity
                        item.save()  # Save the updated item
                        product.stock -= 1
                        product.save()
                        self.show_current_pending_order(chat_id)
                        # self.telegram_service.send_message(chat_id, 'تعداد افزایش یافت')
                        # print(f"Increased quantity of item {item_id}. New quantity: {item.quantity}")
                    else:
                        # print(f"Cannot increase quantity. Only {product.stock} in stock.")
                        self.telegram_service.send_message(chat_id, 'تعداد افزایش نیافت، موجودی محدود')
                        # self.show_current_pending_order(chat_id, False)

                else:
                    print("Item not found in the order.")
            else:
                print("No pending orders found for the user.")

        except TelegramUser .DoesNotExist:
            print("User  not found.")


    def get_pending_orders_for_user(self, chat_id):
        try:
            # Get the TelegramUser  instance
            user = TelegramUser.objects.get(chat_id=chat_id)

            # Filter for pending orders
            pending_orders = user.orders.filter(status='pending')

            return pending_orders  # This will return a queryset of pending orders
        except TelegramUser.DoesNotExist:
            return None  # Or handle the case where the user does not exist

    def show_current_pending_order(self, chat_id):
        try:
            # Get the TelegramUser  instance
            user = TelegramUser .objects.get(chat_id=chat_id)

            # Retrieve the pending order
            pending_order = user.orders.filter(status='pending').first()

            if not pending_order:
                self.telegram_service.send_message(chat_id, "You have no pending orders.")
                return



            # Prepare the message and keyboard
            message = "سبد خرید شما:"
            keyboard = {'inline_keyboard': [], 'remove_keyboard': False}

            # Create buttons for each order item
            for item in pending_order.items.all():
                if item.product.downloadable:
                    row = [
                        {'text': "حذف این محصول", 'callback_data': f"decrease_quantity:{item.id}"},
                        {'text': f"{item.product.title}", 'callback_data': f"view_quantity_{item.id}"}
                    ]
                    keyboard['inline_keyboard'].append(row)
                else:
                    row = [
                        {'text': "کم کردن", 'callback_data': f"decrease_quantity:{item.id}"},
                        {'text': f"{item.product.title[:5]} * {item.quantity}", 'callback_data': f"view_quantity_{item.id}"},
                        {'text': "زیاد کردن", 'callback_data': f"increase_quantity:{item.id}"}
                    ]
                    keyboard['inline_keyboard'].append(row)

            keyboard['inline_keyboard'].append([{'text': "تکمیل خرید", 'callback_data': "checkout_order"}])

            # Delete the last message before sending the updated order
            response = self.telegram_service.send_message_with_keyboard(chat_id, message, keyboard=keyboard)


        except TelegramUser .DoesNotExist:
            self.telegram_service.send_message(chat_id, "User  not found.")


    def show_current_unpaid_order(self, chat_id, current_order):
        try:
            total_price = sum(item.product.price * item.quantity for item in current_order.items.all())
            message = f"سبد خرید #{current_order.id}\nجمع کل: {total_price}"
            keyboard = {'inline_keyboard': [], 'remove_keyboard': False}


            # Create buttons for each order item
            for item in current_order.items.all():
                if item.product.downloadable:
                    row = [
                        {'text': f"{item.product.title}", 'callback_data': f"view_quantity_{item.id}"}
                    ]
                    keyboard['inline_keyboard'].append(row)
                else:
                    row = [
                        {'text': f"{item.product.title[:5]} * {item.quantity}", 'callback_data': f"view_quantity_{item.id}"}
                    ]
                    keyboard['inline_keyboard'].append(row)

            keyboard['inline_keyboard'].append([{'text': self.my_bot.send_recipe_button_text, 'callback_data': f"send_recipe:{current_order.id}"}, {'text': self.my_bot.cancel_button_text, 'callback_data':f'delete_order:{current_order.id}'}])

            # Send the message with the keyboard
            self.telegram_service.send_message_with_keyboard(chat_id, message, keyboard=keyboard)

        except TelegramUser .DoesNotExist:
            self.telegram_service.send_message(chat_id, "User  not found.")


    def process_checkout(self, chat_id):
        try:
            # Get the TelegramUser  instance
            user = TelegramUser .objects.get(chat_id=chat_id)

            # Retrieve the pending order
            pending_order = user.orders.filter(status='pending').first()


            if not pending_order:
                self.telegram_service.send_message(chat_id, "در حال حاضر سبد خریدی ندارید")
                return
            else:
                user.current_order_id = pending_order.id
                user.save()

            # Check if there are any physical items in the order
            physical_items = [item for item in pending_order.items.all() if not item.product.downloadable]
            print(len(physical_items))
            # If there is not any physical items in the order we can proceed
            # else we should first take their address
            if len(physical_items) == 0:
                # Proceed with the checkout process
                self.checkout(chat_id, pending_order)
            else:
                pending_order.need_tracking = True
                pending_order.save()
                # Check if user has address
                try:
                    address = Address.objects.get(customer=user)

                    # First show the address to user to approve
                    keyboard = {
                        'inline_keyboard':
                        [
                            [
                                {
                                    'text': "تایید آدرس",
                                    'callback_data': "address_approved"
                                },
                                {
                                    'text': "ویرایش آدرس",
                                    'callback_data': 'address_edit'
                                }
                            ]
                        ],
                        'remove_keyboard': False
                    }
                    self.telegram_service.send_message_with_keyboard(chat_id, self.generate_address_message(chat_id), keyboard)
                except Address.DoesNotExist:
                    # No address, creating a new one
                    keyboard = {
                        'inline_keyboard':
                        [
                            [
                                {
                                    'text': "افزودن آدرس",
                                    'callback_data': "add_address"
                                },
                                {
                                    'text': "انصراف از خرید",
                                    'callback_data': f'delete_order:{pending_order.id}'
                                }
                            ]
                        ],
                        'remove_keyboard': False
                    }
                    self.telegram_service.send_message_with_keyboard(chat_id, constants.NO_ADDRESS_MESSAGE, keyboard)
                # We should take the user address first then let them to checkout

        except TelegramUser .DoesNotExist:
            self.telegram_service.send_message(chat_id, "User  not found.")


    def generate_address_message(self, chat_id):

        user = TelegramUser .objects.get(chat_id=chat_id)
        address = Address.objects.get(customer=user)
        message = f'استان: {address.state}'
        message += '\n'
        message += f'شهر: {address.city}'
        message += '\n'
        message += f'بلوار: {address.street}'
        message += '\n'
        message += f'خیابان: {address.neighborhood}'
        message += '\n'
        message += f'پلاک: {address.plate}'
        message += '\n'
        message += f'واحد: {address.unit}'
        message += '\n'
        return message





    def checkout(self, chat_id, order):
        print("CORRECTOOO")
        # Calculate the total price
        total_price = sum(item.product.price * item.quantity for item in order.items.all())

        # Prepare the checkout message



        message = self.generate_checkout_inovice(order)

        # Send the checkout message
        self.telegram_service.send_message(chat_id, message, False)
        self.telegram_service.send_main_menu(chat_id)


        # Optionally, you might want to update the order status here
        order.status = 'wait_for_pay'
        order.save()

    def generate_checkout_inovice(self, order):
        message = ''
        for item in order.items.all():
            message += f"نام محصول: {item.product.title} [تعداد: {item.quantity}]\n"

        total_price = sum(item.product.price * item.quantity for item in order.items.all())
        shipping_price = 0
        physical_items = [item for item in order.items.all() if not item.product.downloadable]
        if len(physical_items) == 0:
            shipping_price = 0
        else:
            shipping_price = 70000
        message += f'\n\nهزینه ارسال: {shipping_price} تومان\n\n جمع کل: {total_price+shipping_price} تومان'

        message += f'\n\nلطفا مبلغ مجموع را به شماره کارت\n{self.my_bot.card_number_text} \nواریز کنید و از قسمت سفارشات اقدام به ارسال رسید نمایید'

        return message


    def get_file_path(self, file_id):
        # Replace 'YOUR_BOT_TOKEN' with your actual bot token
        url = f"https://api.telegram.org/bot{get_bot_token()}/getFile?file_id={file_id}"
        response = requests.get(url)
        file_path = response.json()['result']['file_path']
        return file_path


    def download_image(self, file_path):
        # Replace 'YOUR_BOT_TOKEN' with your actual bot token
        url = f"https://api.telegram.org/file/bot{get_bot_token()}/{file_path}"
        response = requests.get(url)
        return response.content




def add_bot(request):
    if Telebot.objects.exists():
        return redirect('edit_bot')

    if request.method == 'POST':
        form = RobotForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            cd = form.cleaned_data
            bot_token = cd['token']
            url = settings.BASE_URL
            trim_url = url.split('//')[1]
            api_url = f'https://api.telegram.org/bot{bot_token}/setwebhook?url={trim_url}/bot/webhook/'
            print(api_url)
            res = requests.get(api_url)
            if res.status_code == 200:
                messages.success(request, 'ربات با موفقیت به سرور تلگرام متصل شد')
                return redirect('edit_bot')
            else:
                messages.error(request, 'خطایی در هنگام اتصال به سرور تلگرام رخ داد، با دکمه بروزرسانی دوباره تلاش کنید')
                return redirect('edit_bot')


    else:
        form = RobotForm()


    context = {
        'form':form
    }

    return render(request, 'shop/bot/add.html', context)




def edit_bot(request):
    bot = Telebot.objects.first()

    if request.method == 'POST':
        form = RobotForm(request.POST, request.FILES, instance=bot)
        if form.is_valid():
            form.save()
            cd = form.cleaned_data
            bot_token = cd['token']
            url = settings.BASE_URL
            trim_url = url.split('//')[1]
            api_url = f'https://api.telegram.org/bot{bot_token}/setwebhook?url={trim_url}/bot/webhook/'
            print(api_url)
            res = requests.get(api_url)
            if res.status_code == 200:
                messages.success(request, 'ربات با موفقیت به سرور تلگرام متصل شد')
                return redirect('edit_bot')
            else:
                messages.error(request, 'خطایی در هنگام اتصال به سرور تلگرام رخ داد، با دکمه بروزرسانی دوباره تلاش کنید')
                return redirect('edit_bot')

    else:
        form = RobotForm(instance=bot)


    context = {
        'bot':bot,
        'form':form
    }

    return render(request, 'shop/bot/edit.html', context)