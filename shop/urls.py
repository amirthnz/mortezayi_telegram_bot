from django.urls import path
from shop import views

urlpatterns = [
    path('users/', views.user_list, name='users'),
    path('users/<chat_id>', views.user_detail, name='user-detail'),
    path('addresses/', views.address_list, name='addresses'),
    path('address/<customer_id>/', views.address, name='customer-address'),
    path('broadcast/', views.broadcast, name='broadcast'),

    # Categories
    path('categories/', views.category_list, name='cat_list'),
    path('categories/add/', views.add_category, name='cat_add'), # Add category
    path('categories/edit/<int:pk>/', views.edit_category, name='cat_edit'), # Edit category
    path('categories/delete/<pk>/', views.delete_category, name='cat_delete'), # Delete category

    # Products
    path('products/', views.list_product, name='product_list'), # List products
    path('products/add/', views.add_product, name='product_add'), # Add product
    path('products/edit/<int:pk>/', views.edit_product, name='product_edit'), # Edit product
    path('products/delete/<pk>/', views.delete_product, name='product_delete'), # Delete product

    # Orders
    path('orders/', views.order_list, name='orders'),
    path('orders/<pk>/', views.order_detail, name='order_detail'),
    path('change-order-status/', views.change_order_status, name='your_status_change_url'),
    path('add_order/<product_id>/', views.add_order, name='add_order'),
    path('order/delete/<pk>/', views.order_delete , name='order_delete'),

    # Bot
    path('bot/add/', views.add_bot, name='add_bot'),
    path('bot/', views.edit_bot, name='edit_bot'),
    path('webhook/', views.TelegramWebhookAPI.as_view(), name='webhook'),
]
