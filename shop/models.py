from django.db import models
import os


def get_cat_upload_path(instance, filename):
    # Assuming 'title' is a field in your model
    # Ensure the title is safe for use in a file path
    safe_title = instance.title.lower().replace(' ', '_')  # Convert to lower case and replace spaces with underscores
    return os.path.join('media', 'categories', safe_title, filename)

def get_pro_upload_path(instance, filename):
    # Assuming 'title' is a field in your model
    # Ensure the title is safe for use in a file path
    safe_title = instance.title.lower().replace(' ', '_')  # Convert to lower case and replace spaces with underscores
    return os.path.join('media', 'products', safe_title, filename)

def get_pro_image_upload_path(instance, filename):
    # Assuming 'title' is a field in your model
    # Ensure the title is safe for use in a file path
    return os.path.join('media', 'product_images', filename)

class Telebot(models.Model):
    title = models.CharField(max_length=100, verbose_name='عنوان')
    token = models.CharField(max_length=300, verbose_name='توکن')
    welcome_message = models.TextField(verbose_name='پیام خوش آمدگویی')
    welcome_picture = models.ImageField(upload_to='media/pictures/', verbose_name='تصویر خوش آمدگویی')


    select_category_message = models.CharField(max_length=300, default='لطفا دسته بندی را انتخاب کنید')
    back_button_text = models.CharField(max_length=150, default='بازگشت')
    select_product_message = models.CharField(max_length=300, default='محصول را از لیست زیر انتخاب کنید')
    no_product_message = models.CharField(max_length=300, default='مصحولی در این دسته بندی وجود ندارد')
    product_stock_message = models.CharField(max_length=300, default='متاسفانه موجودی این محصول به پایان رسید')
    card_number_text = models.CharField(max_length=16, default='5041721025446205')
    category_button_text = models.CharField(max_length=150, default='دسته بندی ها 📁')
    basket_button_text = models.CharField(max_length=150, default='سبد خرید 🛍️')
    order_button_text = models.CharField(max_length=150, default='سفارشات من 📦')
    send_recipe_button_text = models.CharField(max_length=150, default='ارسال رسید خرید')
    cancel_button_text = models.CharField(max_length=150, default='لغو سفارش')
    cancel_order_message = models.CharField(max_length=300, default='سفارش شما لغو شد')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'ربات'
        verbose_name_plural = 'ربات ها'


# Customers will be telegram users
class TelegramUser(models.Model):
    chat_id = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, null=True, blank=True)         # The page user is currently on
    current_order_id = models.IntegerField(default=0)
    last_message_id = models.BigIntegerField(null=True, blank=True)
    last_order_message_id = models.BigIntegerField(null=True, blank=True)


    def __str__(self):
        if self.last_name:
            return self.first_name + " " + self.last_name
        else:
            return self.first_name



class Address(models.Model):
    customer = models.OneToOneField(TelegramUser, on_delete=models.CASCADE, related_name='addresses')
    location = models.TextField(null=True, blank=True)

    state = models.CharField(max_length=150, blank=True, null=True)
    city = models.CharField(max_length=150, blank=True, null=True)
    street = models.CharField(max_length=150, blank=True, null=True)
    neighborhood = models.CharField(max_length=150, blank=True, null=True)
    plate = models.CharField(max_length=10, blank=True, null=True)
    unit = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.customer.first_name + " Address"


class Category(models.Model):
    title = models.CharField(max_length=30)
    featured_picture = models.ImageField(upload_to=get_cat_upload_path, blank=True, null=True)

    def __str__(self):
        return self.title


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.filter(models.Q(stock__gt=0) | models.Q(downloadable=True))

class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)

    def available(self):
        return self.get_queryset().available()


class Product(models.Model):
    title = models.CharField(max_length=30)
    downloadable = models.BooleanField(default=False)
    category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL, blank=True, related_name='products')
    description = models.TextField(blank=True, null=True)
    price = models.IntegerField(default=0)
    stock = models.IntegerField(default=0)
    product_file = models.FileField(upload_to='files/', null=True, blank=True)
    featured_picture = models.ImageField(upload_to=get_pro_upload_path, blank=True, null=True)

    # objects = models.Manager()
    objects = ProductManager()

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=get_pro_image_upload_path, null=True, blank=True)
    # You can add additional fields like 'caption' if needed

    def __str__(self):
        return f"{self.product.title} - Image {self.id}"



class PendingManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Order.Status.PENDING)


class ReviewManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Order.Status.WAIT_FOR_REVIEW)



class Order(models.Model):

    class Status(models.TextChoices) :
        PENDING = 'pending', 'Pending'
        WAIT_FOR_PAY = 'wait_for_pay', 'Wait for Pay'
        COMPLETE = 'complete', 'Complete'
        WAIT_FOR_REVIEW = 'wait_for_review', 'Wait for review'


    customer = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='orders')
    photo_id = models.CharField(max_length=255, null=True, blank=True)  # Field to store the photo ID
    photo = models.ImageField(blank=True, null=True, upload_to='media/user/')
    status = models.CharField(max_length=100, choices=Status.choices, default=Status.PENDING)
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.SET_NULL)
    need_tracking = models.BooleanField(default=False)
    tracking_id = models.CharField(max_length=300, null=True, blank=True)

    objects = models.Manager()
    pending = PendingManager()
    review = ReviewManager()

    def __str__(self):
        return self.customer.first_name + " order number #" + str(self.id)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return self.product.title + " * " + str(self.quantity) + " --> " + self.order.customer.first_name
