import os
import json
from django.core.files.base import ContentFile
import requests
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from shop.models import Product, TelegramUser, Telebot
from shop import constants

# Configure logging
# logger = logging.getLogger('core')

class TelegramService:
    def __init__(self):
        self.api_url = f'https://api.telegram.org/bot{self.get_bot_token()}/'
        self.mybot = self.get_bot()

    @property
    def token(self):
        return self.get_bot_token()

    def get_bot(self):
        mybot = Telebot.objects.first()
        return mybot

    def get_bot_token(self):
        try:
            bot = Telebot.objects.first()
            return bot.token if bot else None
        except Exception as e:
            # Handle the exception (e.g., log it)
            return None

    def send_request(self, method, payload):
        try:
            url = f"{self.api_url}{method}"
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()  # Raises an error for 4xx/5xx responses
            return response.json()
        except requests.exceptions.RequestException as e:
            # logger.error(f"Failed to call Telegram API: {e}")
            raise Exception(f"Error calling Telegram API: ==> {e.response.text}")


    def send_welcome_message(self, chat_id):
        # payload = {
        #     'chat_id': chat_id,
        #     'text': 'Welcome to our shop!',
        # }
        # self.send_request('sendMessage', payload)
        self.send_welcome_message_test(chat_id)

    def send_welcome_message_test(self, chat_id):




        message = self.mybot.welcome_message
        photo = self.mybot.welcome_picture.name
        new_keyboard = [[self.mybot.category_button_text, self.mybot.basket_button_text ], [self.mybot.order_button_text]]
        reply_markup = {
            'keyboard': new_keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }

        if photo:

            picture_path = f'{settings.BASE_URL}{settings.MEDIA_URL}{photo}'

            payload = {
                'chat_id': chat_id,
                'photo': picture_path,
                'caption': message,
                'reply_markup':reply_markup
            }
            response = self.send_request('sendPhoto', payload)

        else:
            payload = {
                'chat_id': chat_id,
                'text': message,
            }
            response = self.send_request('sendMessage', payload)


    def send_main_menu(self, chat_id, delete_last=False):
        user = TelegramUser .objects.filter(chat_id=chat_id).first()

        # Check if there is a last message ID to delete
        if user and user.last_message_id and delete_last:
            try:
                delete_payload = {
                    'chat_id': chat_id,
                    'message_id': user.last_message_id
                }
                self.send_request('deleteMessage', delete_payload)  # Delete the last message
            except Exception as e:
                # Handle any errors during message deletion (e.g., log it)
                pass

        new_keyboard = [[self.mybot.category_button_text, self.mybot.basket_button_text ], [self.mybot.order_button_text]]
        reply_markup = {
            'keyboard': new_keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
        payload = {
            'chat_id': chat_id,
            'text': 'لطفا گزینه موردنظر را انتخاب کنید',
            'reply_markup':reply_markup
        }
        response = self.send_request('sendMessage', payload)
        # Update the last message ID in the user's record
        if response:
            user.last_message_id = response['result']['message_id']
            user.save()



    def send_message(self, chat_id, message, remove_keyboard=False):
        user = TelegramUser .objects.filter(chat_id=chat_id).first()
        payload = {
            'chat_id': chat_id,
            'text': message,
            'reply_markup': {'remove_keyboard': remove_keyboard}
        }
        response = self.send_request('sendMessage', payload)
        # Update the last message ID in the user's record
        if response:
            user.last_message_id = response['result']['message_id']
            user.save()

    def send_message_with_keyboard(self, chat_id, message, keyboard=None):
        # user = TelegramUser .objects.filter(chat_id=chat_id).first()

        # Check if there is a last message ID to delete
        # if user and user.last_message_id:
        #     try:
        #         delete_payload = {
        #             'chat_id': chat_id,
        #             'message_id': user.last_message_id
        #         }
        #         self.send_request('deleteMessage', delete_payload)  # Delete the last message
        #     except Exception as e:
        #         # Handle any errors during message deletion (e.g., log it)
        #         pass

        payload = {
            'chat_id': chat_id,
            'text': message,
            'reply_markup': keyboard or {}
        }
        return self.send_request("sendMessage", payload)
        # if response:
        #     user.last_message_id = response['result']['message_id']
        #     user.save()


    def send_force_reply_message(self, chat_id, message):
        keyboard = {
            'force_reply': True,
        }
        self.send_message_with_keyboard(chat_id, message, keyboard)

    def send_product_choices(self, chat_id, category, delete_last=False):
        user = TelegramUser .objects.filter(chat_id=chat_id).first()

        # Check if there is a last message ID to delete
        if user and user.last_message_id and delete_last:
            try:
                delete_payload = {
                    'chat_id': chat_id,
                    'message_id': user.last_message_id
                }
                self.send_request('deleteMessage', delete_payload)  # Delete the last message
            except Exception as e:
                # Handle any errors during message deletion (e.g., log it)
                pass


        products = Product.objects.available().filter(category=category)
        if products.count() > 0:
            keyboard = {'inline_keyboard': [], 'remove_keyboard': False}

            for i in range(0, len(products), 2):
                row = []
                for product in products[i:i + 2]:
                    button = {'text': product.title, 'callback_data': product.title}
                    row.append(button)
                keyboard['inline_keyboard'].append(row)

            response = self.send_message_with_keyboard(chat_id, self.mybot.select_product_message, keyboard)
            if response:
                user.last_message_id = response['result']['message_id']
                user.save()
        else:
            message = self.mybot.no_product_message
            response = self.send_message(chat_id, message)
            if response:
                user.last_message_id = response['result']['message_id']
                user.save()


    def generate_add_to_order_keyboard(self, product_id):
        print(product_id)
        return {
            "inline_keyboard": [
                [
                    {
                        "text": constants.ADD_PRODUCT,
                        "callback_data": f"add_to_order:{product_id}"  # Use callback data to identify the action
                    }
                ]
            ]
        }


    def send_product(self, chat_id, message, product_id, picture_name=None, delete_last=False):
        user = TelegramUser .objects.filter(chat_id=chat_id).first()

        # Check if there is a last message ID to delete
        if user and user.last_message_id and delete_last:
            try:
                delete_payload = {
                    'chat_id': chat_id,
                    'message_id': user.last_message_id
                }
                self.send_request('deleteMessage', delete_payload)  # Delete the last message
            except Exception as e:
                # Handle any errors during message deletion (e.g., log it)
                pass


        if picture_name:
            picture_path = f'{settings.BASE_URL}{settings.MEDIA_URL}{picture_name}'

            keyboard = self.generate_add_to_order_keyboard(product_id)

            payload = {
                'chat_id': chat_id,
                'photo':picture_path,
                'caption': message,
                'reply_markup': keyboard
            }
            # Ideally, you should send the photo using the sendPhoto method
            response = self.send_request("sendPhoto", payload)
            if response:
                user.last_message_id = response['result']['message_id']
                user.save()
        else:
            keyboard = self.generate_add_to_order_keyboard(product_id)

            payload = {
                'chat_id': chat_id,
                'text': message,
                'reply_markup': keyboard
            }
            # Ideally, you should send the photo using the sendPhoto method
            response = self.send_request("sendMessage", payload)
            if response:
                user.last_message_id = response['result']['message_id']
                user.save()



    def send_product(self, chat_id, message, product_id, picture_names=None):
        if picture_names:
            if len(picture_names) > 1:
                media = []
                for picture_name in picture_names:
                    picture_path = f'{settings.BASE_URL}{settings.MEDIA_URL}{picture_name}'
                    media.append({
                        'type': 'photo',
                        'media': picture_path,
                        'caption': '',  # Only set caption for the first photo
                    })


                # Ideally, you should send the photo using the sendPhoto method
                response = self.send_request("sendMediaGroup", {
                    'chat_id': chat_id,
                    'media': media
                })
                keyboard = self.generate_add_to_order_keyboard(product_id)
                if response:
                    self.send_request("sendMessage", {
                        'chat_id': chat_id,
                        'text': message,  # You can leave the text empty or add a message if needed
                        'reply_markup': keyboard
                    })
            else:
                picture_path = f'{settings.BASE_URL}{settings.MEDIA_URL}{picture_names[0]}'
                keyboard = self.generate_add_to_order_keyboard(product_id)

                payload = {
                    'chat_id': chat_id,
                    'photo':picture_path,
                    'caption': message,
                    'reply_markup': keyboard
                }
                # Ideally, you should send the photo using the sendPhoto method
                response = self.send_request("sendPhoto", payload)
        else:
            keyboard = self.generate_add_to_order_keyboard(product_id)

            payload = {
                'chat_id': chat_id,
                'text': message,
                'reply_markup': keyboard
            }
            # Ideally, you should send the photo using the sendPhoto method
            response = self.send_request("sendMessage", payload)




