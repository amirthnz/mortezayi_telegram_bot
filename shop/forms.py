from django import forms
from django.forms.widgets import ClearableFileInput
from django.forms import ImageField, FileInput
from shop.models import Product, Category, Order, ProductImage, Telebot


class NotClearableImageField(ImageField):
    widget = forms.FileInput

class CustomImageInput(ClearableFileInput):
    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control', 'accept': 'image/*', 'form_class': NotClearableImageField}  # Add any default attributes
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)



class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['title', 'featured_picture']
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان دسته بندی'}),
            'featured_picture': CustomImageInput()
        }



class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'downloadable', 'category', 'description', 'price', 'stock', 'product_file', 'featured_picture']
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان محصول'}),
            'category': forms.Select(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'id':'w3review', 'class':'form-control', 'cols':"40", 'rows':"10"}),
            'price' : forms.NumberInput(attrs={'class':'form-control', 'placeholder':'قیمت'}),
            'stock' : forms.NumberInput(attrs={'class':'form-control', 'placeholder':'موجودی'}),
            'product_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.zip', 'placeholder': 'فایل محصول'}),
            'featured_picture': CustomImageInput(),
        }


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': CustomImageInput()
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['tracking_id']
        widgets = {
            'tracking_id': forms.TextInput(attrs={'class':'form-control', 'placeholder':'کد رهگیری پستی'})
        }


class RobotForm(forms.ModelForm):
    class Meta:
        model = Telebot
        fields = [
            'title',
            'token',

            # 'shipping_price',

            'select_category_message',
            'back_button_text',
            'select_product_message',
            'no_product_message',
            'product_stock_message',
            'card_number_text',
            'category_button_text',
            'basket_button_text',
            'order_button_text',
            'send_recipe_button_text',
            'cancel_button_text',
            'cancel_order_message',

            'welcome_message',
            'welcome_picture'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'token' : forms.TextInput(attrs={'class':'form-control', 'placeholder':'توکن ربات'}),

            # 'shipping_price' : forms.NumberInput(attrs={'class':'form-control', 'placeholder':'هزینه ارسال محصولات'}),

            'select_category_message': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'back_button_text': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'select_product_message': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'no_product_message': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'product_stock_message': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'card_number_text': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'category_button_text': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'basket_button_text': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'order_button_text': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'send_recipe_button_text': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'cancel_button_text': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),
            'cancel_order_message': forms.TextInput(attrs={'class':'form-control', 'placeholder':'عنوان ربات'}),

            'welcome_message': forms.Textarea(attrs={'id':'w3review', 'class':'form-control', 'cols':"40", 'rows':"10"}),
            'welcome_picture': CustomImageInput(),
        }